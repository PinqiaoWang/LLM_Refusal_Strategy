#!/usr/bin/env bash
# Targeted re-judge of parse_error rows.
#
# The judge's resume logic drops parse_error rows from `existing` and re-attempts
# them on each fresh run. We bump --reasoning-effort=medium so the judge gets a
# new bite at the apple instead of repeating the same deterministic temp=0
# refusal it gave last time. The prompt SHA256 is unchanged by reasoning effort,
# so successful rows stay put.

set -euo pipefail
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"

LOG_DIR="logs"
mkdir -p "$LOG_DIR"

models=(
  claude-sonnet-3.7
  gemini-2.5-pro
  gpt-4-turbo
  gpt-5
  gpt-5.3
  gpt-5.3-reasoning
  llama-3-70b-instruct
  llama-3.1-70b
  llama-3.1-8b
  mistral-7b-instruct-v0.1
  qwen3-32b
  qwen3-32b-reasoning
  qwen3-8b
  qwen3-8b-reasoning
)

EFFORT="${1:-medium}"
echo "[recovery] $(date) re-judging parse_error rows with --reasoning-effort=$EFFORT"

printf '%s\n' "${models[@]}" | xargs -n 1 -P 4 -I {} bash -c '
  m="$1"; effort="$2"
  in="data/responses/openrouter/sampled_200/responses_${m}.json"
  out="data/annotations/responses_${m}.judged.json"
  log="logs/recover_${m}.log"
  if [ ! -f "$in" ]; then
    echo "[skip] $m: missing $in"; exit 0
  fi
  echo "[start] $m (effort=$effort)"
  if python scripts/05_run_full_validation_judge.py \
       --input "$in" --output "$out" \
       --reasoning-effort "$effort" >> "$log" 2>&1; then
    echo "[ok]    $m"
  else
    rc=$?; echo "[FAIL]  $m exit=$rc (see $log)"; exit $rc
  fi
' _ {} "$EFFORT"

echo "[recovery] $(date) done"
