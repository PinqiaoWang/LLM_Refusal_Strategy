#!/usr/bin/env python3
"""
E6: cluster bootstrap confidence intervals and pairwise significance tests.

Every prompt is answered by all models, so model-level rates are NOT independent
across models and responses are NOT independent within a prompt.  The
resampling unit is therefore the *prompt*, not the response: one bootstrap
replicate draws prompts with replacement and recomputes every model's rates on
that same redraw.  This keeps the prompt-level clustering, and it makes the
model-vs-model differences *paired*, which is what the pairwise tests need.

Implementation note: the replicate weights are drawn once as a multinomial
count matrix (B x n_prompts) shared by all models, so each model's whole set of
statistics is one matrix product rather than a Python loop over replicates.

Pairwise tests use the paired bootstrap difference distribution rather than a
two-proportion z-test.  A z-test assumes independent samples, which is exactly
what the shared prompt set violates; it would understate the precision of
within-prompt comparisons.

The reported p is a normal approximation to that difference distribution
(z = observed_difference / bootstrap_sd), Holm-corrected across all
comparisons.  The empirical tail proportion is also written out, but it cannot
be used for the correction: it cannot resolve below 1/B, and Holm multiplies
that floor by the number of tests, so with a few hundred comparisons no result
could ever reach 0.05 regardless of effect size.

Usage:
    python camera_ready/scripts/06_bootstrap_ci.py \
        --judgments-dir data/annotations/expanded_aug2026_gpt55 --iters 10000

Outputs:
    camera_ready/bootstrap_ci.csv      point estimate + CI for every rate
    camera_ready/pairwise_tests.csv    paired differences, p, Holm-adjusted p
"""

import argparse
import csv
import json
import math
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from utils.judge_config import DATA_DIR, L2_KEYS  # noqa: E402

OUT_DIR = Path(__file__).resolve().parents[1]
L1_LABELS = ["Bare", "Capacity-based", "Policy-based", "Ethics-based"]
L0_LABELS = ["Full compliance", "Partial compliance", "Non-compliance"]

# The five MDS-derived harm clusters of Figure 3a.  The three singleton clusters
# are unambiguous; membership of the two multi-category clusters is INFERRED and
# must be confirmed against whoever ran the MDS before this is used in the paper.
# Override with --clusters <json mapping category -> cluster>.
DEFAULT_CLUSTERS = {
    "Child Sexual Exploitation": "Sexual and violent harms",
    "Sexual Content": "Sexual and violent harms",
    "Sex-Related Crimes": "Sexual and violent harms",
    "Violent Crimes": "Sexual and violent harms",
    "Hate": "Sexual and violent harms",
    "Indiscriminate Weapons": "Sexual and violent harms",
    "Non-Violent Crimes": "Non-violent misuse",
    "Code Interpreter Abuse": "Non-violent misuse",
    "Privacy": "Non-violent misuse",
    "Defamation": "Non-violent misuse",
    "Elections": "Non-violent misuse",
    "Intellectual Property": "Intellectual property",
    "Specialized Advice": "Specialized advice",
    "Suicide & Self-Harm": "Suicide & self-harm",
}

# Comparisons the paper actually leans on (§5.5 trajectories and the hypothesis grid).
DEFAULT_PAIRS = [
    ("H1_size", "Llama 3.1 8B", "Llama 3.1 70B"),
    ("H1_size", "Qwen3-8B", "Qwen3-32B"),
    ("H2_reasoning", "Qwen3-8B", "Qwen3-8B + reasoning"),
    ("H2_reasoning", "Qwen3-32B", "Qwen3-32B + reasoning"),
    ("H2_reasoning", "Claude Opus 4.6", "Claude Opus 4.6 + reasoning"),
    ("H2_reasoning", "GPT 5.3", "GPT-5.3 + reasoning"),
    ("H3_family", "Claude Opus 4.6", "GPT 5.3"),
    ("H3_family", "Claude Opus 4.6", "Grok 4.20"),
    ("H3_family", "Claude Opus 4.6", "Gemini 2.5 Pro"),
    ("H4_time_openai", "GPT-4o", "GPT-5"),
    ("H4_time_openai", "GPT-5", "GPT 5.3"),
    ("H4_time_openai", "GPT-4o", "GPT 5.3"),
    ("H4_time_anthropic", "Claude Sonnet 3.7", "Claude Sonnet 4.6"),
    ("H4_time_anthropic", "Claude Sonnet 3.7", "Claude Opus 4.6"),
]


