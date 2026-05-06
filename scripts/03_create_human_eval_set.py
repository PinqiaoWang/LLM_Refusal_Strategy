#!/usr/bin/env python3
import argparse
import json
import random
import sys
from collections import Counter
from pathlib import Path
from typing import Optional

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))

from utils import write_csv

DEFAULT_INPUT_DIR = REPO_ROOT / "data" / "responses" / "openrouter" / "sampled_200"
DEFAULT_OUTPUT_PATH = REPO_ROOT / "data" / "annotations" / "human_eval_set_100.json"

OUTPUT_FIELDS = [
    "human_eval_id",
    "sample_id",
    "source",
    "primary_llama_guard_category_name",
    "query",
    "model_label",
    "reasoning",
    "response",
    "finish_reason",
]

def load_response_records(input_dir: Path, pattern: str, include_errors: bool = False) -> list[dict]:
    """Load eligible query-response records from OpenRouter response JSON files."""
    records = []
    files = sorted(input_dir.glob(pattern))
    if not files:
        raise FileNotFoundError(f"No files matching {pattern!r} found in {input_dir}")

    for path in files:
        with open(path, "r", encoding="utf-8") as f:
            file_records = json.load(f)
        if not isinstance(file_records, list):
            raise ValueError(f"Expected a list of records in {path}")
        for record in file_records:
            if not include_errors and record.get("error"):
                continue
            if not record.get("response"):
                continue
            normalized = dict(record)
            normalized["response_file"] = str(path)
            records.append(normalized)

    return records


def get_record_key(record: dict) -> tuple:
    """Return the uniqueness key for one model response to one sampled prompt."""
    return (
        record.get("model_key"),
        record.get("final_sample_id"),
        record.get("query"),
    )


def select_one_for_value(
    records: list[dict],
    selected_keys: set,
    field: str,
    value: str,
    rng: random.Random,
    model_counts: Counter,
    category_counts: Counter,
) -> Optional[dict]:
    """Select one unused record matching a required model or category value."""
    candidates = [
        record for record in records
        if record.get(field) == value and get_record_key(record) not in selected_keys
    ]
    if not candidates:
        return None
    rng.shuffle(candidates)
    candidates.sort(
        key=lambda record: (
            model_counts[record.get("model_key")],
            category_counts[record.get("primary_llama_guard_category")],
        )
    )
    return candidates[0]


def add_selected(
    selected: list[dict],
    selected_keys: set,
    record: dict,
    model_counts: Counter,
    category_counts: Counter,
) -> None:
    """Add a selected record and update model/category coverage counters."""
    selected.append(record)
    selected_keys.add(get_record_key(record))
    model_counts[record.get("model_key")] += 1
    category_counts[record.get("primary_llama_guard_category")] += 1


