#!/usr/bin/env python3
"""
E8: how much does expanding 200 -> 262 prompts actually move the paper's numbers?

The rebuttal promised the expanded query set, but expanding the sample
necessarily changes every reported rate.  Before rewriting the paper around the
262-prompt set, it is worth knowing whether the shifts are cosmetic (claims
survive, numbers get edited) or substantive (claims have to change).

Computes every Layer 0/1/2 rate twice on the SAME models and the SAME judge --
once restricted to the original 200 prompts, once on all 262 -- so the only
thing that differs is the added prompts.  Also re-checks the specific
trajectory claims §5.5 makes.

Usage:
    python camera_ready/scripts/14_expansion_impact.py

Outputs:
    camera_ready/expansion_impact.csv
    camera_ready/expansion_impact.md
"""

import argparse
import csv
import json
import statistics
import sys
from collections import Counter
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
CAMERA = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from utils.judge_config import L2_KEYS  # noqa: E402

L1_LABELS = ["Bare", "Capacity-based", "Policy-based", "Ethics-based"]
ORIGINAL_MAX_ID = 200

# Trajectory claims from §5.5, restricted to endpoints that BOTH got expanded.
# The §5.5 endpoints GPT-5.3 and Claude Sonnet 3.7 were delisted from OpenRouter
# before the expansion (FINDINGS F7/E2), so they exist only on the original 200
# and their trajectories cannot be re-tested on the larger set at all -- which is
# itself worth stating in the paper.
TRAJECTORY = [
    ("negative_stance", "GPT-4o", "GPT-5"),
    ("normative_suggestion", "GPT-4o", "GPT-5"),
    ("alternative_offer", "GPT-4o", "GPT-5"),
    ("executed_alternative", "GPT-4o", "GPT-5"),
    ("apology", "GPT-4o", "GPT-5"),
    ("positive_alignment", "Claude Sonnet 4.6", "Claude Opus 4.6"),
    ("explanatory_preface", "Claude Sonnet 4.6", "Claude Opus 4.6"),
    ("apology", "Claude Sonnet 4.6", "Claude Opus 4.6"),
    ("negative_stance", "Claude Sonnet 4.6", "Claude Opus 4.6"),
]