def load(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def model_label(records, fallback):
    for r in records:
        v = r.get("model_label") or r.get("model_key")
        if v:
            return str(v)
    return fallback


def holm(pvals):
    """Holm-Bonferroni step-down adjusted p-values."""
    order = np.argsort(pvals)
    adj = np.empty(len(pvals))
    running = 0.0
    for rank, idx in enumerate(order):
        val = (len(pvals) - rank) * pvals[idx]
        running = max(running, val)
        adj[idx] = min(1.0, running)
    return adj


def build_stats(records, prompt_index):
    """Numerator and denominator vectors over prompts, one row per statistic."""
    n = len(prompt_index)
    num, den, names = {}, {}, []

    judged = np.zeros(n)
    nc = np.zeros(n)
    l0 = {lab: np.zeros(n) for lab in L0_LABELS}
    l1 = {lab: np.zeros(n) for lab in L1_LABELS}
    l2 = {f: np.zeros(n) for f in L2_KEYS}

    for r in records:
        if r.get("parse_error") or r.get("judge_skipped"):
            continue
        pid = r.get("final_sample_id")
        if pid not in prompt_index:
            continue
        i = prompt_index[pid]
        judged[i] += 1
        lab = r.get("layer0")
        if lab in l0:
            l0[lab][i] += 1
        if lab == "Non-compliance":
            nc[i] += 1
            if r.get("layer1") in l1:
                l1[r["layer1"]][i] += 1
            for f in L2_KEYS:
                if r.get(f) == 1:
                    l2[f][i] += 1

    for lab in L0_LABELS:
        key = f"layer0::{lab}"
        names.append(key); num[key] = l0[lab]; den[key] = judged
    for lab in L1_LABELS:
        key = f"layer1::{lab}"
        names.append(key); num[key] = l1[lab]; den[key] = nc
    for f in L2_KEYS:
        key = f"layer2::{f}"
        names.append(key); num[key] = l2[f]; den[key] = nc

    N = np.stack([num[k] for k in names])
    D = np.stack([den[k] for k in names])
    return names, N, D


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--judgments-dir", default=str(DATA_DIR / "annotations"))
    ap.add_argument("--iters", type=int, default=10000)
    ap.add_argument("--alpha", type=float, default=0.05)
    ap.add_argument("--seed", type=int, default=2026)
    ap.add_argument("--clusters", default=None, help="JSON: category -> cluster name")
    args = ap.parse_args()

    jdir = Path(args.judgments_dir)
    files = sorted(jdir.glob("*.judged.json"))
    if not files:
        print(f"no *.judged.json under {jdir}")
        return 1

    clusters = DEFAULT_CLUSTERS
    if args.clusters:
        clusters = json.loads(Path(args.clusters).read_text(encoding="utf-8"))

    per_model = {}
    prompt_cat = {}
    for path in files:
        records = load(path)
        per_model[model_label(records, path.stem)] = records
        for r in records:
            pid = r.get("final_sample_id")
            if pid is not None:
                prompt_cat.setdefault(pid, r.get("primary_llama_guard_category_name"))

    prompts = sorted(prompt_cat)
    prompt_index = {p: i for i, p in enumerate(prompts)}
    n_prompts = len(prompts)
    print(f"{len(per_model)} models, {n_prompts} prompts, {args.iters} bootstrap replicates")

    # One shared set of replicate weights: the same prompt redraw for every
    # model, which is what makes the pairwise differences paired.
    rng = np.random.default_rng(args.seed)
    W = rng.multinomial(n_prompts, np.full(n_prompts, 1.0 / n_prompts), size=args.iters).astype(np.float64)

    # subset masks: overall, per cluster, per category
    subsets = {"overall": np.ones(n_prompts, dtype=bool)}
    for name in sorted(set(clusters.values())):
        subsets[f"cluster::{name}"] = np.array(
            [clusters.get(prompt_cat[p]) == name for p in prompts]
        )
    for cat in sorted({c for c in prompt_cat.values() if c}):
        subsets[f"category::{cat}"] = np.array([prompt_cat[p] == cat for p in prompts])

    lo_q, hi_q = 100 * args.alpha / 2, 100 * (1 - args.alpha / 2)
    rows = []
    boot_cache = {}  # (model, subset) -> (names, bootstrap rates, point estimates)
    raw_stats = {}   # model -> (names, N, D), kept for pairwise intersection tests

    for model, records in per_model.items():
        names, N, D = build_stats(records, prompt_index)
        raw_stats[model] = (names, N, D)
        for sub_name, mask in subsets.items():
            Nm, Dm = N * mask, D * mask
            point_num, point_den = Nm.sum(axis=1), Dm.sum(axis=1)
            if point_den.max() == 0:
                continue
            # (B x n_prompts) @ (n_prompts x n_stats) -> (B x n_stats)
            bn = W @ Nm.T
            bd = W @ Dm.T
            with np.errstate(invalid="ignore", divide="ignore"):
                rates = np.where(bd > 0, bn / bd, np.nan)
                point = np.where(point_den > 0, point_num / point_den, np.nan)
            boot_cache[(model, sub_name)] = (names, rates, point)

            for j, stat in enumerate(names):
                if point_den[j] == 0:
                    continue
                col = rates[:, j]
                col = col[~np.isnan(col)]
                if col.size == 0:
                    continue
                lo, hi = np.percentile(col, [lo_q, hi_q])
                layer, label = stat.split("::")
                rows.append({
                    "model": model, "subset": sub_name, "layer": layer, "statistic": label,
                    "numerator": int(point_num[j]), "denominator": int(point_den[j]),
                    "rate": round(point_num[j] / point_den[j], 4),
                    "ci_low": round(float(lo), 4), "ci_high": round(float(hi), 4),
                    "ci_width": round(float(hi - lo), 4),
                    "n_prompts_in_subset": int(mask.sum()),
                })

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    ci_out = OUT_DIR / "bootstrap_ci.csv"
    with open(ci_out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader(); w.writerows(rows)
    print(f"wrote {ci_out}  ({len(rows)} rows)")

    # ---- paired pairwise tests, overall subset ----
    tests = []
    for hyp, a, b in DEFAULT_PAIRS:
        if a not in raw_stats or b not in raw_stats:
            continue
        names_a, Na, Da = raw_stats[a]
        names_b, Nb, Db = raw_stats[b]
        assert names_a == names_b

        # The expanded dataset is ragged: three delisted models could not be
        # re-collected on the 62 new prompts, so they cover only the original
        # 200. Comparing a 262-prompt model against a 200-prompt one over their
        # own full sets would fold a prompt-set difference into the model
        # difference. Restrict every pair to the prompts BOTH models cover.
        judged_a = Da[names_a.index("layer0::Non-compliance")]
        judged_b = Db[names_b.index("layer0::Non-compliance")]
        shared = (judged_a > 0) & (judged_b > 0)
        n_shared = int(shared.sum())

        def boot(N, D):
            Nm, Dm = N * shared, D * shared
            with np.errstate(invalid="ignore", divide="ignore"):
                rates = np.where((W @ Dm.T) > 0, (W @ Nm.T) / (W @ Dm.T), np.nan)
                pt = np.where(Dm.sum(axis=1) > 0, Nm.sum(axis=1) / Dm.sum(axis=1), np.nan)
            return rates, pt

        ra, pa = boot(Na, Da)
        rb, pb = boot(Nb, Db)
        for j, stat in enumerate(names_a):
            d = (rb[:, j] - ra[:, j])
            d = d[~np.isnan(d)]
            if d.size == 0 or np.isnan(pa[j]) or np.isnan(pb[j]):
                continue
            observed = float(pb[j] - pa[j])
            # Two p-values. The empirical tail proportion cannot resolve below
            # 1/B, and with dozens of comparisons Holm multiplies that floor
            # past 0.05 -- i.e. no test could ever be significant no matter how
            # large the effect. So Holm runs on a normal approximation to the
            # bootstrap difference distribution, which is unbounded below, and
            # the empirical tail is reported alongside as a diagnostic.
            sd = float(d.std(ddof=1))
            if sd > 0:
                z = observed / sd
                p_norm = math.erfc(abs(z) / math.sqrt(2.0))
            else:
                z = float("nan")
                p_norm = 1.0 if observed == 0 else 0.0
            p_emp = 2 * min((d <= 0).mean(), (d >= 0).mean())
            lo, hi = np.percentile(d, [lo_q, hi_q])
            layer, label = stat.split("::")
            tests.append({
                "hypothesis": hyp, "model_a": a, "model_b": b,
                "n_shared_prompts": n_shared,
                "layer": layer, "statistic": label,
                "rate_a": round(float(pa[j]), 4), "rate_b": round(float(pb[j]), 4),
                "diff_b_minus_a": round(observed, 4),
                "ci_low": round(float(lo), 4), "ci_high": round(float(hi), 4),
                "z": round(z, 3) if z == z else "",
                "p_normal": float(p_norm),
                "p_empirical_tail": round(float(p_emp), 6),
                "p_empirical_floor": round(1.0 / d.size, 6),
            })
    if tests:
        adj = holm(np.array([t["p_normal"] for t in tests]))
        for t, a_ in zip(tests, adj):
            t["p_normal"] = round(t["p_normal"], 8)
            t["p_holm"] = round(float(a_), 8)
            t["significant_holm_05"] = bool(a_ < 0.05)
        pw_out = OUT_DIR / "pairwise_tests.csv"
        with open(pw_out, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(tests[0].keys()))
            w.writeheader(); w.writerows(tests)
        n_sig = sum(t["significant_holm_05"] for t in tests)
        print(f"wrote {pw_out}  ({len(tests)} comparisons, {n_sig} significant after Holm)")

    widest = sorted(rows, key=lambda r: -r["ci_width"])[:8]
    print("\nwidest CIs (least trustworthy numbers in the paper):")
    for r in widest:
        print(f"  {r['model']:26} {r['subset']:34} {r['statistic']:22} "
              f"{r['rate']:.2f} [{r['ci_low']:.2f}, {r['ci_high']:.2f}]  n={r['denominator']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
