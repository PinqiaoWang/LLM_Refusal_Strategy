#!/usr/bin/env python3
"""
Step 2: Query LLMs and collect responses on benchmark prompts.
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Optional

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BENCHMARK_PROMPTS_PATH = REPO_ROOT / "data" / "prompts" / "benchmark.json"
DEFAULT_SAMPLED_PROMPTS_PATH = REPO_ROOT / "data" / "prompts" / "sampled_200_final_queries.json"
DEFAULT_RESPONSES_DIR = REPO_ROOT / "data" / "responses"
DEFAULT_OPENROUTER_RESPONSES_DIR = DEFAULT_RESPONSES_DIR / "openrouter"
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

sys.path.insert(0, str(REPO_ROOT))
from utils import openrouter_responses_json_to_csv

OPENROUTER_MODEL_CONFIGS = {
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
    # Older / legacy generation — added 2026-05-20 to extend temporal coverage.
    "gpt-4-turbo": {
        "label": "GPT-4 Turbo",
        "model_id": "openai/gpt-4-turbo",
    },
    "llama-3-70b-instruct": {
        "label": "Llama 3 70B Instruct",
        "model_id": "meta-llama/llama-3-70b-instruct",
    },
    "mistral-7b-instruct-v0.1": {
        "label": "Mistral 7B Instruct v0.1",
        "model_id": "mistralai/mistral-7b-instruct-v0.1",
    },
}


def get_openrouter_client():
    from openai import OpenAI

    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        raise RuntimeError("Set OPENROUTER_API_KEY before running OpenRouter collection.")

    return OpenAI(
        base_url=OPENROUTER_BASE_URL,
        api_key=api_key,
        default_headers={
            "HTTP-Referer": "https://github.com/PinqiaoWang/LLM_Refusal_Strategy",
            "X-Title": "LLM Refusal Strategy",
        },
    )


def list_openrouter_models(client) -> None:
    models = client.models.list()
    for model in models.data:
        print(model.id)


def build_openrouter_extra_body(config: dict) -> dict:
    if not config.get("reasoning"):
        return {}

    return {
        "reasoning": {
            "effort": "medium",
        }
    }


def load_sampled_prompts(
    prompts_path: Path,
    categories: Optional[list] = None,
    max_prompts: Optional[int] = None,
    one_per_category: bool = False,
) -> list:
    with open(prompts_path, "r", encoding="utf-8") as f:
        records = json.load(f)

    selected_records = []
    seen_categories = set()
    wanted_categories = set(categories) if categories else None
    for record in records:
        category = record.get("primary_llama_guard_category")
        if wanted_categories and category not in wanted_categories:
            continue
        if one_per_category:
            if not category or category in seen_categories:
                continue
            seen_categories.add(category)
        selected_records.append(record)
        if max_prompts is not None and len(selected_records) >= max_prompts:
            break

    return selected_records


def get_result_key(result: dict) -> tuple:
    return (
        result.get("model_key"),
        result.get("final_sample_id"),
        result.get("query"),
    )


def save_results(results: list, output_path: Path) -> None:
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)


def load_existing_results(output_path: Path) -> list:
    if not output_path.exists():
        return []

    try:
        with open(output_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError:
        backup_path = output_path.with_suffix(output_path.suffix + ".corrupt")
        output_path.rename(backup_path)
        print(f"Existing output was not valid JSON; moved it to {backup_path}")
        return []


def query_openrouter_model(
    client,
    model_key: str,
    prompt_record: dict,
    max_tokens: Optional[int],
    temperature: float,
) -> dict:
    config = OPENROUTER_MODEL_CONFIGS[model_key]
    request_kwargs = {
        "model": config["model_id"],
        "messages": [{"role": "user", "content": prompt_record["query"]}],
        "temperature": temperature,
        "extra_body": build_openrouter_extra_body(config),
    }
    if max_tokens is not None:
        request_kwargs["max_completion_tokens"] = max_tokens

    response = client.chat.completions.create(**request_kwargs)
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


def collect_openrouter_responses(args) -> None:
    client = get_openrouter_client()

    if args.list_models:
        list_openrouter_models(client)
        return

    if args.all:
        model_keys = list(OPENROUTER_MODEL_CONFIGS.keys())[:args.limit]
    elif args.model:
        if args.model not in OPENROUTER_MODEL_CONFIGS:
            raise ValueError(f"Unknown OpenRouter model key: {args.model}")
        model_keys = [args.model]
    else:
        model_keys = ["gpt-4o"]

    prompt_records = load_sampled_prompts(
        prompts_path=Path(args.prompts),
        categories=args.category,
        max_prompts=args.max_prompts,
        one_per_category=args.one_per_category,
    )

    print(f"Selected {len(prompt_records)} prompts")
    for record in prompt_records:
        print(
            f"  {record.get('primary_llama_guard_category')} "
            f"{record.get('primary_llama_guard_category_name')}: "
            f"final_sample_id={record.get('final_sample_id')}"
        )

    combined_output_path = Path(args.output) if args.output else None
    combined_results = None
    combined_completed_keys = None
    if combined_output_path:
        combined_output_path.parent.mkdir(parents=True, exist_ok=True)
        combined_results = load_existing_results(combined_output_path)
        combined_completed_keys = {
            get_result_key(result)
            for result in combined_results
            if not result.get("error")
        }
        print(f"Loaded {len(combined_results)} existing responses from {combined_output_path}")

    for model_key in model_keys:
        config = OPENROUTER_MODEL_CONFIGS[model_key]
        if combined_output_path:
            output_path = combined_output_path
            results = combined_results
            completed_keys = combined_completed_keys
        else:
            output_path = Path(args.output_dir) / f"responses_{model_key}.json"
            output_path.parent.mkdir(parents=True, exist_ok=True)
            results = load_existing_results(output_path)
            completed_keys = {
                get_result_key(result)
                for result in results
                if not result.get("error")
            }
            print(f"Loaded {len(results)} existing responses from {output_path}")

        print(f"\nTesting {config['label']} ({config['model_id']})")
        for prompt_record in prompt_records:
            category = prompt_record.get("primary_llama_guard_category")
            result_key = (
                model_key,
                prompt_record.get("final_sample_id"),
                prompt_record.get("query"),
            )
            if result_key in completed_keys:
                print(f"  Prompt {prompt_record.get('final_sample_id')} [{category}] SKIP existing")
                continue
            print(f"  Prompt {prompt_record.get('final_sample_id')} [{category}]")
            try:
                result = query_openrouter_model(
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
            if not result.get("error"):
                completed_keys.add(get_result_key(result))
            save_results(results, output_path)
            output_csv_path = output_path.with_suffix(".csv")
            openrouter_responses_json_to_csv(str(output_path), str(output_csv_path))
            print(f"    Saved progress: {len(results)} rows")
            print(f"    Saved CSV progress to {output_csv_path}")
            time.sleep(args.delay)

        print(f"Saved {len(results)} responses to {output_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Collect model responses")
    parser.add_argument("--mode", choices=["api", "local", "openrouter"], default="openrouter",
                        help="API models, local vLLM models, or OpenRouter models")
    parser.add_argument("--model", default=None,
                        help="Specific model name")
    parser.add_argument("--all", action="store_true",
                        help="Run all configured OpenRouter models")
    parser.add_argument("--limit", type=int, default=None,
                        help="Limit number of OpenRouter models when using --all")
    parser.add_argument("--category", action="append",
                        help="Llama Guard category to include, e.g. S8. Can repeat.")
    parser.add_argument("--max-prompts", type=int, default=None,
                        help="Limit number of selected sampled prompts")
    parser.add_argument("--one-per-category", action="store_true",
                        help="Select only the first prompt from each selected Llama Guard category")
    parser.add_argument("--list-models", action="store_true",
                        help="Print model IDs available from OpenRouter")
    parser.add_argument("--prompts", default=None,
                        help="Path to benchmark or sampled prompt JSON")
    parser.add_argument("--config", default="configs/models.yaml",
                        help="Path to model config for api/local modes")
    parser.add_argument("--output-dir", default=None,
                        help="Output directory for responses")
    parser.add_argument("--output", default=None,
                        help="Output JSON path for OpenRouter mode")
    parser.add_argument("--max-tokens", type=int, default=None,
                        help="Optional max completion tokens for OpenRouter mode")
    parser.add_argument("--temperature", type=float, default=0.0,
                        help="Temperature for OpenRouter mode")
    parser.add_argument("--delay", type=float, default=1.0,
                        help="Delay between OpenRouter requests")
    parser.add_argument("--wildchat", action="store_true",
                        help="Also sample from WildChat for Layer 0 analysis")
    parser.add_argument("--n", type=int, default=1000,
                        help="Number of WildChat samples")
    args = parser.parse_args()
    if args.prompts is None:
        if args.mode == "openrouter":
            args.prompts = str(DEFAULT_SAMPLED_PROMPTS_PATH)
        else:
            args.prompts = str(DEFAULT_BENCHMARK_PROMPTS_PATH)
    if args.output_dir is None:
        if args.mode == "openrouter":
            args.output_dir = str(DEFAULT_OPENROUTER_RESPONSES_DIR)
        else:
            args.output_dir = str(DEFAULT_RESPONSES_DIR)

    if args.wildchat:
        from src.data_collection import sample_wildchat
        print("=" * 60)
        print("Sampling from WildChat for Layer 0 analysis")
        print("=" * 60)
        sample_wildchat(
            n=args.n,
            output_path="data/responses/wildchat_sample.json",
        )
        print()

    print("=" * 60)
    print(f"Collecting responses (mode={args.mode})")
    print("=" * 60)

    if args.mode == "openrouter":
        collect_openrouter_responses(args)
        return

    from src.model_inference import collect_responses
    collect_responses(
        prompts_path=args.prompts,
        config_path=args.config,
        mode=args.mode,
        model_name=args.model,
        output_dir=args.output_dir,
    )


if __name__ == "__main__":
    main()
