#!/usr/bin/env bash
# Drives 05_run_full_validation_judge.py across all 16 model response files
# in parallel (default N=8). Resumable: re-running picks up where it left off,
# because the inner script writes after every record and gates on prompt SHA256.
#
# Usage:
#   OPENROUTER_API_KEY=... ./scripts/run_full_population_judge.sh [PARALLELISM]

set -euo pipefail
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"

PARALLELISM="${1:-8}"
LOG_DIR="logs"
mkdir -p "$LOG_DIR" data/annotations

# Canonical 16 models (excludes the stray gpt53.json duplicate of gpt-5.3.json).
models=(
  claude-opus-4.6
  claude-opus-4.6-reasoning
  claude-sonnet-3.7
  claude-sonnet-4.6
  gemini-2.5-pro
  gpt-4o
  gpt-5
  gpt-5.3
  gpt-5.3-reasoning
  grok-4.20
  llama-3.1-8b
  llama-3.1-70b
  qwen3-8b
  qwen3-8b-reasoning
  qwen3-32b
  qwen3-32b-reasoning
)

echo "[driver] $(date) starting full-pop judge run, parallelism=$PARALLELISM"
echo "[driver] judge model: openai/gpt-5.5 (non-reasoning)"
echo "[driver] ${#models[@]} model files"

printf '%s\n' "${models[@]}" | xargs -n 1 -P "$PARALLELISM" -I {} bash -c '
  m="$1"
  in="data/responses/openrouter/sampled_200/responses_${m}.json"
  out="data/annotations/responses_${m}.judged.json"
  log="logs/judge_${m}.log"
  if [ ! -f "$in" ]; then
    echo "[skip] $m: missing input $in"
    exit 0
  fi
  echo "[start] $m"
  if python scripts/05_run_full_validation_judge.py --input "$in" --output "$out" >> "$log" 2>&1; then
    echo "[ok]    $m"
  else
    rc=$?
    echo "[FAIL]  $m exit=$rc (see $log)"
    exit $rc
  fi
' _ {}

echo "[driver] $(date) all models complete"
