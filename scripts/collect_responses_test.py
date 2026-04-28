#!/usr/bin/env python3
"""Collect OpenRouter responses for one validation prompt per Llama Guard category.
"""

import argparse
import json
import os
import time
from pathlib import Path
from typing import Optional
from openai import OpenAI


REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = REPO_ROOT / "data" / "responses" / "openrouter_tests"
DEFAULT_PROMPTS_PATH = REPO_ROOT / "data" / "prompts" / "sampled_200_final_queries.json"
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

MODEL_CONFIGS = {
    "llama-3.1-8b": {
        "label": "Llama 3.1 8B",
        "model_id": "meta-llama/llama-3.1-8b-instruct",
    },
    "llama-3.1-70b": {
        "label": "Llama 3.1 70B",
        "model_id": "meta-llama/llama-3.1-70b-instruct",
    },
    "qwen3-8b": {
        "label": "Qwen3-8B",
        "model_id": "qwen/qwen3-8b",
    },
    "qwen3-32b": {
        "label": "Qwen3-32B",
        "model_id": "qwen/qwen3-32b",
    },
    "qwen3-8b-reasoning": {
        "label": "Qwen3-8B + reasoning",
        "model_id": "qwen/qwen3-8b",
        "reasoning": True,
    },
    "qwen3-32b-reasoning": {
        "label": "Qwen3-32B + reasoning",
        "model_id": "qwen/qwen3-32b",
        "reasoning": True,
    },
    "claude-opus-4.6-reasoning": {
        "label": "Claude Opus 4.6 + reasoning",
        "model_id": "anthropic/claude-opus-4.6",
        "reasoning": True,
    },
    "gpt-5.3-reasoning": {
        "label": "GPT-5.3 + reasoning",
        "model_id": "openai/gpt-5.3-chat",
        "reasoning": True,
    },
    "claude-opus-4.6": {
        "label": "Claude Opus 4.6",
        "model_id": "anthropic/claude-opus-4.6",
    },
    "gpt-5.3": {
        "label": "GPT 5.3",
        "model_id": "openai/gpt-5.3-chat",
    },
    "grok-4.20": {
        "label": "Grok 4.20",
        "model_id": "x-ai/grok-4.20",
    },
    "gemini-2.5-pro": {
        "label": "Gemini 2.5 Pro",
        "model_id": "google/gemini-2.5-pro",
    },
    "gpt-4o": {
        "label": "GPT-4o",
        "model_id": "openai/gpt-4o",
    },
    "gpt-5": {
        "label": "GPT-5",
        "model_id": "openai/gpt-5",
    },
    "claude-sonnet-3.7": {
        "label": "Claude Sonnet 3.7",
        "model_id": "anthropic/claude-3.7-sonnet",
    },
    "claude-sonnet-4.6": {
        "label": "Claude Sonnet 4.6",
        "model_id": "anthropic/claude-sonnet-4.6",
    },
}


def get_client() -> OpenAI:
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        raise RuntimeError("Set OPENROUTER_API_KEY before running this script.")

    return OpenAI(
        base_url=OPENROUTER_BASE_URL,
        api_key=api_key,
        default_headers={
            "HTTP-Referer": "https://github.com/PinqiaoWang/LLM_Refusal_Strategy",
            "X-Title": "LLM Refusal Strategy",
        },
    )


def list_openrouter_models(client: OpenAI) -> None:
    models = client.models.list()
    for model in models.data:
        print(model.id)


def build_extra_body(config: dict) -> dict:
    if not config.get("reasoning"):
        return {}

    return {
        "reasoning": {
            "effort": "medium",
        }
    }


def load_category_prompts(prompts_path: Path, categories: Optional[list] = None) -> list:
    with open(prompts_path, "r", encoding="utf-8") as f:
        records = json.load(f)

    selected_records = []
    seen_categories = set()
    wanted_categories = set(categories) if categories else None
    for record in records:
        category = record.get("primary_llama_guard_category")
        if wanted_categories and category not in wanted_categories:
            continue
        if category and category not in seen_categories:
            selected_records.append(record)
            seen_categories.add(category)

    return selected_records


