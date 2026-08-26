#!/usr/bin/env python3
"""
E7: report the denominator behind every model-by-category estimate.

The rebuttal promised to "report the number of non-compliant responses
underlying each model-by-category estimate" and to mark small cells as
exploratory.  Table 14 currently prints rates with no base, so a cell like
"72%" can be 13/18 or 2.9/4.

Emits one row per (model, category) with n_judged / n_NC and the per-feature
counts, plus an `exploratory` flag for cells whose NC base is below the
threshold.

Usage:
    python camera_ready/scripts/07_model_by_category_base.py \
        --judgments-dir data/annotations/expanded_aug2026_gpt55

Outputs:
    camera_ready/table14_model_by_category_base.csv    long form, one row per cell
    camera_ready/table14_nc_base_matrix.csv            model x category NC bases
"""

import argparse
import csv
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from utils.judge_config import DATA_DIR, L2_KEYS  # noqa: E402

OUT_DIR = Path(__file__).resolve().parents[1]
L1_LABELS = ["Bare", "Capacity-based", "Policy-based", "Ethics-based"]


def load(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def model_label(records, fallback):
    for r in records:
        v = r.get("model_label") or r.get("model_key")
        if v:
            return str(v)
    return fallback


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--judgments-dir", default=str(DATA_DIR / "annotations"))
    ap.add_argument("--min-base", type=int, default=10,
                    help="cells with fewer non-compliant responses are flagged exploratory")
    args = ap.parse_args()

    jdir = Path(args.judgments_dir)
    files = sorted(jdir.glob("*.judged.json"))
    if not files:
        print(f"no *.judged.json under {jdir}")
        return 1

    rows = []
    matrix = defaultdict(dict)
    categories = set()
    models = []

    for path in files:
        records = load(path)
        model = model_label(records, path.stem)
        models.append(model)
        by_cat = defaultdict(list)
        for r in records:
            if r.get("parse_error") or r.get("judge_skipped"):
                continue
            by_cat[r.get("primary_llama_guard_category_name") or "(unknown)"].append(r)

        for cat, recs in sorted(by_cat.items()):
            categories.add(cat)
            nc = [r for r in recs if r.get("layer0") == "Non-compliance"]
            l1 = Counter(r.get("layer1") for r in nc)
            row = {
                "model": model,
                "category": cat,
                "n_judged": len(recs),
                "n_non_compliance": len(nc),
                "nc_rate": round(len(nc) / len(recs), 4) if recs else "",
                "exploratory": len(nc) < args.min_base,
            }
            for label in L1_LABELS:
                row[f"l1_{label.lower().replace('-', '_')}"] = l1.get(label, 0)
            for feat in L2_KEYS:
                count = sum(1 for r in nc if r.get(feat) == 1)
                row[f"{feat}_count"] = count
                # rate is only meaningful when the base exists; leave blank otherwise
                row[f"{feat}_rate"] = round(count / len(nc), 4) if nc else ""
            rows.append(row)
            matrix[model][cat] = len(nc)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    long_out = OUT_DIR / "table14_model_by_category_base.csv"
    with open(long_out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    cats = sorted(categories)
    matrix_out = OUT_DIR / "table14_nc_base_matrix.csv"
    with open(matrix_out, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["model"] + cats)
        for model in models:
            w.writerow([model] + [matrix[model].get(c, 0) for c in cats])

    n_expl = sum(1 for r in rows if r["exploratory"])
    print(f"{len(rows)} model x category cells over {len(models)} models, {len(cats)} categories")
    print(f"{n_expl} cells ({n_expl / len(rows):.0%}) have an NC base below {args.min_base} "
          f"-> must be marked exploratory in Table 14")

    bases = sorted(r["n_non_compliance"] for r in rows)
    print(f"NC base per cell: min={bases[0]}  median={bases[len(bases) // 2]}  max={bases[-1]}")

    worst = sorted(rows, key=lambda r: r["n_non_compliance"])[:10]
    print("\nsmallest cells:")
    for r in worst:
        print(f"  {r['model']:28} {r['category']:26} NC={r['n_non_compliance']:3}/{r['n_judged']:3}")

    print(f"\nwrote {long_out}")
    print(f"wrote {matrix_out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
