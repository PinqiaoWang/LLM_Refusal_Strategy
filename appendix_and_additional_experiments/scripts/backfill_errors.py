#!/usr/bin/env python3
"""
Targeted backfill: re-request only the (model, prompt) pairs that hold an error
record, and patch them into the existing files in place.
It also replaces the failed record rather than appending a second one, avoiding
the duplicate-record behaviour of the upstream resume path.

Usage:
    python appendix_and_additional_experiments/scripts/backfill_errors.py \
        --run-dir data/responses/openrouter/expanded_aug2026 --dry-run
    python appendix_and_additional_experiments/scripts/backfill_errors.py \
        --run-dir data/responses/openrouter/expanded_aug2026 --apply
"""

import argparse
import importlib.util
import json
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts"))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

DELISTED = {"claude-sonnet-3.7", "gpt-5.3", "gpt-5.3-reasoning"}


def load_collector():
    spec = importlib.util.spec_from_file_location(
        "collector", REPO_ROOT / "scripts" / "02_collect_responses.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-dir", required=True)
    ap.add_argument("--delay", type=float, default=0.4)
    ap.add_argument("--prompts",
                    default=str(REPO_ROOT / "data" / "prompts" / "sampled_expanded_final_queries.json"))
    group = ap.add_mutually_exclusive_group()
    group.add_argument("--dry-run", action="store_true", default=True)
    group.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    prompts = {r["final_sample_id"]: r
               for r in json.loads(Path(args.prompts).read_text(encoding="utf-8"))}

    run_dir = Path(args.run_dir)
    todo = []
    for path in sorted(run_dir.glob("responses_*.json")):
        key = path.stem[len("responses_"):]
        if key in DELISTED:
            continue
        records = json.loads(path.read_text(encoding="utf-8"))
        for idx, r in enumerate(records):
            if r.get("error"):
                todo.append((path, key, idx, r.get("final_sample_id")))

    print(f"{len(todo)} error records to retry across "
          f"{len({t[0] for t in todo})} model files")
    if not todo:
        return 0
    if not args.apply:
        for path, key, _, pid in todo:
            print(f"  {key:28} prompt {pid}")
        print("\ndry run; pass --apply to re-request these")
        return 0

    collector = load_collector()
    client = collector.get_openrouter_client()

    by_file = {}
    for path, key, idx, pid in todo:
        by_file.setdefault(path, []).append((key, idx, pid))

    fixed = failed = 0
    for path, items in by_file.items():
        records = json.loads(path.read_text(encoding="utf-8"))
        for key, idx, pid in items:
            record = prompts.get(pid)
            if record is None:
                print(f"  {key} prompt {pid}: not in prompt file, skipped")
                failed += 1
                continue
            try:
                result = collector.query_openrouter_model(
                    client=client, model_key=key, prompt_record=record,
                    max_tokens=None, temperature=0.0)
                records[idx] = result
                fixed += 1
                preview = (result.get("response") or "")[:60]
                print(f"  {key:28} prompt {pid}: OK {preview!r}")
            except Exception as exc:
                failed += 1
                print(f"  {key:28} prompt {pid}: STILL FAILING {str(exc)[:90]}")
            time.sleep(args.delay)
        path.write_text(json.dumps(records, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"\nrepaired {fixed}, still failing {failed}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
