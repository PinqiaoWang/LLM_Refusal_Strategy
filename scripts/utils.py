#!/usr/bin/env python3
import csv
import json
from pathlib import Path
from typing import Iterable


PROMPT_CSV_FIELDS = [
    "sample_id",
    "primary_llama_guard_category",
    "source",
    "query",
]

RESPONSE_CSV_FIELDS = [
    "sample_id",
    "primary_llama_guard_category",
    "source",
    "query",
    "model",
    "response",
]


def load_json_records(path: Path) -> list:
    with open(path, "r", encoding="utf-8") as f:
        records = json.load(f)
    if not isinstance(records, list):
        raise ValueError(f"Expected a list of records in {path}")
    return records


def write_csv(records: Iterable[dict], output_path: Path, fieldnames: list) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(records)


def sampled_prompts_json_to_csv(input_path: str, output_path: str) -> None:
    records = load_json_records(Path(input_path))
    rows = [
        {
            "sample_id": record.get("final_sample_id"),
            "primary_llama_guard_category": record.get("primary_llama_guard_category_name"),
            "source": record.get("source"),
            "query": record.get("query"),
        }
        for record in records
    ]
    write_csv(rows, Path(output_path), PROMPT_CSV_FIELDS)


def iter_openrouter_json_paths(input_path: Path) -> list:
    if input_path.is_dir():
        return sorted(path for path in input_path.glob("*.json") if path.is_file())
    return [input_path]


def openrouter_responses_json_to_csv(input_path: str, output_path: str) -> None:
    rows = []
    for path in iter_openrouter_json_paths(Path(input_path)):
        for record in load_json_records(path):
            rows.append({
                "sample_id": record.get("final_sample_id"),
                "primary_llama_guard_category": record.get("primary_llama_guard_category_name"),
                "source": record.get("source"),
                "query": record.get("query"),
                "model": record.get("model_label") or record.get("model_key") or record.get("model_id"),
                "response": record.get("response", ""),
            })
    write_csv(rows, Path(output_path), RESPONSE_CSV_FIELDS)
