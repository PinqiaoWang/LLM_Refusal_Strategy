#!/usr/bin/env bash
# Judge the 62 newly added prompts for each collectible model.
#
# The judge prompt must rebuild to 238bb923037b -- the same prompt used for the
# existing 200 -- or the new labels are not comparable with the old ones.
#
# Resumable: 05_run_full_validation_judge.py skips records already present in
# the output whose judge_prompt_sha256 matches, so re-running continues.
set -u

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
IN="$ROOT/camera_ready/_judge_input"
OUT="$ROOT/data/annotations/expanded_aug2026_new62"

export OPENROUTER_API_KEY=$(grep '^OPENROUTER_API_KEY=' "$ROOT/.env" | cut -d= -f2- | tr -d '"'\''\r')
if [ -z "${OPENROUTER_API_KEY:-}" ]; then echo "no key"; exit 1; fi

mkdir -p "$OUT"
cd "$ROOT" || exit 1

for f in "$IN"/responses_*.json; do
  m=$(basename "$f" .json)
  echo "=== $m ==="
  python scripts/05_run_full_validation_judge.py \
    --input "$f" \
    --output "$OUT/$m.judged.json" \
    --provider openrouter --model openai/gpt-5.5 --reasoning-effort none \
    --delay 0.2 2>&1 | grep -vE "it/s\]|it\]" | tail -3
done

echo "ALL DONE"
