#!/usr/bin/env python3
"""
E0: Query-pool inventory for the camera-ready expansion.

Answers: for each Llama Guard 3 category, how many *unused* unsafe prompts
remain in the SORRY-Bench and LMSYS candidate pools, and therefore what the
hard ceiling is on expanding that category.

Usage:
    python camera_ready/scripts/00_pool_inventory.py
    python camera_ready/scripts/00_pool_inventory.py --any-category

Outputs:
    camera_ready/pool_inventory.csv
"""

import argparse
import csv
import json
from collections import Counter, defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
PROMPTS = REPO_ROOT / "data" / "prompts"
OUT = Path(__file__).resolve().parents[1] / "pool_inventory.csv"

SB_CODED = PROMPTS / "sorrybench_query_candidates_llama_guard_coded.json"
LM_CODED = PROMPTS / "lmsys_harmful_query_candidates_llama_guard_coded.json"
FINAL = PROMPTS / "sampled_200_final_queries.json"


def load(p):
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--any-category",
        action="store_true",
        help="count a prompt toward every Llama Guard category assigned to it, "
        "not just the primary one (shows how much the pool grows if the "
        "primary-category rule is relaxed)",
    )
    ap.add_argument("--target", type=int, default=20, help="per-category target count")
    args = ap.parse_args()

    sb, lm, final = load(SB_CODED), load(LM_CODED), load(FINAL)
    used = {(r["source"], r["candidate_id"]) for r in final}
    current = Counter(r["primary_llama_guard_category_name"] for r in final)

    def cats_of(r):
        names = r.get("llama_guard_category_names") or []
        if not names:
            return []
        return sorted(set(names)) if args.any_category else [names[0]]

    remaining = defaultdict(lambda: [0, 0])  # cat -> [sorrybench, lmsys]
    for src, ds, idx in (("sorrybench", sb, 0), ("lmsys", lm, 1)):
        for r in ds:
            if r.get("llama_guard_safety_label") != "unsafe":
                continue
            if (src, r.get("candidate_id")) in used:
                continue
            for c in cats_of(r):
                remaining[c][idx] += 1

    rows = []
    for cat in sorted(set(current) | set(remaining)):
        sb_rem, lm_rem = remaining[cat]
        cur = current.get(cat, 0)
        ceiling = cur + sb_rem + lm_rem
        rows.append(
            {
                "category": cat,
                "current": cur,
                "sorrybench_remaining": sb_rem,
                "lmsys_remaining": lm_rem,
                "ceiling": ceiling,
                "need_for_target": max(0, args.target - cur),
                "reachable": ceiling >= args.target,
            }
        )

    w = max(len(r["category"]) for r in rows) + 2
    print(f"{'category':{w}}{'cur':>5}{'SBrem':>7}{'LMrem':>8}{'ceil':>8}  reach{args.target}")
    for r in rows:
        flag = "" if r["reachable"] else "   <-- CANNOT REACH TARGET"
        print(
            f"{r['category']:{w}}{r['current']:5}{r['sorrybench_remaining']:7}"
            f"{r['lmsys_remaining']:8}{r['ceiling']:8}  {str(r['reachable']):>5}{flag}"
        )

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT, "w", newline="", encoding="utf-8") as f:
        wtr = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        wtr.writeheader()
        wtr.writerows(rows)
    print(f"\nwrote {OUT}")

    # ---- sanity check: does the data match Table 8 in the submitted paper? ----
    src_counts = Counter(
        (r["primary_llama_guard_category_name"], r["source"]) for r in final
    )
    paper_table8 = {
        "Child Sexual Exploitation": (8, 17),
        "Code Interpreter Abuse": (8, 2),
        "Defamation": (10, 3),
        "Elections": (10, 0),
        "Hate": (10, 14),
        "Indiscriminate Weapons": (10, 0),
        "Intellectual Property": (10, 0),
        "Non-Violent Crimes": (10, 0),
        "Privacy": (8, 2),
        "Sex-Related Crimes": (8, 8),
        "Sexual Content": (10, 15),
        "Specialized Advice": (10, 0),
        "Suicide & Self-Harm": (10, 5),
        "Violent Crimes": (10, 2),
    }
    mismatches = []
    for cat, paper in paper_table8.items():
        data = (src_counts[(cat, "sorrybench")], src_counts[(cat, "lmsys")])
        if data != paper:
            mismatches.append((cat, data, paper))
    if mismatches:
        print("\n!! Table 8 in the submitted paper disagrees with the data file:")
        for cat, data, paper in mismatches:
            print(f"   {cat:32} data SB/LM={data}  paper SB/LM={paper}")
        print("   (row totals still sum to 132/68, so this looks like a "
              "transcription error in the table -- verify before camera-ready)")


if __name__ == "__main__":
    main()
