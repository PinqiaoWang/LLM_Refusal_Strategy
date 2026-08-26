#!/usr/bin/env python3
"""Shared utilities for judge scripts."""

import csv
import hashlib
import json
import os
import time
from pathlib import Path
from typing import Dict, List, Optional, Union

import httpx
from openai import OpenAI

from .judge_config import (
    DATA_DIR,
    GOLD_ACTION_MAP,
    GOLD_L1_MAP,
    GOLD_L2_MAP,
    GOLD_PATH,
    L0_LABELS,
    L1_LABELS,
    L2_KEYS,
    OPENROUTER_BASE_URL,
    REQUIRED_GOLD_FIELDS,
)


def compact_text(text: str, max_chars: int) -> str:
    text = " ".join(str(text).split())
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 20].rstrip() + " ... [truncated]"


PathLike = Union[str, Path]


def load_json(path: PathLike):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def write_json(path: PathLike, data) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def load_records(path: PathLike) -> List[Dict]:
    path = Path(path)
    if path.suffix.lower() == ".csv":
        with open(path, "r", encoding="utf-8-sig", newline="") as f:
            return list(csv.DictReader(f))
    data = load_json(path)
    if isinstance(data, list):
        return data
    raise ValueError(f"Expected a list of records in {path}")


def write_csv(path: PathLike, records: List[Dict]) -> None:
    if not records:
        return
    path = Path(path)
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


def validate_gold_schema(gold: List[Dict]) -> None:
    if not gold:
        raise ValueError("gold_100.json is empty.")

    errors = []
    seen_ids = set()
    for idx, item in enumerate(gold, start=1):
        missing = [field for field in REQUIRED_GOLD_FIELDS if field not in item]
        if missing:
            errors.append(f"row {idx}: missing fields {missing}")

        hid = item.get("human_eval_id")
        if hid in seen_ids:
            errors.append(f"row {idx}: duplicate human_eval_id {hid}")
        seen_ids.add(hid)

        action = normalize_layer0(item.get("gold_action"))
        if action not in L0_LABELS:
            errors.append(f"row {idx}: invalid gold_action {item.get('gold_action')!r}")

        if action == "Non-compliance":
            layer1 = normalize_layer1(item.get("gold_refusal_basis"))
            if layer1 not in L1_LABELS:
                errors.append(f"row {idx}: invalid gold_refusal_basis {item.get('gold_refusal_basis')!r}")
            for feature, gold_key in GOLD_L2_MAP.items():
                value = item.get(gold_key)
                if value not in (0, 1, "0", "1"):
                    errors.append(f"row {idx}: invalid {gold_key} for {feature}: {value!r}")

    if errors:
        preview = "\n".join(errors[:20])
        suffix = f"\n... plus {len(errors) - 20} more" if len(errors) > 20 else ""
        raise ValueError(f"Gold schema validation failed:\n{preview}{suffix}")


def load_gold(path: PathLike = GOLD_PATH) -> List[Dict]:
    gold = load_json(path)
    validate_gold_schema(gold)
    return gold


def normalize_layer0(value) -> Optional[str]:
    return GOLD_ACTION_MAP.get(value, value)


def normalize_layer1(value) -> Optional[str]:
    return GOLD_L1_MAP.get(value, value)


def gold_feature_value(item: dict, feature: str):
    value = item.get(GOLD_L2_MAP[feature])
    return None if value is None else int(value)


def gold_annotation(item: dict) -> dict:
    layer0 = normalize_layer0(item["gold_action"])
    result = {
        "layer0": layer0,
        "layer0_reason": f"Human gold annotation labels the action as {layer0}.",
        "layer1": None,
        "layer1_reason": None,
    }

    if layer0 == "Non-compliance":
        layer1 = normalize_layer1(item.get("gold_refusal_basis"))
        result["layer1"] = layer1
        result["layer1_reason"] = (
            f"Human gold annotation labels the refusal rationale as {layer1}."
            if layer1 else None
        )
        for feature in L2_KEYS:
            value = gold_feature_value(item, feature)
            result[feature] = 0 if value is None else value
    else:
        for feature in L2_KEYS:
            result[feature] = None

    result["notes"] = "Gold annotation converted to judge JSON."
    return result


def user_message(item: dict) -> str:
    return f"User query:\n{item['query']}\n\nLLM response:\n{item['response']}"


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


def normalize_binary_value(value, feature: str) -> int:
    if value in (0, 1):
        return int(value)
    if isinstance(value, str) and value.strip() in {"0", "1"}:
        return int(value.strip())
    raise ValueError(f"Non-compliance output must label {feature} as 0 or 1, got {value!r}")


def validate_judge_output(parsed: dict) -> dict:
    layer0 = parsed.get("layer0")
    if layer0 not in L0_LABELS:
        raise ValueError(f"Invalid layer0: {layer0!r}")

    if layer0 != "Non-compliance":
        parsed["layer1"] = None
        parsed["layer1_reason"] = None
        for feature in L2_KEYS:
            parsed[feature] = None
        return parsed

    layer1 = parsed.get("layer1")
    if layer1 not in L1_LABELS:
        raise ValueError(f"Non-compliance output must include valid layer1, got {layer1!r}")

    for feature in L2_KEYS:
        parsed[feature] = normalize_binary_value(parsed.get(feature), feature)

    if parsed["explicit_nc"] + parsed["implicit_nc"] != 1:
        raise ValueError("Non-compliance output must set exactly one of explicit_nc/implicit_nc to 1.")
    return parsed


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


def retry_parse_call(fn, max_retries: int = 5, base_delay: float = 1.0) -> dict:
    last_error = None
    last_raw = ""
    for attempt in range(max_retries + 1):
        raw = retry_call(fn)
        last_raw = raw
        try:
            return validate_judge_output(parse_json_response(raw))
        except (json.JSONDecodeError, ValueError, TypeError) as exc:
            last_error = exc
            if attempt < max_retries:
                delay = base_delay * (2 ** attempt)
                print(f"    parse retry {attempt + 1}/{max_retries} after {delay:.1f}s: {exc}", flush=True)
                time.sleep(delay)
    raise ValueError(f"{last_error}; raw output starts with: {last_raw[:1000]!r}")


def create_client(provider: str, timeout: httpx.Timeout) -> OpenAI:
    from .env import load_env_file

    load_env_file()
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


def keep_successful(records: List[Dict]) -> List[Dict]:
    return [record for record in records if not record.get("parse_error")]


def record_id(record: dict) -> str:
    for key in ["human_eval_id", "final_sample_id", "sample_id", "candidate_id"]:
        value = record.get(key)
        if value not in (None, ""):
            return f"{key}:{value}"
    return f"query:{record.get('query', '')[:80]}"


def text_sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()
