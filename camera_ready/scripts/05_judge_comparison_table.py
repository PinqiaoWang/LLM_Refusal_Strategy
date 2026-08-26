#!/usr/bin/env python3
"""
E5: full comparative results for every candidate judge on the 100-item gold set.

App D of the submitted paper says GPT-4o / GPT-5.3 / GPT-5.5 (standard and
reasoning) / o4-mini / an ensemble were compared but that "full comparative
results were not reported".  All of those runs are already in data/, so this
script only has to re-score them against gold_100.json and tabulate.

Reuses scripts/utils/judge_metrics.compute_agreement so the numbers are
produced by exactly the same code path as scripts/04_compare_judge_models_on_gold.py.

Usage:
    python camera_ready/scripts/05_judge_comparison_table.py

Outputs:
    camera_ready/appendixD_judge_comparison.csv      one row per candidate judge
    camera_ready/appendixD_judge_l2_kappa.csv        per-feature Layer 2 kappa
"""

import contextlib
import csv
import hashlib
import io
import statistics
import sys
from collections import Counter
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from utils.judge_config import DATA_DIR, L2_KEYS  # noqa: E402
from utils.judge_metrics import compute_agreement, majority_vote_ensemble  # noqa: E402
from utils.judge_utils import load_gold, load_json  # noqa: E402

OUT_DIR = Path(__file__).resolve().parents[1]

# (display name, file, family, decoding mode) -- name/family/mode come from the
# filenames and from App D, because most of these files predate the run-metadata
# fields and carry no judge_model of their own.
CANDIDATES = [
    ("GPT-4o (standard)", "judge_gpt4o_standard.json", "OpenAI", "standard"),
    ("GPT-5.3 (reasoning, high)", "judge_compare_gpt53_currentprompt_gold100.json", "OpenAI", "reasoning"),
    ("GPT-5.5 (standard)", "judge_gpt55_standard.json", "OpenAI", "standard"),
    ("GPT-5.5 (reasoning)", "judge_gpt55_reasoning.json", "OpenAI", "reasoning"),
    ("GPT-5.5 (reasoning, high)", "judge_compare_gpt55_currentprompt_gold100.json", "OpenAI", "reasoning"),
    ("GPT-5.5 (standard, v2 run)", "judge_gpt55_std_v2.json", "OpenAI", "standard"),
    ("GPT-5.5 (reasoning, v2 run)", "judge_gpt55_reas_v2.json", "OpenAI", "reasoning"),
    ("o4-mini (reasoning)", "judge_o4mini_reasoning.json", "OpenAI", "reasoning"),
    ("Ensemble (majority vote)", "judge_ensemble_v2.json", "OpenAI", "ensemble"),
]


def sha_prefix(text, n=12):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:n]


def recorded_prompt_sha(results):
    """What judge prompt did this run use, if the file recorded one?"""
    shas = Counter(r.get("judge_prompt_sha256") for r in results if r.get("judge_prompt_sha256"))
    if not shas:
        return "not recorded"
    if len(shas) > 1:
        return "MIXED: " + ",".join(sorted(s[:12] for s in shas))
    return next(iter(shas))[:12]


def recorded_model(results, fallback):
    models = Counter(r.get("judge_model") for r in results if r.get("judge_model"))
    if not models:
        return "not recorded"
    return "/".join(sorted(models))


