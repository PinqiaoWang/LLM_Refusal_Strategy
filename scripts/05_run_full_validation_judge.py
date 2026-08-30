#!/usr/bin/env python3
"""Run the calibrated LLM judge on unlabeled validation response records."""

import argparse
import json
import time
from pathlib import Path
from typing import Dict, List, Optional

import httpx
from tqdm import tqdm

from utils.gold_rule_common import build_gold_rule_section
from utils.judge_config import DATA_DIR, DEFAULT_GOLD_RULE_PATH, JUDGE_SYSTEM_PROMPT, L2_KEYS
from utils.judge_utils import (
    create_client,
    load_records,
    record_id,
    retry_parse_call,
    text_sha256,
    user_message,
    write_csv,
    write_json,
)


DEFAULT_OUTPUT = DATA_DIR / "judge_validation_200_predictions.json"


def load_checkpoint(path: Path) -> List[Dict]:
    if not path.exists():
        return []
    records = []
    lines = path.read_text(encoding="utf-8").splitlines()
    for index, line in enumerate(lines):
        if not line.strip():
            continue
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError:
            if index != len(lines) - 1:
                raise
            print(f"WARNING: ignoring an incomplete final checkpoint line in {path}")
    return records


def append_checkpoint(path: Path, record: Dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")


def merge_attempts(records: List[Dict]) -> List[Dict]:
    """Deduplicate canonical and checkpoint rows, preferring a valid attempt."""
    merged = {}
    for record in records:
        key = (record_id(record), record.get("judge_prompt_sha256"))
        previous = merged.get(key)
        if previous is None or previous.get("parse_error") or not record.get("parse_error"):
            merged[key] = record
    return list(merged.values())


def validate_records(records: List[Dict], input_path: Path) -> None:
    if not records:
        raise ValueError(f"No records found in {input_path}")
    missing_query = [idx for idx, r in enumerate(records, start=1) if not r.get("query")]
    missing_response = [idx for idx, r in enumerate(records, start=1) if not r.get("response")]
    if missing_query:
        raise ValueError(f"{input_path} is missing 'query' for rows: {missing_query[:10]}")
    if missing_response:
        print(
            f"WARNING: {input_path} has no response for {len(missing_response)} rows. "
            "Those rows will be marked judge_skipped instead of sent to the judge."
        )


def build_prompt(
    max_query_chars: int,
    max_response_chars: int,
    gold_rule_path: Optional[str],
    gold_rule_examples: Optional[int],
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


def judge_record(
    client,
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

    return retry_parse_call(call)


def prediction_fields(result: dict) -> dict:
    keys = ["layer0", "layer0_reason", "layer1", "layer1_reason", *L2_KEYS, "notes"]
    return {key: result.get(key) for key in keys}


def main() -> None:
    parser = argparse.ArgumentParser(description="Run calibrated judge on validation responses")
    parser.add_argument("--input", required=True, help="JSON/CSV with query and response fields")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    parser.add_argument("--provider", choices=["openai", "openrouter"], default="openrouter")
    parser.add_argument("--model", default="openai/gpt-5.5")
    parser.add_argument("--reasoning-effort", default="none", choices=["none", "low", "medium", "high"])
    parser.add_argument("--calibration-size", type=int, default=0,
                        help="Deprecated compatibility flag. Training-split calibration is no longer used.")
    parser.add_argument("--gold-rule-path", default=str(DEFAULT_GOLD_RULE_PATH),
                        help="Path to human Gold Rule xlsx. Pass an empty string to disable.")
    parser.add_argument("--gold-rule-examples", type=int, default=25,
                        help="Number of Gold Rule examples to include. Default uses the current 25.")
    parser.add_argument("--max-query-chars", type=int, default=900)
    parser.add_argument("--max-response-chars", type=int, default=1800)
    parser.add_argument("--delay", type=float, default=0.3)
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()
    if args.calibration_size:
        print("NOTE: --calibration-size is deprecated and ignored. The prompt uses system rules + Gold Rule examples only.")

    input_path = Path(args.input)
    records = load_records(input_path)
    if args.limit is not None:
        records = records[: args.limit]
    validate_records(records, input_path)

    output_path = Path(args.output)
    checkpoint_path = output_path.with_name(output_path.name + ".checkpoint.jsonl")
    canonical = load_records(output_path) if output_path.exists() else []
    existing = merge_attempts(canonical + load_checkpoint(checkpoint_path))
    prompt = build_prompt(
        args.max_query_chars,
        args.max_response_chars,
        args.gold_rule_path or None,
        args.gold_rule_examples,
    )
    prompt_path = output_path.with_suffix(".prompt.txt")
    prompt_path.parent.mkdir(parents=True, exist_ok=True)
    prompt_path.write_text(prompt, encoding="utf-8")
    prompt_hash = text_sha256(prompt)
    print(f"Saved prompt -> {prompt_path}")
    print(f"Judge prompt SHA256: {prompt_hash}")

    successful = [record for record in existing if not record.get("parse_error")]
    results = [record for record in successful if record.get("judge_prompt_sha256") == prompt_hash]
    skipped_errors = len(existing) - len(successful)
    stale_successes = len(successful) - len(results)
    if skipped_errors:
        print(f"Retrying {skipped_errors} previous parse/API errors instead of keeping them in output.")
    if stale_successes:
        print(f"Rerunning {stale_successes} previous successes because the prompt hash changed.")
    done_ids = {record_id(record) for record in results}

    client = create_client(args.provider, httpx.Timeout(180.0, connect=30.0))

    for record in tqdm(records, desc=f"[{args.provider}:{args.model} validation judge]"):
        rid = record_id(record)
        if rid in done_ids:
            continue
        if not record.get("response"):
            result = {
                **record,
                "judge_provider": args.provider,
                "judge_model": args.model,
                "judge_reasoning_effort": args.reasoning_effort,
                "judge_prompt_sha256": prompt_hash,
                "parse_error": False,
                "judge_skipped": True,
                "skip_reason": "missing response",
            }
            results.append(result)
            done_ids.add(rid)
            append_checkpoint(checkpoint_path, result)
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
                "judge_prompt_sha256": prompt_hash,
                "parse_error": False,
            }
        except Exception as exc:
            result = {
                **record,
                "judge_provider": args.provider,
                "judge_model": args.model,
                "judge_reasoning_effort": args.reasoning_effort,
                "judge_prompt_sha256": prompt_hash,
                "parse_error": True,
                "raw_output": str(exc),
            }
            print(f"  ERROR {rid}: {exc}")

        results.append(result)
        if not result.get("parse_error"):
            done_ids.add(rid)
        append_checkpoint(checkpoint_path, result)
        time.sleep(args.delay)

    # Compact the append-only checkpoint only after the model pass completes.
    # If either final write fails, the journal remains available for resume.
    write_json(output_path, results)
    write_csv(output_path.with_suffix(".csv"), results)
    checkpoint_path.unlink(missing_ok=True)
    print(f"Saved {len(results)} predictions -> {output_path}")
    print(f"Saved CSV -> {output_path.with_suffix('.csv')}")


if __name__ == "__main__":
    main()