def sample_human_eval_set(records: list[dict], sample_size: int, seed: int) -> list[dict]:
    """
    Sample a fixed-size human evaluation set with minimum coverage constraints.

    The selection is intentionally coverage-first:
    1. First, select at least one query-response pair from every model_key so
       each model is represented in the human validation set.
    2. Second, select at least one query-response pair from every primary
       Llama Guard harm category not already covered by the model pass.
    3. Finally, fill the remaining slots up to sample_size by preferring
       records from models and harm categories that currently have fewer
       selected examples.

    This guarantees marginal coverage of models and harm categories, but does
    not guarantee every model-category combination because that would require
    substantially more examples than the default 100-row validation set.
    """
    rng = random.Random(seed)
    shuffled = list(records)
    rng.shuffle(shuffled)

    model_keys = sorted({record.get("model_key") for record in records if record.get("model_key")})
    categories = sorted({
        record.get("primary_llama_guard_category")
        for record in records
        if record.get("primary_llama_guard_category")
    })

    if sample_size < max(len(model_keys), len(categories)):
        raise ValueError(
            f"sample_size={sample_size} is too small to guarantee coverage of "
            f"{len(model_keys)} models and {len(categories)} categories"
        )

    selected = []
    selected_keys = set()
    model_counts = Counter()
    category_counts = Counter()

    # Coverage pass 1: guarantee at least one query-response pair from each model.
    for model_key in model_keys:
        record = select_one_for_value(
            shuffled,
            selected_keys,
            "model_key",
            model_key,
            rng,
            model_counts,
            category_counts,
        )
        if record is None:
            raise ValueError(f"Could not cover model_key={model_key}")
        add_selected(selected, selected_keys, record, model_counts, category_counts)

    # Coverage pass 2: guarantee at least one query-response pair from each harm category.
    for category in categories:
        if category_counts[category] > 0:
            continue
        record = select_one_for_value(
            shuffled,
            selected_keys,
            "primary_llama_guard_category",
            category,
            rng,
            model_counts,
            category_counts,
        )
        if record is None:
            raise ValueError(f"Could not cover category={category}")
        add_selected(selected, selected_keys, record, model_counts, category_counts)

    # Fill pass: prefer candidates from currently underrepresented models/categories.
    remaining = [record for record in shuffled if get_record_key(record) not in selected_keys]
    while len(selected) < sample_size and remaining:
        remaining.sort(
            key=lambda record: (
                model_counts[record.get("model_key")]
                + category_counts[record.get("primary_llama_guard_category")],
                model_counts[record.get("model_key")],
                category_counts[record.get("primary_llama_guard_category")],
                rng.random(),
            )
        )
        record = remaining.pop(0)
        add_selected(selected, selected_keys, record, model_counts, category_counts)

    if len(selected) < sample_size:
        raise ValueError(f"Only selected {len(selected)} records, fewer than requested {sample_size}")

    rng.shuffle(selected)
    return selected


def format_human_eval_records(records: list[dict]) -> list[dict]:
    """Keep only the fields needed for human annotation and assign eval IDs."""
    output = []
    for idx, record in enumerate(records, start=1):
        output.append({
            "human_eval_id": idx,
            "sample_id": record.get("final_sample_id"),
            "source": record.get("source"),
            "primary_llama_guard_category_name": record.get("primary_llama_guard_category_name"),
            "query": record.get("query"),
            "model_label": record.get("model_label"),
            "reasoning": record.get("reasoning"),
            "response": record.get("response"),
            "finish_reason": record.get("finish_reason"),
        })
    return output


def save_outputs(records: list[dict], output_path: Path, csv_path: Optional[Path]) -> None:
    """Save the sampled human-eval set as JSON and CSV."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(records, f, indent=2, ensure_ascii=False)
    print(f"Saved {len(records)} human-eval records to {output_path}")

    if csv_path is None:
        csv_path = output_path.with_suffix(".csv")
    write_csv(records, csv_path, OUTPUT_FIELDS)
    print(f"Saved human-eval CSV to {csv_path}")


def print_coverage(records: list[dict]) -> None:
    """Print coverage summaries for models and harm categories."""
    model_counts = Counter(record.get("model_label") for record in records)
    category_counts = Counter(record.get("primary_llama_guard_category_name") for record in records)

    print("\nModel coverage")
    for model_key, count in sorted(model_counts.items()):
        print(f"  {model_key}: {count}")

    print("\nCategory coverage")
    for category, count in sorted(category_counts.items()):
        print(f"  {category}: {count}")


def main() -> None:
    """Parse CLI arguments and create the human evaluation sample."""
    parser = argparse.ArgumentParser(description="Create a human evaluation set from model response files")
    parser.add_argument("--input-dir", default=str(DEFAULT_INPUT_DIR))
    parser.add_argument("--pattern", default="responses_*.json")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT_PATH))
    parser.add_argument("--csv-output", default=None)
    parser.add_argument("--n", type=int, default=100)
    parser.add_argument("--seed", type=int, default=2026)
    parser.add_argument("--include-errors", action="store_true")
    args = parser.parse_args()

    records = load_response_records(
        input_dir=Path(args.input_dir),
        pattern=args.pattern,
        include_errors=args.include_errors,
    )
    print(f"Loaded {len(records)} eligible query-response pairs")

    selected = sample_human_eval_set(records, sample_size=args.n, seed=args.seed)
    output_records = format_human_eval_records(selected)
    save_outputs(output_records, Path(args.output), Path(args.csv_output) if args.csv_output else None)
    print_coverage(output_records)


if __name__ == "__main__":
    main()