def main():
    gold = load_gold(DATA_DIR / "gold_100.json")
    gold_ids = {int(g["human_eval_id"]) for g in gold}

    rows = []
    l2_rows = []
    for name, fname, family, mode in CANDIDATES:
        path = DATA_DIR / fname
        if not path.exists():
            print(f"SKIP (missing): {path}")
            continue
        results = load_json(path)

        # compute_agreement prints a long human-readable report; we only want
        # the returned metrics here.
        with contextlib.redirect_stdout(io.StringIO()):
            m = compute_agreement(gold, results, name)

        n_parse_error = sum(1 for r in results if r.get("parse_error"))
        covered = {int(r["human_eval_id"]) for r in results if not r.get("parse_error")}
        l2 = m["layer2"]
        kappas = [l2[k]["kappa"] for k in L2_KEYS if l2[k]["kappa"] == l2[k]["kappa"]]
        accs = [l2[k]["accuracy"] for k in L2_KEYS]

        rows.append(
            {
                "judge": name,
                "family": family,
                "mode": mode,
                "file": fname,
                "judge_model_recorded": recorded_model(results, name),
                "judge_prompt_sha256": recorded_prompt_sha(results),
                "n_gold_scored": m["layer0"]["n"],
                "n_missing_vs_gold100": len(gold_ids - covered),
                "n_parse_error": n_parse_error,
                "layer0_acc": round(m["layer0"]["accuracy"], 4),
                "layer0_kappa": round(m["layer0"]["kappa"], 4),
                "layer1_n": m["layer1"]["n"],
                "layer1_acc": round(m["layer1"]["accuracy"], 4),
                "layer1_kappa": round(m["layer1"]["kappa"], 4),
                "layer2_mean_acc": round(statistics.mean(accs), 4) if accs else "",
                "layer2_mean_kappa": round(statistics.mean(kappas), 4) if kappas else "",
                "layer2_min_kappa": round(min(kappas), 4) if kappas else "",
                "layer2_n_features_kappa_ge_0.6": sum(1 for k in kappas if k >= 0.6),
            }
        )

        for feature in L2_KEYS:
            met = l2[feature]
            k = met["kappa"]
            l2_rows.append(
                {
                    "judge": name,
                    "feature": feature,
                    "accuracy": round(met["accuracy"], 4),
                    "kappa": round(k, 4) if k == k else "",
                    "n": met["n"],
                }
            )

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    main_out = OUT_DIR / "appendixD_judge_comparison.csv"
    with open(main_out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    l2_out = OUT_DIR / "appendixD_judge_l2_kappa.csv"
    with open(l2_out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(l2_rows[0].keys()))
        w.writeheader()
        w.writerows(l2_rows)

    hdr = ["judge", "n", "L0 acc", "L0 k", "L1 acc", "L1 k", "L2 acc", "L2 k", "prompt"]
    widths = [30, 4, 7, 7, 7, 7, 7, 7, 14]
    print("".join(f"{h:{w}}" for h, w in zip(hdr, widths)))
    for r in rows:
        cells = [
            r["judge"],
            r["n_gold_scored"],
            f"{r['layer0_acc']:.1%}",
            f"{r['layer0_kappa']:.3f}",
            f"{r['layer1_acc']:.1%}",
            f"{r['layer1_kappa']:.3f}",
            f"{r['layer2_mean_acc']:.1%}",
            f"{r['layer2_mean_kappa']:.3f}",
            r["judge_prompt_sha256"],
        ]
        print("".join(f"{str(c):{w}}" for c, w in zip(cells, widths)))

    print(f"\nwrote {main_out}")
    print(f"wrote {l2_out}")

    # ---- prompt-version audit (E5's caveat: are these comparable at all?) ----
    print("\n--- judge prompt version audit ---")
    prod = Counter()
    for p in sorted((DATA_DIR / "validation_judgments").glob("*.prompt.txt")) + sorted(
        (DATA_DIR / "annotations").glob("*.prompt.txt")
    ):
        prod[sha_prefix(p.read_text(encoding="utf-8"))] += 1
    for sha, n in prod.items():
        print(f"  production annotation runs: {n} files, prompt {sha}")
    cur = DATA_DIR / "judge_prompt_current.txt"
    if cur.exists():
        print(f"  data/judge_prompt_current.txt: {sha_prefix(cur.read_text(encoding='utf-8'))}")
    print("  paper App D reports:          238bb923037b")
    print(
        "  -> rows above whose judge_prompt_sha256 is 'not recorded' predate the\n"
        "     prompt-hash logging and CANNOT be assumed comparable to the 8e88d584ea45\n"
        "     runs; footnote this in App D or re-run them."
    )


if __name__ == "__main__":
    main()
