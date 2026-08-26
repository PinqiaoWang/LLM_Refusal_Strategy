#!/usr/bin/env python3
"""
Build per-model judging inputs containing ONLY the newly added prompts.

The existing 200 prompts are already annotated upstream with the current judge
(openai/gpt-5.5, reasoning_effort=none, prompt sha 238bb923037b), so they must
not be re-judged: re-running them would spend money and, because the judge is
an LLM, would perturb numbers the paper already reports.  Only the 62 prompts
added by the camera-ready expansion need labels.

The judge prompt must rebuild to 238bb923037b, the same prompt used for the
existing 200; the script prints the exact invocations to use.

Usage:
    python camera_ready/scripts/12_prepare_new_prompt_judging.py
"""

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
CAMERA = Path(__file__).resolve().parents[1]
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

DELISTED = {"claude-sonnet-3.7", "gpt-5.3", "gpt-5.3-reasoning"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-dir",
                    default=str(REPO_ROOT / "data/responses/openrouter/expanded_aug2026"))
    ap.add_argument("--prompts",
                    default=str(REPO_ROOT / "data/prompts/sampled_expanded_final_queries.json"))
    ap.add_argument("--out-dir", default=str(CAMERA / "_judge_input"))
    args = ap.parse_args()

    prompts = json.loads(Path(args.prompts).read_text(encoding="utf-8"))
    v2_ids = {r["final_sample_id"] for r in prompts if r.get("batch") == "v2"}
    print(f"new prompts to judge: {len(v2_ids)} (batch v2)")

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    total = total_empty = 0
    written = []
    for path in sorted(Path(args.run_dir).glob("responses_*.json")):
        key = path.stem[len("responses_"):]
        if key in DELISTED:
            continue
        records = json.loads(path.read_text(encoding="utf-8"))
        new = [r for r in records if r.get("final_sample_id") in v2_ids]
        if not new:
            continue
        # Guard: a concurrent collector append (see 10_dedupe_responses.py) would
        # silently duplicate prompts here and double-bill the judge. Refuse rather
        # than emit a bad input file.
        ids = [r.get("final_sample_id") for r in new]
        if len(set(ids)) != len(ids):
            dupes = {i for i in ids if ids.count(i) > 1}
            print(f"ERROR {key}: {len(dupes)} duplicated prompt ids. "
                  f"Run 10_dedupe_responses.py --apply first.")
            return 1
        # Service-level refusals (empty response) are kept: the judge script
        # records them as judge_skipped, which is how the original 200 were
        # handled, and App E counts them.
        empty = sum(1 for r in new if not (r.get("response") or "").strip())
        still_err = sum(1 for r in new if r.get("error"))
        dest = out_dir / f"responses_{key}.json"
        dest.write_text(json.dumps(new, indent=2, ensure_ascii=False), encoding="utf-8")
        written.append((key, len(new), empty, still_err))
        total += len(new)
        total_empty += empty

    print(f"\n{'model':30}{'to judge':>10}{'svc-ref':>9}{'error':>7}")
    for key, n, empty, err in written:
        print(f"{key:30}{n:10}{empty:9}{err:7}")
    print(f"\n{len(written)} models x {len(v2_ids)} prompts = {total} records "
          f"({total_empty} will be marked judge_skipped)")

    print("\n--- run these from the upstream checkout (prompt sha 238bb923037b) ---")
    print("for f in %s/responses_*.json; do" % out_dir.as_posix())
    print("  m=$(basename \"$f\" .json)")
    print("  python scripts/05_run_full_validation_judge.py \\")
    print("    --input \"$f\" \\")
    print("    --output %s/\"$m\".judged.json \\" % (CAMERA / "_judge_output").as_posix())
    print("    --provider openrouter --model openai/gpt-5.5 --reasoning-effort none --delay 0.3")
    print("done")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
