#!/usr/bin/env python3
"""
Deduplicate a collection run and report what is still missing.

02_collect_responses.py resumes by skipping prompts that already have a
NON-error record, but a retry `results.append(...)`s the new attempt without
removing the old error record.  So after a backfill pass a prompt can hold both
an error record and a successful one, and the file grows past the prompt count.
Upstream's own data/responses files are clean (checked), so this only bites when
someone actually retries -- which the F8 encoding bug made necessary.

Keeps, per (model_key, final_sample_id): a successful record over an error
record, and among successes the most recently collected one.

Usage:
    python appendix_and_additional_experiments/scripts/dedupe_responses.py \
        --run-dir data/responses/openrouter/expanded_aug2026 --dry-run
    python appendix_and_additional_experiments/scripts/dedupe_responses.py \
        --run-dir data/responses/openrouter/expanded_aug2026 --apply
"""

import argparse
import json
import shutil
import sys
from collections import defaultdict
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# Delisted on OpenRouter as of 2026-08; the camera-ready reuses their May data.
DELISTED = {"claude-sonnet-3.7", "gpt-5.3", "gpt-5.3-reasoning"}


def is_ok(record):
    return not record.get("error") and bool((record.get("response") or "").strip())


def better(a, b):
    """Which of two records for the same prompt to keep."""
    if is_ok(a) != is_ok(b):
        return a if is_ok(a) else b
    return a if (a.get("collected_at") or "") >= (b.get("collected_at") or "") else b


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-dir", required=True)
    ap.add_argument("--expected", type=int, default=262)
    group = ap.add_mutually_exclusive_group()
    group.add_argument("--dry-run", action="store_true", default=True)
    group.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    run_dir = Path(args.run_dir)
    files = sorted(run_dir.glob("responses_*.json"))
    if not files:
        print(f"no responses_*.json under {run_dir}")
        return 1

    # An empty response with no error is NOT a failure: it is a service-level
    # refusal, the provider blocking output before the model produced any
    print(f"{'model':30}{'records':>9}{'uniq':>7}{'ok':>6}{'svc-ref':>9}{'error':>7}{'missing':>9}")
    tot_ok = tot_err = tot_svc = tot_missing = 0
    for path in files:
        key = path.stem[len("responses_"):]
        records = json.loads(path.read_text(encoding="utf-8"))

        best = {}
        for r in records:
            pid = r.get("final_sample_id")
            best[pid] = better(best[pid], r) if pid in best else r

        deduped = [best[k] for k in sorted(best)]
        n_ok = sum(1 for r in deduped if is_ok(r))
        n_err = sum(1 for r in deduped if r.get("error"))
        n_svc = len(deduped) - n_ok - n_err
        missing = args.expected - len(deduped)

        tag = "  (delisted, reuse May data)" if key in DELISTED else ""
        print(f"{key:30}{len(records):9}{len(deduped):7}{n_ok:6}{n_svc:9}{n_err:7}{missing:9}{tag}")
        if key not in DELISTED:
            tot_ok += n_ok
            tot_err += n_err
            tot_svc += n_svc
            tot_missing += max(0, missing)

        if args.apply and len(deduped) != len(records):
            backup = path.with_suffix(".json.predupe")
            if not backup.exists():
                shutil.copy2(path, backup)
            path.write_text(json.dumps(deduped, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"\n13 collectible models: ok={tot_ok}  error={tot_err}  missing={tot_missing}")
    if args.apply:
        print("applied (originals kept as *.json.predupe)")
    else:
        print("dry run; pass --apply to rewrite the files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
