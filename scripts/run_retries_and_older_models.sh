#!/usr/bin/env bash
# Three-step background driver:
#   (1) Retry empty-response rows for re-routable models via alt OR sub-providers
#   (2) Collect responses for older models (GPT-4 Turbo, Llama-2-70B, Mistral-7B)
#   (3) Run GPT-5.5 judge on the older models (full-pop, resumable)
#
# Idempotent: each step skips rows already populated. Safe to re-run.
#
# Usage:
#   OPENROUTER_API_KEY=... ./scripts/run_retries_and_older_models.sh
#   OPENROUTER_API_KEY=... ./scripts/run_retries_and_older_models.sh older-only
#   OPENROUTER_API_KEY=... ./scripts/run_retries_and_older_models.sh retries-only

set -euo pipefail
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"

MODE="${1:-all}"
LOG_DIR="logs"
mkdir -p "$LOG_DIR"

RESP_DIR="data/responses/openrouter/sampled_200"
ANNOT_DIR="data/annotations"

retry_one() {
  # retry_one <local_model_key> <model_id> <provider_only_csv> [--reasoning]
  local key="$1"; local model_id="$2"; local provider_only="$3"; shift 3
  local file="$RESP_DIR/responses_${key}.json"
  local log="$LOG_DIR/retry_${key}.log"
  echo "[retry] ${key}  provider_only=${provider_only}  -> $log"
  python scripts/02b_retry_empty_responses.py \
    --input "$file" \
    --model-id "$model_id" \
    --provider-only "$provider_only" \
    --allow-fallbacks \
    "$@" \
    >> "$log" 2>&1
}

collect_one() {
  # collect_one <local_model_key>
  local key="$1"
  local log="$LOG_DIR/collect_${key}.log"
  echo "[collect] ${key} -> $log"
  python scripts/02_collect_responses.py --mode openrouter --model "$key" \
    --output-dir "$RESP_DIR" \
    >> "$log" 2>&1
}

judge_one() {
  local key="$1"
  local in="$RESP_DIR/responses_${key}.json"
  local out="$ANNOT_DIR/responses_${key}.judged.json"
  local log="$LOG_DIR/judge_${key}.log"
  echo "[judge] ${key} -> $log"
  python scripts/05_run_full_validation_judge.py --input "$in" --output "$out" \
    >> "$log" 2>&1
}

if [ "$MODE" = "all" ] || [ "$MODE" = "retries-only" ]; then
  echo "=== Step 1: provider re-routing for empty rows ==="
  # Anthropic Claude: try direct Anthropic provider on OR (current: Amazon Bedrock).
  retry_one "claude-opus-4.6"            "anthropic/claude-opus-4.6"    "Anthropic"
  retry_one "claude-opus-4.6-reasoning"  "anthropic/claude-opus-4.6"    "Anthropic" --reasoning
  retry_one "claude-sonnet-4.6"          "anthropic/claude-sonnet-4.6"  "Anthropic"
  # Qwen3: re-route off Alibaba. Available alt providers differ by model size.
  # Qwen3-8B has limited alt: only AtlasCloud. Qwen3-32B has more.
  retry_one "qwen3-8b"                   "qwen/qwen3-8b"   "atlas-cloud"
  retry_one "qwen3-32b"                  "qwen/qwen3-32b"  "DeepInfra,Fireworks,Together,Cerebras,Hyperbolic,Novita,Groq,GMI,Lambda"
  retry_one "qwen3-32b-reasoning"        "qwen/qwen3-32b"  "DeepInfra,Fireworks,Together,Cerebras,Hyperbolic,Novita,Groq,GMI,Lambda" --reasoning
  # GPT-5: re-try via OpenAI direct (already the only provider, but worth one resampling pass).
  retry_one "gpt-5"                      "openai/gpt-5"    "OpenAI"
fi

if [ "$MODE" = "all" ] || [ "$MODE" = "older-only" ]; then
  echo "=== Step 2: collect older-model responses ==="
  collect_one "gpt-4-turbo"
  collect_one "llama-3-70b-instruct"
  collect_one "mistral-7b-instruct-v0.1"

  echo "=== Step 3: judge older-model responses ==="
  judge_one "gpt-4-turbo"
  judge_one "llama-3-70b-instruct"
  judge_one "mistral-7b-instruct-v0.1"
fi

echo "=== driver done ==="