def rates(records, max_id=None):
    judged = [r for r in records
              if not r.get("parse_error") and not r.get("judge_skipped")
              and (max_id is None or (r.get("final_sample_id") or 0) <= max_id)]
    if not judged:
        return None
    l0 = Counter(r.get("layer0") for r in judged)
    nc = [r for r in judged if r.get("layer0") == "Non-compliance"]
    l1 = Counter(r.get("layer1") for r in nc)
    out = {"n_judged": len(judged), "n_nc": len(nc)}
    for lab in ("Full compliance", "Partial compliance", "Non-compliance"):
        out[f"layer0::{lab}"] = l0.get(lab, 0) / len(judged)
    for lab in L1_LABELS:
        out[f"layer1::{lab}"] = l1.get(lab, 0) / len(nc) if nc else 0.0
    for f in L2_KEYS:
        out[f"layer2::{f}"] = sum(1 for r in nc if r.get(f) == 1) / len(nc) if nc else 0.0
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--judgments-dir", default=str(CAMERA / "annotations_expanded"))
    args = ap.parse_args()

    jdir = Path(args.judgments_dir)
    per_model = {}
    for path in sorted(jdir.glob("*.judged.json")):
        records = json.loads(path.read_text(encoding="utf-8"))
        label = next((r.get("model_label") for r in records if r.get("model_label")), path.stem)
        ids = {r.get("final_sample_id") for r in records}
        if max(i for i in ids if i is not None) <= ORIGINAL_MAX_ID:
            continue  # model was never expanded; nothing to compare
        per_model[label] = records
    print(f"{len(per_model)} expanded models\n")

    rows = []
    for label, records in per_model.items():
        old, new = rates(records, ORIGINAL_MAX_ID), rates(records, None)
        if not old or not new:
            continue
        for key in old:
            if key in ("n_judged", "n_nc"):
                continue
            layer, stat = key.split("::")
            rows.append({
                "model": label, "layer": layer, "statistic": stat,
                "rate_200": round(old[key], 4), "rate_262": round(new[key], 4),
                "delta_pp": round(100 * (new[key] - old[key]), 2),
                "n_nc_200": old["n_nc"], "n_nc_262": new["n_nc"],
            })

    with open(CAMERA / "expansion_impact.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader(); w.writerows(rows)

    deltas = [abs(r["delta_pp"]) for r in rows]
    big = [r for r in rows if abs(r["delta_pp"]) >= 5]
    print(f"{len(rows)} model x statistic rates compared")
    print(f"  median |Δ| = {statistics.median(deltas):.2f} pp")
    print(f"  mean   |Δ| = {statistics.mean(deltas):.2f} pp")
    print(f"  |Δ| >= 5pp : {len(big)} ({len(big)/len(rows):.1%})")
    print(f"  |Δ| >=10pp : {sum(1 for d in deltas if d >= 10)}")
    print(f"  max    |Δ| = {max(deltas):.1f} pp")

    print("\nlargest shifts:")
    for r in sorted(rows, key=lambda r: -abs(r["delta_pp"]))[:10]:
        print(f"  {r['model']:26} {r['statistic']:22} "
              f"{r['rate_200']:.0%} -> {r['rate_262']:.0%}  ({r['delta_pp']:+.1f}pp)")

    # ---- do the §5.5 trajectory claims survive? ----
    lines = ["# 扩样对论文数字的影响(200 -> 262)", "",
             f"同样的模型、同样的 judge,唯一变化是新增的 62 条 prompt。", "",
             f"- 比较了 {len(rows)} 个 model×statistic 比率",
             f"- 中位数 |Δ| = **{statistics.median(deltas):.2f}pp**,平均 {statistics.mean(deltas):.2f}pp",
             f"- |Δ| ≥ 5pp 的有 {len(big)} 个({len(big)/len(rows):.0%}),≥10pp 的有"
             f"{sum(1 for d in deltas if d >= 10)} 个,最大 {max(deltas):.1f}pp", "",
             "## §5.5 的趋势claim在扩样后是否成立", "",
             "| 特征 | 轨迹 | 200 条 | 262 条 | 方向 |", "|---|---|---|---|---|"]

    lookup = {(r["model"], r["statistic"]): r for r in rows}
    survived = broken = 0
    for feat, m_from, m_to in TRAJECTORY:
        a, b = lookup.get((m_from, feat)), lookup.get((m_to, feat))
        if not a or not b:
            lines.append(f"| {feat} | {m_from} → {m_to} | (模型未扩样,沿用 200) | — | — |")
            continue
        # sign() with a dead zone: a trend that goes from "declines 2pp" to
        # "flat" has not reversed, but calling it unchanged overstates the case.
        def direction(d):
            return 0 if abs(d) < 0.01 else (1 if d > 0 else -1)

        old_dir = direction(b["rate_200"] - a["rate_200"])
        new_dir = direction(b["rate_262"] - a["rate_262"])
        if old_dir == new_dir:
            verdict, ok = "✅ 一致", True
        elif old_dir * new_dir < 0:
            verdict, ok = "❌ 反转", False
        else:
            verdict, ok = "⚠️ 趋势变平(未反转)", False
        survived += ok
        broken += not ok
        lines.append(f"| {feat} | {m_from} → {m_to} | "
                     f"{a['rate_200']:.0%}→{b['rate_200']:.0%} | "
                     f"{a['rate_262']:.0%}→{b['rate_262']:.0%} | {verdict} |")

    lines += ["", f"**{survived} 条方向不变,{broken} 条需要复核(反转或变平)。**",
              "> 方向判定用 ±1pp 的死区:小于 1pp 的变化算\"持平\",不算上升或下降。", "",
              "## 变化最大的 10 个", "", "| 模型 | 统计量 | 200 | 262 | Δ |", "|---|---|---|---|---|"]
    for r in sorted(rows, key=lambda r: -abs(r["delta_pp"]))[:10]:
        lines.append(f"| {r['model']} | {r['statistic']} | {r['rate_200']:.0%} | "
                     f"{r['rate_262']:.0%} | {r['delta_pp']:+.1f}pp |")

    (CAMERA / "expansion_impact.md").write_text("\n".join(lines), encoding="utf-8")
    print(f"\n§5.5 trajectory directions: {survived} unchanged, {broken} reversed")
    print(f"wrote {CAMERA / 'expansion_impact.csv'}")
    print(f"wrote {CAMERA / 'expansion_impact.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
