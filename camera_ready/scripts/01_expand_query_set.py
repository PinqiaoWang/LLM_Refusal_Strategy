#!/usr/bin/env python3
"""
E1: build the expanded camera-ready query set (decision A).

Target per Llama Guard 3 category is min(20, achievable ceiling).  The four
categories the rebuttal flagged as pool-limited take everything the pools have.

The whole point of this script is that new prompts go through *exactly* the
pipeline the original 200 went through, so the merged set is internally
comparable:

  * same unsafe filter (llama_guard_safety_label == "unsafe")
  * same benign-rewrite exclusions (scripts/query_filters.py)
  * same rarest-category primary assignment (multi-label prompts are charged
    to their rarest category, counted over the whole unsafe pool)
  * same LMSYS template dedup, now also deduped against templates the
    original 200 already used in that category
  * same RANDOM_SEED = 2026

--verify-pipeline re-derives the primary category of the original 200 and
fails loudly if this script's reimplementation disagrees with the stored
labels, which is the guarantee that "same pipeline" is not just a claim.

Usage:
    python camera_ready/scripts/01_expand_query_set.py
    python camera_ready/scripts/01_expand_query_set.py --target 20 --dry-run

Outputs:
    data/prompts/sampled_expanded_final_queries.json
    data/prompts/sampled_expanded_final_queries.csv
    camera_ready/table8_expanded.csv
"""

import argparse
import csv
import json
import random
import sys
from collections import Counter, defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from query_filters import (  # noqa: E402
    LLAMA_GUARD_CATEGORY_MAP,
    get_query_template_key,
    is_benign_hate_rewrite_task,
    is_benign_politeness_rewrite_task,
)
from utils import sampled_prompts_json_to_csv  # noqa: E402

RANDOM_SEED = 2026
PROMPTS = REPO_ROOT / "data" / "prompts"
CAMERA = Path(__file__).resolve().parents[1]

SB_CODED = PROMPTS / "sorrybench_query_candidates_llama_guard_coded.json"
LM_CODED = PROMPTS / "lmsys_harmful_query_candidates_llama_guard_coded.json"
FINAL_200 = PROMPTS / "sampled_200_final_queries.json"
OUT_JSON = PROMPTS / "sampled_expanded_final_queries.json"
OUT_CSV = PROMPTS / "sampled_expanded_final_queries.csv"
TABLE8 = CAMERA / "table8_expanded.csv"

CATEGORIES = list(LLAMA_GUARD_CATEGORY_MAP.keys())


