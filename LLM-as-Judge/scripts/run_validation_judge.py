#!/usr/bin/env python3
"""Run the calibrated LLM judge on unlabeled validation response records."""

import argparse
import csv
import json
import time
from pathlib import Path

import httpx
from openai import OpenAI
from tqdm import tqdm

from ft_judge_common import DATA_DIR, SYSTEM_PROMPT, gold_annotation, load_gold, user_message
from run_calibrated_judge import (
    build_calibration_section,
    create_client,
    parse_json_response,
    retry_call,
    select_calibration_items,
)
from run_ensemble_judge import L2_KEYS


DEFAULT_OUTPUT = DATA_DIR / "judge_validation_200_predictions.json"


def load_records(path: Path) -> list[dict]:
    if path.suffix.lower() == ".csv":
        with open(path, "r", encoding="utf-8-sig", newline="") as f:
            return list(csv.DictReader(f))

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, list):
        return data
    raise ValueError(f"Expected a list of records in {path}")


def write_json(path: Path, records: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(records, f, indent=2, ensure_ascii=False)


def write_csv(path: Path, records: list[dict]) -> None:
    if not records:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = []
    for record in records:
        for key in record:
            if key not in fieldnames:
                fieldnames.append(key)
    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(records)


def record_id(record: dict) -> str:
    for key in ["human_eval_id", "final_sample_id", "sample_id", "candidate_id"]:
        value = record.get(key)
        if value not in (None, ""):
            return f"{key}:{value}"
    return f"query:{record.get('query', '')[:80]}"


def validate_records(records: list[dict], input_path: Path) -> None:
    if not records:
        raise ValueError(f"No records found in {input_path}")
    missing_query = [idx for idx, r in enumerate(records, start=1) if not r.get("query")]
    missing_response = [idx for idx, r in enumerate(records, start=1) if not r.get("response")]
    if missing_query:
        raise ValueError(f"{input_path} is missing 'query' for rows: {missing_query[:10]}")
    if missing_response:
        raise ValueError(
            f"{input_path} has no 'response' column/value for {len(missing_response)} rows. "
            "LLM-as-judge needs query-response pairs. First collect model responses with "
            "scripts/02_collect_responses.py, then pass the response JSON/CSV here."
        )


def build_prompt(calibration_size: int, max_query_chars: int, max_response_chars: int) -> str:
    gold = load_gold()
    train_ids_path = DATA_DIR / "ft_judge_train_ids.json"
    if not train_ids_path.exists():
        raise FileNotFoundError(
            f"Missing {train_ids_path}. Run scripts/prepare_ft_judge_data.py first."
        )
    with open(train_ids_path, "r", encoding="utf-8") as f:
        train_ids = [int(value) for value in json.load(f)]
    calibration_items = select_calibration_items(gold, train_ids, calibration_size)
    calibration_section = build_calibration_section(
        calibration_items,
        max_query_chars=max_query_chars,
        max_response_chars=max_response_chars,
    )
    print(f"Calibration examples: {[item['human_eval_id'] for item in calibration_items]}")
    return SYSTEM_PROMPT + calibration_section


def judge_record(
    client: OpenAI,
    provider: str,
    model: str,
    prompt: str,
    reasoning_effort: str,
    record: dict,
) -> dict:
    def call():
        if provider == "openrouter":
            request_kwargs = {
                "model": model,
                "messages": [
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": user_message(record)},
                ],
                "max_tokens": 8192 if reasoning_effort != "none" else 4096,
                "temperature": 0,
            }
            if reasoning_effort != "none":
                request_kwargs["extra_body"] = {"reasoning": {"effort": reasoning_effort}}
            response = client.chat.completions.create(**request_kwargs)
            return (response.choices[0].message.content or "").strip()

        response = client.responses.create(
            model=model,
            instructions=prompt,
            input=user_message(record),
            reasoning={"effort": reasoning_effort},
            max_output_tokens=16384 if reasoning_effort != "none" else 4096,
        )
        return response.output_text.strip()

    return parse_json_response(retry_call(call))


def prediction_fields(result: dict) -> dict:
    keys = ["layer0", "layer0_reason", "layer1", "layer1_reason", *L2_KEYS, "notes"]
    return {key: result.get(key) for key in keys}


def main() -> None:
    parser = argparse.ArgumentParser(description="Run calibrated judge on validation responses")
    parser.add_argument("--input", required=True, help="JSON/CSV with query and response fields")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    parser.add_argument("--provider", choices=["openai", "openrouter"], default="openrouter")
    parser.add_argument("--model", default="openai/gpt-5.3-chat")
    parser.add_argument("--reasoning-effort", default="high", choices=["none", "low", "medium", "high"])
    parser.add_argument("--calibration-size", type=int, default=20)
    parser.add_argument("--max-query-chars", type=int, default=900)
    parser.add_argument("--max-response-chars", type=int, default=1800)
    parser.add_argument("--delay", type=float, default=0.3)
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()

    input_path = Path(args.input)
    records = load_records(input_path)
    if args.limit is not None:
        records = records[: args.limit]
    validate_records(records, input_path)

    output_path = Path(args.output)
    existing = load_records(output_path) if output_path.exists() else []
    done_ids = {record_id(record) for record in existing if not record.get("parse_error")}
    results = list(existing)

    prompt = build_prompt(args.calibration_size, args.max_query_chars, args.max_response_chars)
    prompt_path = output_path.with_suffix(".prompt.txt")
    prompt_path.write_text(prompt, encoding="utf-8")
    print(f"Saved prompt -> {prompt_path}")

    client = create_client(args.provider, httpx.Timeout(180.0, connect=30.0))

    for record in tqdm(records, desc=f"[{args.provider}:{args.model} validation judge]"):
        rid = record_id(record)
        if rid in done_ids:
            continue
        try:
            judgment = judge_record(
                client=client,
                provider=args.provider,
                model=args.model,
                prompt=prompt,
                reasoning_effort=args.reasoning_effort,
                record=record,
            )
            result = {
                **record,
                **prediction_fields(judgment),
                "judge_provider": args.provider,
                "judge_model": args.model,
                "judge_reasoning_effort": args.reasoning_effort,
                "parse_error": False,
            }
        except Exception as exc:
            result = {
                **record,
                "judge_provider": args.provider,
                "judge_model": args.model,
                "judge_reasoning_effort": args.reasoning_effort,
                "parse_error": True,
                "raw_output": str(exc),
            }
            print(f"  ERROR {rid}: {exc}")

        results.append(result)
        if not result.get("parse_error"):
            done_ids.add(rid)
        write_json(output_path, results)
        write_csv(output_path.with_suffix(".csv"), results)
        time.sleep(args.delay)

    print(f"Saved {len(results)} predictions -> {output_path}")
    print(f"Saved CSV -> {output_path.with_suffix('.csv')}")


if __name__ == "__main__":
    main()
