#!/usr/bin/env python3
"""Merge the two August annotation shards into the actual August 262 run.
The August ``old200`` and ``new62`` directories are storage shards from the
same independent response run. 
Usage:
    python appendix_and_additional_experiments/scripts/merge_annotations.py
"""

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
CAMERA = Path(__file__).resolve().parents[1]
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

EXPECTED_SHA = "238bb923037b"
DELISTED = {"claude-sonnet-3.7", "gpt-5.3", "gpt-5.3-reasoning"}


def sha_of(records):
    return {(r.get("judge_prompt_sha256") or "")[:12] for r in records if not r.get("judge_skipped")}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--old-dir", default=str(
        REPO_ROOT / "data" / "annotations" / "expanded_aug2026_old200"))
    ap.add_argument("--new-dir",
                    default=str(REPO_ROOT / "data" / "annotations" / "expanded_aug2026_new62"))
    ap.add_argument("--out-dir", default=str(CAMERA / "annotations_august262"))
    args = ap.parse_args()

    old_dir, new_dir = Path(args.old_dir), Path(args.new_dir)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    rows = []
    for old_path in sorted(old_dir.glob("*.judged.json")):
        key = old_path.stem[len("responses_"):-len(".judged")] if old_path.stem.endswith(".judged") \
            else old_path.name[len("responses_"):-len(".judged.json")]
        old = json.loads(old_path.read_text(encoding="utf-8"))

        new_path = new_dir / f"responses_{key}.judged.json"
        new = json.loads(new_path.read_text(encoding="utf-8")) if new_path.exists() else []

        if new:
            shas = sha_of(old) | sha_of(new)
            bad = {s for s in shas if s and s != EXPECTED_SHA}
            if bad:
                print(f"ABORT {key}: judge prompt mismatch {bad} (expected {EXPECTED_SHA}); "
                      f"the two halves would not be comparable.")
                return 1

        if len(old) != 200 or len(new) != 62:
            print(f"ABORT {key}: expected August shards of 200+62; "
                  f"found {len(old)}+{len(new)}")
            return 1

        merged = old + new
        ids = [r.get("final_sample_id") for r in merged]
        dupes = [i for i, n in Counter(ids).items() if n > 1]
        if dupes:
            print(f"ABORT {key}: {len(dupes)} duplicated prompt ids after merge")
            return 1
        query_keys = [" ".join((r.get("query") or "").split()).casefold() for r in merged]
        duplicate_queries = [q for q, n in Counter(query_keys).items() if n > 1]
        if duplicate_queries:
            print(f"ABORT {key}: {len(duplicate_queries)} duplicated query texts after merge")
            return 1

        merged.sort(key=lambda r: (r.get("final_sample_id") or 0))
        (out_dir / f"responses_{key}.judged.json").write_text(
            json.dumps(merged, indent=2, ensure_ascii=False), encoding="utf-8")

        judged = [r for r in merged if not r.get("parse_error") and not r.get("judge_skipped")]
        nc = sum(1 for r in judged if r.get("layer0") == "Non-compliance")
        rows.append({
            "model": key, "old": len(old), "new": len(new), "total": len(merged),
            "judged": len(judged), "nc": nc,
            "skipped": sum(1 for r in merged if r.get("judge_skipped")),
            "parse_err": sum(1 for r in merged if r.get("parse_error")),
        })

    print(f"{'model':28}{'old':>5}{'new':>5}{'total':>7}{'judged':>8}{'NC':>6}"
          f"{'svc':>5}{'perr':>6}")
    for r in rows:
        tag = "  <- delisted, 200 only" if r["model"] in DELISTED else (
            "  <- supplementary" if r["new"] == 0 and r["model"] not in DELISTED else "")
        print(f"{r['model']:28}{r['old']:5}{r['new']:5}{r['total']:7}{r['judged']:8}"
              f"{r['nc']:6}{r['skipped']:5}{r['parse_err']:6}{tag}")

    exp = [r for r in rows if r["new"]]
    print(f"\n{len(exp)} August models merged to {exp[0]['total'] if exp else 0} prompts")
    print(f"total judged rows: {sum(r['judged'] for r in rows)}")
    print(f"wrote {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