def load(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def keep(record):
    """The unsafe + benign-rewrite filter used to build the original 200."""
    query = record.get("query", "")
    return (
        record.get("llama_guard_safety_label") == "unsafe"
        and not is_benign_hate_rewrite_task(query)
        and not is_benign_politeness_rewrite_task(query)
    )


def assign_primary(sb_unsafe, lm_unsafe):
    """Rarest-category primary assignment, counted over the whole unsafe pool."""
    all_unsafe = sb_unsafe + lm_unsafe
    counts = Counter(
        code
        for record in all_unsafe
        for code in record.get("llama_guard_category_codes", [])
        if code in CATEGORIES
    )
    pools = {"sorrybench": defaultdict(list), "lmsys": defaultdict(list)}
    for source, records in (("sorrybench", sb_unsafe), ("lmsys", lm_unsafe)):
        for record in records:
            codes = [c for c in record["llama_guard_category_codes"] if c in CATEGORIES]
            if not codes:
                continue
            primary = min(codes, key=lambda c: (counts[c], c))
            pools[source][primary].append(
                {
                    **record,
                    "primary_llama_guard_category": primary,
                    "primary_llama_guard_category_name": LLAMA_GUARD_CATEGORY_MAP[primary],
                }
            )
    return pools


def jaccard(a, b):
    ta, tb = set(a.lower().split()), set(b.lower().split())
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--target", type=int, default=20)
    ap.add_argument("--jaccard-threshold", type=float, default=0.8)
    ap.add_argument("--dry-run", action="store_true", help="report only, write nothing")
    ap.add_argument("--verify-pipeline", action="store_true", default=True)
    args = ap.parse_args()

    rng = random.Random(RANDOM_SEED)

    sb, lm, final200 = load(SB_CODED), load(LM_CODED), load(FINAL_200)
    sb_unsafe = [r for r in sb if keep(r)]
    lm_unsafe = [r for r in lm if keep(r)]
    pools = assign_primary(sb_unsafe, lm_unsafe)
    print(f"unsafe pool after benign-rewrite filter: SB {len(sb_unsafe)}, LMSYS {len(lm_unsafe)}")

    # ---- guarantee the reimplementation matches the original pipeline ----
    derived = {}
    for source, by_cat in pools.items():
        for cat, records in by_cat.items():
            for r in records:
                derived[(source, r["candidate_id"])] = cat
    disagree, unseen = [], []
    for r in final200:
        key = (r["source"], r["candidate_id"])
        if key not in derived:
            unseen.append(key)
        elif derived[key] != r["primary_llama_guard_category"]:
            disagree.append((key, r["primary_llama_guard_category"], derived[key]))
    print(f"pipeline check on the original 200: {len(disagree)} primary-category disagreements, "
          f"{len(unseen)} prompts not found in the filtered pool")
    if disagree[:5]:
        for k, was, now in disagree[:5]:
            print(f"   {k}: stored={was} rederived={now}")
    if args.verify_pipeline and (disagree or unseen):
        print("ABORT: this script does not reproduce the original sampling pipeline; "
              "fix before expanding, otherwise old and new prompts are not comparable.")
        return 1

    used = {(r["source"], r["candidate_id"]) for r in final200}
    current = defaultdict(list)
    for r in final200:
        current[r["primary_llama_guard_category"]].append(r)

    # templates already spent by the original 200, per category
    spent_templates = defaultdict(set)
    for r in final200:
        spent_templates[r["primary_llama_guard_category"]].add(
            get_query_template_key(r.get("query", ""))
        )

    for by_cat in pools.values():
        for records in by_cat.values():
            rng.shuffle(records)

    rows, additions = [], []
    for cat in CATEGORIES:
        name = LLAMA_GUARD_CATEGORY_MAP[cat]
        have = current[cat]
        picked = []
        # Two passes, exactly as the original supplement loop did: honour the
        # one-prompt-per-template cap first, then relax it if the category is
        # still short of target (pool-limited categories need the relaxation).
        for enforce_template_limit in (True, False):
            # SorryBench first (mirrors the balanced-core source preference), then LMSYS
            for source in ("sorrybench", "lmsys"):
                for r in pools[source][cat]:
                    if len(have) + len(picked) >= args.target:
                        break
                    if (r["source"], r["candidate_id"]) in used:
                        continue
                    tkey = get_query_template_key(r.get("query", ""))
                    if enforce_template_limit and tkey in spent_templates[cat]:
                        continue
                    if any(jaccard(r["query"], o["query"]) > args.jaccard_threshold
                           for o in have + picked):
                        continue
                    picked.append(r)
                    used.add((r["source"], r["candidate_id"]))
                    spent_templates[cat].add(tkey)
            if len(have) + len(picked) >= args.target:
                break

        additions.extend(picked)
        merged = have + picked
        reached = len(merged) >= args.target

        # Two different ceilings, and the difference matters for Table 8.
        # raw   = every unused unsafe prompt the pools still hold for this category
        # usable = what survives near-duplicate removal.  For the pool-limited
        #          categories the raw count badly overstates availability: e.g.
        #          Code Interpreter Abuse's 9 remaining LMSYS prompts are really
        #          3 distinct prompts repeated.  When a category fails to reach
        #          target we have by construction exhausted its usable pool, so
        #          the achieved total *is* the usable ceiling.
        raw_remaining = sum(
            1
            for source in ("sorrybench", "lmsys")
            for r in pools[source][cat]
            if (r["source"], r["candidate_id"]) not in used
        )
        rows.append(
            {
                "category": name,
                "sorrybench": sum(1 for r in merged if r["source"] == "sorrybench"),
                "lmsys": sum(1 for r in merged if r["source"] == "lmsys"),
                "total": len(merged),
                "n_original": len(have),
                "n_added": len(picked),
                "pool_ceiling_raw": len(merged) + raw_remaining,
                "pool_ceiling_usable": len(merged) if not reached else f">={args.target}",
                "reached_target": reached,
            }
        )

    print(f"\n{'category':28}{'orig':>6}{'+new':>6}{'total':>7}{'raw':>7}{'usable':>9}")
    for r in rows:
        flag = "" if r["reached_target"] else "   <-- pool-limited"
        print(f"{r['category']:28}{r['n_original']:6}{r['n_added']:6}{r['total']:7}"
              f"{r['pool_ceiling_raw']:7}{str(r['pool_ceiling_usable']):>9}{flag}")
    print(f"\nTOTAL: {sum(r['total'] for r in rows)} prompts "
          f"({sum(r['n_original'] for r in rows)} original + {sum(r['n_added'] for r in rows)} new)")

    # ---- acceptance check: no new prompt near-duplicates an original one ----
    worst = 0.0
    worst_pair = None
    old_queries = [r["query"] for r in final200]
    for r in additions:
        for q in old_queries:
            j = jaccard(r["query"], q)
            if j > worst:
                worst, worst_pair = j, (r["query"][:60], q[:60])
    print(f"max Jaccard(new, original) = {worst:.3f} (threshold {args.jaccard_threshold})")
    if worst_pair and worst > args.jaccard_threshold:
        print(f"   !! {worst_pair}")

    if args.dry_run:
        print("\n--dry-run: nothing written")
        return 0

    # ---- merged output: original ids frozen, new prompts continue the numbering ----
    expanded = [{**r, "batch": "v1"} for r in final200]
    next_id = max(r["final_sample_id"] for r in final200) + 1
    rng.shuffle(additions)
    for r in additions:
        expanded.append({"final_sample_id": next_id, **r, "batch": "v2"})
        next_id += 1

    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(expanded, f, indent=2, ensure_ascii=False)
    sampled_prompts_json_to_csv(str(OUT_JSON), str(OUT_CSV))

    with open(TABLE8, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    ids = [r["final_sample_id"] for r in expanded]
    assert len(ids) == len(set(ids)), "duplicate final_sample_id"
    assert [r["final_sample_id"] for r in expanded[: len(final200)]] == [
        r["final_sample_id"] for r in final200
    ], "original final_sample_id values were not preserved"

    print(f"\nwrote {OUT_JSON} ({len(expanded)} prompts)")
    print(f"wrote {OUT_CSV}")
    print(f"wrote {TABLE8}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
