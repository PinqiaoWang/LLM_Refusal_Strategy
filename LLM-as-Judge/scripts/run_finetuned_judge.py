#!/usr/bin/env python3
"""Run a fine-tuned OpenAI judge on the held-out gold examples."""

import argparse
import json
import os
import time
from pathlib import Path

from openai import OpenAI
from tqdm import tqdm

from ft_judge_common import DATA_DIR, SYSTEM_PROMPT, load_gold, user_message
from run_ensemble_judge import compute_agreement


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


def judge_item(client: OpenAI, model: str, item: dict) -> dict:
    def call():
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_message(item)},
            ],
            response_format={"type": "json_object"},
            temperature=0,
            max_tokens=4096,
        )
        return response.choices[0].message.content or ""

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
    parser = argparse.ArgumentParser(description="Run fine-tuned judge on holdout set")
    parser.add_argument("--model", default=os.environ.get("FT_JUDGE_MODEL"))
    parser.add_argument("--input", default=str(DATA_DIR / "ft_judge_holdout.json"))
    parser.add_argument("--output", default=str(DATA_DIR / "judge_ft_v3.json"))
    parser.add_argument("--delay", type=float, default=0.3)
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()

    if not args.model:
        raise RuntimeError("Pass --model <fine_tuned_model> or set FT_JUDGE_MODEL.")

    input_path = Path(args.input)
    output_path = Path(args.output)
    with open(input_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if args.limit is not None:
        data = data[:args.limit]

    results = load_existing(output_path)
    done_ids = {int(result["human_eval_id"]) for result in results if not result.get("parse_error")}
    client = OpenAI()

    for item in tqdm(data, desc=f"[fine-tuned judge: {args.model}]"):
        hid = int(item["human_eval_id"])
        if hid in done_ids:
            continue
        try:
            result = judge_item(client, args.model, item)
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

    gold = load_gold()
    train_ids_path = DATA_DIR / "ft_judge_train_ids.json"
    exclude_ids = set()
    if train_ids_path.exists():
        with open(train_ids_path, "r", encoding="utf-8") as f:
            exclude_ids = {int(value) for value in json.load(f)}
    compute_agreement(gold, results, f"fine-tuned {args.model}", exclude_ids=exclude_ids)


if __name__ == "__main__":
    main()
