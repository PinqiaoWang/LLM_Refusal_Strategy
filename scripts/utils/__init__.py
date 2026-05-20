"""Utility helpers shared across pipeline scripts."""

import csv
import json
from pathlib import Path


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


def _load_json_records(path):
    with open(path, "r", encoding="utf-8") as f:
        records = json.load(f)
    if not isinstance(records, list):
        raise ValueError("Expected a list of records in {}".format(path))
    return records


def _write_csv(rows, output_path, fieldnames):
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _iter_paths(input_path):
    p = Path(input_path)
    if p.is_dir():
        return sorted(path for path in p.glob("*.json") if path.is_file())
    return [p]


def sampled_prompts_json_to_csv(input_path, output_path):
    rows = [
        {
            "sample_id": record.get("final_sample_id"),
            "primary_llama_guard_category": record.get("primary_llama_guard_category_name"),
            "source": record.get("source"),
            "query": record.get("query"),
        }
        for record in _load_json_records(Path(input_path))
    ]
    _write_csv(rows, Path(output_path), PROMPT_CSV_FIELDS)


def openrouter_responses_json_to_csv(input_path, output_path):
    rows = []
    for path in _iter_paths(input_path):
        for record in _load_json_records(path):
            rows.append({
                "sample_id": record.get("final_sample_id"),
                "primary_llama_guard_category": record.get("primary_llama_guard_category_name"),
                "source": record.get("source"),
                "query": record.get("query"),
                "model": record.get("model_label") or record.get("model_key") or record.get("model_id"),
                "response": record.get("response", ""),
            })
    _write_csv(rows, Path(output_path), RESPONSE_CSV_FIELDS)
