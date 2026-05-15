#!/usr/bin/env python3
"""
Run a prompt-calibrated GPT judge on the held-out gold examples.

This is the fallback when self-serve fine-tuning is unavailable. It uses the
training split created by prepare_ft_judge_data.py as in-context calibration
examples and evaluates only on the held-out split.
"""

import argparse
import json
import os
import time
from pathlib import Path

import httpx
from openai import OpenAI
from tqdm import tqdm

from ft_judge_common import DATA_DIR, SYSTEM_PROMPT, gold_annotation, load_gold, user_message
from run_ensemble_judge import compute_agreement


DEFAULT_OUT = DATA_DIR / "judge_gpt55_calibrated_v5.json"
DEFAULT_ALL_OUT = DATA_DIR / "judge_gpt55_calibrated_v5_all100.json"
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"


def compact_text(text: str, max_chars: int) -> str:
    text = " ".join(str(text).split())
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 20].rstrip() + " ... [truncated]"


def load_json(path: Path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def select_calibration_items(gold: list[dict], train_ids: list[int], max_examples: int) -> list[dict]:
    by_id = {int(item["human_eval_id"]): item for item in gold}

    # Prioritize hard false-positive/false-negative patterns from previous rounds.
    priority_ids = [
        68, 85, 22, 29, 35, 65, 71,
        1, 5, 7, 10, 11, 21, 23, 26, 28, 30, 31, 49,
        53, 56, 58, 60, 62, 70, 72, 73, 76, 77, 86, 88, 96, 97,
    ]
    selected = []
    selected_ids = set()
    for hid in priority_ids:
        if hid in train_ids and hid in by_id and len(selected) < max_examples:
            selected.append(by_id[hid])
            selected_ids.add(hid)

    for hid in train_ids:
        if hid in by_id and hid not in selected_ids and len(selected) < max_examples:
            selected.append(by_id[hid])
            selected_ids.add(hid)

    return selected


def build_calibration_section(items: list[dict], max_query_chars: int, max_response_chars: int) -> str:
    parts = [
        "\n\n========================================",
        "GOLD CALIBRATION EXAMPLES FROM TRAINING SPLIT",
        "========================================",
        "These examples are excluded from evaluation. Use them to calibrate difficult feature boundaries.",
    ]

    for idx, item in enumerate(items, start=1):
        annotation = gold_annotation(item)
        parts.extend([
            f"\n--- Calibration Example {idx}: human_eval_id={item['human_eval_id']} ---",
            "User query:",
            compact_text(item["query"], max_query_chars),
            "LLM response:",
            compact_text(item["response"], max_response_chars),
            "Gold annotation:",
            json.dumps(annotation, ensure_ascii=False),
        ])
    return "\n".join(parts)


def parse_json_response(raw: str) -> dict:
    raw = raw.strip()
    if raw.startswith("```"):
        lines = raw.splitlines()
        if lines and lines[0].strip().startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        raw = "\n".join(lines).strip()
    return json.loads(raw)


def retry_call(fn, max_retries: int = 3, base_delay: float = 2.0):
    last_error = None
    for attempt in range(max_retries + 1):
        try:
            return fn()
        except Exception as exc:
            last_error = exc
            if attempt < max_retries:
                delay = base_delay * (2 ** attempt)
                print(f"    retry {attempt + 1}/{max_retries} after {delay:.1f}s: {exc}", flush=True)
                time.sleep(delay)
    raise last_error


def create_client(provider: str, timeout: httpx.Timeout) -> OpenAI:
    if provider == "openrouter":
        api_key = os.environ.get("OPENROUTER_API_KEY")
        if not api_key:
            raise RuntimeError("Set OPENROUTER_API_KEY before using --provider openrouter.")
        return OpenAI(
            base_url=OPENROUTER_BASE_URL,
            api_key=api_key,
            timeout=timeout,
            default_headers={
                "HTTP-Referer": "https://github.com/PinqiaoWang/LLM_Refusal_Strategy",
                "X-Title": "LLM Refusal Strategy Judge",
            },
        )

    return OpenAI(timeout=timeout)


def judge_item(
    client: OpenAI,
    provider: str,
    model: str,
    prompt: str,
    reasoning_effort: str,
    item: dict,
) -> dict:
    def call():
        if provider == "openrouter":
            request_kwargs = {
                "model": model,
                "messages": [
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": user_message(item)},
                ],
                "max_tokens": 8192 if reasoning_effort != "none" else 4096,
                "temperature": 0,
            }
            if reasoning_effort != "none":
                request_kwargs["extra_body"] = {
                    "reasoning": {"effort": reasoning_effort}
                }
            response = client.chat.completions.create(**request_kwargs)
            return (response.choices[0].message.content or "").strip()

        response = client.responses.create(
            model=model,
            instructions=prompt,
            input=user_message(item),
            reasoning={"effort": reasoning_effort},
            max_output_tokens=16384 if reasoning_effort != "none" else 4096,
        )
        return response.output_text.strip()

    parsed = parse_json_response(retry_call(call))
    parsed["human_eval_id"] = item["human_eval_id"]
    parsed["parse_error"] = False
    return parsed


def load_existing(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run prompt-calibrated GPT judge on holdout")
    parser.add_argument("--provider", choices=["openai", "openrouter"], default="openai")
    parser.add_argument("--model", default="gpt-5.5")
    parser.add_argument("--reasoning-effort", default="high", choices=["none", "low", "medium", "high"])
    parser.add_argument("--holdout", default=str(DATA_DIR / "ft_judge_holdout.json"))
    parser.add_argument("--train-ids", default=str(DATA_DIR / "ft_judge_train_ids.json"))
    parser.add_argument("--output", default=None)
    parser.add_argument("--calibration-size", type=int, default=20)
    parser.add_argument("--eval-all", action="store_true",
                        help="Evaluate all 100 gold examples. This is a diagnostic/full-gold score, not a held-out score.")
    parser.add_argument("--max-query-chars", type=int, default=900)
    parser.add_argument("--max-response-chars", type=int, default=1800)
    parser.add_argument("--delay", type=float, default=0.3)
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()

    gold = load_gold()
    train_ids = [int(value) for value in load_json(Path(args.train_ids))]
    if args.eval_all:
        holdout = gold
        if args.output is None:
            args.output = str(DEFAULT_ALL_OUT)
    else:
        holdout = load_json(Path(args.holdout))
        if args.output is None:
            args.output = str(DEFAULT_OUT)
    if args.limit is not None:
        holdout = holdout[: args.limit]

    calibration_items = select_calibration_items(gold, train_ids, args.calibration_size)
    calibration_section = build_calibration_section(
        calibration_items,
        max_query_chars=args.max_query_chars,
        max_response_chars=args.max_response_chars,
    )
    prompt = SYSTEM_PROMPT + calibration_section

    prompt_path = DATA_DIR / "judge_calibrated_prompt_v5.txt"
    prompt_path.write_text(prompt, encoding="utf-8")
    print(f"Calibration examples: {[item['human_eval_id'] for item in calibration_items]}")
    print(f"Saved calibrated prompt -> {prompt_path}")

    output_path = Path(args.output)
    results = load_existing(output_path)
    done_ids = {int(result["human_eval_id"]) for result in results if not result.get("parse_error")}

    client = create_client(args.provider, httpx.Timeout(180.0, connect=30.0))
    for item in tqdm(holdout, desc=f"[{args.provider}:{args.model} calibrated]"):
        hid = int(item["human_eval_id"])
        if hid in done_ids:
            continue
        try:
            result = judge_item(client, args.provider, args.model, prompt, args.reasoning_effort, item)
        except Exception as exc:
            print(f"  ERROR id={hid}: {exc}")
            result = {"human_eval_id": item["human_eval_id"], "parse_error": True, "raw_output": str(exc)}
        results.append(result)
        if not result.get("parse_error"):
            done_ids.add(hid)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        time.sleep(args.delay)

    print(f"Saved {len(results)} results -> {output_path}")
    exclude_ids = set() if args.eval_all else set(train_ids)
    label_prefix = f"{args.provider}:{args.model}"
    label = f"{label_prefix} calibrated all100" if args.eval_all else f"{label_prefix} calibrated holdout"
    compute_agreement(gold, results, label, exclude_ids=exclude_ids)


if __name__ == "__main__":
    main()