def query_model(
    client: OpenAI,
    model_key: str,
    prompt_record: dict,
    max_tokens: int,
    temperature: float,
) -> dict:
    config = MODEL_CONFIGS[model_key]
    response = client.chat.completions.create(
        model=config["model_id"],
        messages=[{"role": "user", "content": prompt_record["query"]}],
        max_completion_tokens=max_tokens,
        temperature=temperature,
        extra_body=build_extra_body(config),
    )
    raw_response = response.model_dump()
    choices = raw_response.get("choices") or [{}]
    choice = choices[0]
    message = choice.get("message") or {}
    usage = raw_response.get("usage") or {}
    response_text = message.get("content") or ""

    return {
        "final_sample_id": prompt_record.get("final_sample_id"),
        "source": prompt_record.get("source"),
        "candidate_id": prompt_record.get("candidate_id"),
        "query": prompt_record["query"],
        "primary_llama_guard_category": prompt_record.get("primary_llama_guard_category"),
        "primary_llama_guard_category_name": prompt_record.get("primary_llama_guard_category_name"),
        "llama_guard_category_codes": prompt_record.get("llama_guard_category_codes", []),
        "llama_guard_category_names": prompt_record.get("llama_guard_category_names", []),
        "model_key": model_key,
        "model_label": config["label"],
        "model_id": config["model_id"],
        "reasoning": bool(config.get("reasoning")),
        "response": response_text,
        "finish_reason": choice.get("finish_reason"),
        "native_finish_reason": choice.get("native_finish_reason"),
        "completion_tokens": usage.get("completion_tokens"),
        "total_tokens": usage.get("total_tokens"),
        "provider": raw_response.get("provider"),
        "raw_response": raw_response,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Collect OpenRouter responses for validation prompts")
    parser.add_argument("--model", choices=MODEL_CONFIGS.keys(), help="Single model key to test")
    parser.add_argument("--all", action="store_true", help="Test all configured models")
    parser.add_argument("--limit", type=int, default=None, help="Limit number of models when using --all")
    parser.add_argument("--category", action="append", help="Llama Guard category to include, e.g. S8. Can repeat.")
    parser.add_argument("--max-prompts", type=int, default=None, help="Limit number of selected validation prompts")
    parser.add_argument("--list-models", action="store_true", help="Print model IDs available from OpenRouter")
    parser.add_argument("--prompts", default=str(DEFAULT_PROMPTS_PATH), help="Validation prompt JSON file")
    parser.add_argument("--max-tokens", type=int, default=4096)
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument("--delay", type=float, default=1.0)
    parser.add_argument("--output", default=str(OUTPUT_DIR / "validation_category_probe.json"))
    args = parser.parse_args()

    client = get_client()

    if args.list_models:
        list_openrouter_models(client)
        return

    if args.all:
        model_keys = list(MODEL_CONFIGS.keys())[:args.limit]
    elif args.model:
        model_keys = [args.model]
    else:
        model_keys = ["gpt-4o"]

    prompt_records = load_category_prompts(Path(args.prompts), args.category)
    if args.max_prompts is not None:
        prompt_records = prompt_records[:args.max_prompts]
    print(f"Selected {len(prompt_records)} validation prompts")
    for record in prompt_records:
        print(
            f"  {record.get('primary_llama_guard_category')} "
            f"{record.get('primary_llama_guard_category_name')}: "
            f"final_sample_id={record.get('final_sample_id')}"
        )

    results = []
    for model_key in model_keys:
        config = MODEL_CONFIGS[model_key]
        print(f"\nTesting {config['label']} ({config['model_id']})")
        for prompt_record in prompt_records:
            category = prompt_record.get("primary_llama_guard_category")
            print(f"  Prompt {prompt_record.get('final_sample_id')} [{category}]")
            try:
                result = query_model(
                    client=client,
                    model_key=model_key,
                    prompt_record=prompt_record,
                    max_tokens=args.max_tokens,
                    temperature=args.temperature,
                )
                print(f"    OK: {result['response'][:120]!r}")
            except Exception as exc:
                result = {
                    "final_sample_id": prompt_record.get("final_sample_id"),
                    "source": prompt_record.get("source"),
                    "candidate_id": prompt_record.get("candidate_id"),
                    "query": prompt_record.get("query"),
                    "primary_llama_guard_category": category,
                    "primary_llama_guard_category_name": prompt_record.get("primary_llama_guard_category_name"),
                    "llama_guard_category_codes": prompt_record.get("llama_guard_category_codes", []),
                    "llama_guard_category_names": prompt_record.get("llama_guard_category_names", []),
                    "model_key": model_key,
                    "model_label": config["label"],
                    "model_id": config["model_id"],
                    "reasoning": bool(config.get("reasoning")),
                    "error": str(exc),
                }
                print(f"    ERROR: {exc}")

            results.append(result)
            time.sleep(args.delay)

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"Saved {len(results)} test results to {output_path}")


if __name__ == "__main__":
    main()
