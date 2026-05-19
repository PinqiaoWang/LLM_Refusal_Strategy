#!/usr/bin/env python3
"""Helpers for using the human Gold Rule spreadsheet as judge calibration."""

import json
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd

from .judge_config import DEFAULT_GOLD_RULE_PATH, L2_KEYS


REPO_ROOT = Path(__file__).resolve().parents[2]

GOLD_RULE_L1_MAP = {
    "Ethics-based refusal": "Ethics-based",
    "Policy-based refusal": "Policy-based",
    "Bare Refusal": "Bare",
    "Capacity-based refusal": "Capacity-based",
}

GOLD_RULE_L2_MAP = {
    "explicit_nc": "Explicit non-compliance",
    "implicit_nc": "Implicit non-compliance",
    "apology": "Apology / regret",
    "hedge": "Hedges / epistemic\nsoftener",
    "explanatory_preface": "Preface / delay",
    "positive_alignment": "Positive alignment ",
    "solidarity": "Solidarity / empathy",
    "negative_stance": "Negative stance",
    "executed_alternative": "Executed Alternative ",
    "alternative_offer": "Alternative offer / switch of topic",
    "normative_suggestion": "Normative suggestion ",
    "statement_of_principle": "Statement of principle",
    "role_based": "Role-based self-positioning",
}


def compact_text(text: str, max_chars: int) -> str:
    text = " ".join(str(text).split())
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 20].rstrip() + " ... [truncated]"


def _is_missing(value) -> bool:
    return pd.isna(value)


def load_gold_rule_examples(path=DEFAULT_GOLD_RULE_PATH) -> List[Dict]:
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(
            f"Gold Rule spreadsheet not found: {path}. "
            "Pass --gold-rule-path to use a different location."
        )
    df = pd.read_excel(path, sheet_name=0)
    examples = []
    for idx, row in df.iterrows():
        if _is_missing(row.get("Query")) or _is_missing(row.get("Response")):
            continue

        layer0 = row.get("Action")
        layer1 = None
        if not _is_missing(row.get("refusal basis")):
            layer1 = GOLD_RULE_L1_MAP.get(row.get("refusal basis"), row.get("refusal basis"))

        annotation = {
            "layer0": layer0,
            "layer0_reason": "Human Gold Rule annotation.",
            "layer1": layer1,
            "layer1_reason": "Human Gold Rule annotation." if layer1 else None,
        }
        for feature, column in GOLD_RULE_L2_MAP.items():
            value = row.get(column)
            annotation[feature] = None if _is_missing(value) else int(value)
        annotation["notes"] = "Gold Rule calibration example."

        examples.append({
            "gold_rule_id": idx + 1,
            "query": str(row["Query"]),
            "response": str(row["Response"]),
            "annotation": annotation,
            "data_source": None if _is_missing(row.get("Data source")) else row.get("Data source"),
            "model": None if _is_missing(row.get("Model ")) else row.get("Model "),
            "topic": None if _is_missing(row.get("Unnamed: 19")) else row.get("Unnamed: 19"),
        })
    return examples


def build_gold_rule_section(
    path=DEFAULT_GOLD_RULE_PATH,
    max_examples: Optional[int] = None,
    max_query_chars: int = 900,
    max_response_chars: int = 1800,
) -> str:
    examples = load_gold_rule_examples(path)
    if max_examples is not None:
        examples = examples[:max_examples]

    parts = [
        "\n\n========================================",
        "HUMAN GOLD RULE CALIBRATION EXAMPLES",
        "========================================",
        "These examples come from human annotation and should be treated as binding calibration rules for difficult label boundaries.",
    ]

    for example in examples:
        parts.extend([
            f"\n--- Gold Rule Example {example['gold_rule_id']} ---",
            "User query:",
            compact_text(example["query"], max_query_chars),
            "LLM response:",
            compact_text(example["response"], max_response_chars),
            "Gold annotation:",
            json.dumps(example["annotation"], ensure_ascii=False),
        ])

    return "\n".join(parts)


def gold_rule_summary(path=DEFAULT_GOLD_RULE_PATH) -> Dict:
    examples = load_gold_rule_examples(path)
    summary = {"n": len(examples)}
    for key in ["layer0", "layer1", *L2_KEYS]:
        counts = {}
        for example in examples:
            value = example["annotation"].get(key)
            counts[str(value)] = counts.get(str(value), 0) + 1
        summary[key] = counts
    return summary
