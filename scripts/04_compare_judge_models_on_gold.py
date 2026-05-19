#!/usr/bin/env python3
"""Evaluate a judge model against the 100 human gold examples."""

import argparse
import time
from pathlib import Path
from typing import Optional

import httpx
from tqdm import tqdm

from utils.gold_rule_common import build_gold_rule_section
from utils.judge_config import DATA_DIR, DEFAULT_GOLD_RULE_PATH, JUDGE_SYSTEM_PROMPT
from utils.judge_utils import (
    create_client,
    keep_successful,
    load_gold,
    load_json,
    retry_parse_call,
    text_sha256,
    user_message,
    write_json,
)
from utils.judge_metrics import compute_agreement


DEFAULT_OUT = DATA_DIR / "judge_calibrated_gold100.json"
DEFAULT_PROMPT_OUT = DATA_DIR / "judge_prompt_current.txt"


def build_prompt(
    gold_rule_path: Optional[str],
    gold_rule_examples: Optional[int],
    max_query_chars: int,
    max_response_chars: int,
) -> str:
    prompt = JUDGE_SYSTEM_PROMPT
    if gold_rule_path:
        prompt += build_gold_rule_section(
            gold_rule_path,
            max_examples=gold_rule_examples,
            max_query_chars=max_query_chars,
            max_response_chars=max_response_chars,
        )
    return prompt


def judge_item(
    client,
    provider: str,
    model: str,
    prompt: str,
    reasoning_effort: str,
    item: dict,
    max_output_tokens: int,
) -> dict:
    def call():
        if provider == "openrouter":
            request_kwargs = {
                "model": model,
                "messages": [
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": user_message(item)},
                ],
                "max_tokens": max_output_tokens,
                "temperature": 0,
            }
            if reasoning_effort != "none":
                request_kwargs["extra_body"] = {"reasoning": {"effort": reasoning_effort}}
            response = client.chat.completions.create(**request_kwargs)
            return (response.choices[0].message.content or "").strip()

        response = client.responses.create(
            model=model,
            instructions=prompt,
            input=user_message(item),
            reasoning={"effort": reasoning_effort},
            max_output_tokens=max_output_tokens,
        )
        return response.output_text.strip()

    parsed = retry_parse_call(call)
    parsed["human_eval_id"] = item["human_eval_id"]
    parsed["parse_error"] = False
    return parsed


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate an LLM judge on gold_100")
    parser.add_argument("--provider", choices=["openai", "openrouter"], default="openrouter")
    parser.add_argument("--model", default="openai/gpt-5.3-chat")
    parser.add_argument("--reasoning-effort", default="high", choices=["none", "low", "medium", "high"])
    parser.add_argument("--gold", default=str(DATA_DIR / "gold_100.json"))
    parser.add_argument("--output", default=str(DEFAULT_OUT))
    parser.add_argument("--prompt-output", default=str(DEFAULT_PROMPT_OUT))
    parser.add_argument("--gold-rule-path", default=str(DEFAULT_GOLD_RULE_PATH),
                        help="Path to Gold Rule xlsx. Pass an empty string to disable.")
    parser.add_argument("--gold-rule-examples", type=int, default=25,
                        help="Number of Gold Rule examples to include. Default uses the current 25.")
    parser.add_argument("--max-query-chars", type=int, default=900)
    parser.add_argument("--max-response-chars", type=int, default=1800)
    parser.add_argument("--max-output-tokens", type=int, default=2048)
    parser.add_argument("--delay", type=float, default=0.3)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--metrics-only", action="store_true",
                        help="Only compute agreement from an existing output file.")
    parser.add_argument("--eval-all", action="store_true",
                        help="Compatibility flag; this script always evaluates the provided gold file.")
    parser.add_argument("--calibration-size", type=int, default=0,
                        help="Deprecated compatibility flag. Training-split calibration is no longer used.")
    args = parser.parse_args()

    if args.calibration_size:
        print("NOTE: --calibration-size is deprecated and ignored. The prompt uses system rules + Gold Rule examples only.")

    gold = load_gold(Path(args.gold))
    if args.limit is not None:
        gold = gold[: args.limit]

    prompt = build_prompt(
        args.gold_rule_path or None,
        args.gold_rule_examples,
        args.max_query_chars,
        args.max_response_chars,
    )
    Path(args.prompt_output).parent.mkdir(parents=True, exist_ok=True)
    Path(args.prompt_output).write_text(prompt, encoding="utf-8")
    prompt_hash = text_sha256(prompt)
    print(f"Gold examples loaded and schema-validated: {len(gold)}")
    print(f"Saved judge prompt -> {args.prompt_output}")
    print(f"Judge prompt SHA256: {prompt_hash}")

    output_path = Path(args.output)
    existing = load_json(output_path) if output_path.exists() else []
    label = f"{args.provider}:{args.model} gold100"
    if args.metrics_only:
        results = keep_successful(existing)
        print(f"Loaded {len(results)} successful existing results from {output_path}")
        compute_agreement(gold, results, label, exclude_ids=set())
        return

    successful = keep_successful(existing)
    results = [result for result in successful if result.get("judge_prompt_sha256") == prompt_hash]
    skipped_errors = len(existing) - len(successful)
    stale_successes = len(successful) - len(results)
    if skipped_errors:
        print(f"Retrying {skipped_errors} previous parse/API errors instead of keeping them in output.")
    if stale_successes:
        print(f"Rerunning {stale_successes} previous successes because the prompt hash changed.")
    done_ids = {int(result["human_eval_id"]) for result in results}

    client = create_client(args.provider, httpx.Timeout(180.0, connect=30.0))
    for item in tqdm(gold, desc=f"[{label}]"):
        hid = int(item["human_eval_id"])
        if hid in done_ids:
            continue
        try:
            result = judge_item(
                client=client,
                provider=args.provider,
                model=args.model,
                prompt=prompt,
                reasoning_effort=args.reasoning_effort,
                item=item,
                max_output_tokens=args.max_output_tokens,
            )
        except Exception as exc:
            print(f"  ERROR id={hid}: {exc}")
            result = {"human_eval_id": item["human_eval_id"], "parse_error": True, "raw_output": str(exc)}
        result["judge_provider"] = args.provider
        result["judge_model"] = args.model
        result["judge_reasoning_effort"] = args.reasoning_effort
        result["judge_prompt_sha256"] = prompt_hash

        results.append(result)
        if not result.get("parse_error"):
            done_ids.add(hid)
        write_json(output_path, results)
        time.sleep(args.delay)

    print(f"Saved {len(results)} results -> {output_path}")
    compute_agreement(gold, results, label, exclude_ids=set())


if __name__ == "__main__":
    main()
