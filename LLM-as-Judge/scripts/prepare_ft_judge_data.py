#!/usr/bin/env python3
"""
Prepare fine-tuning data for the LLM refusal-strategy judge.

The selected training IDs are removed from the holdout evaluation set.
"""

import argparse
import json
from collections import Counter
from pathlib import Path

from ft_judge_common import DATA_DIR, GOLD_ACTION_MAP, GOLD_L1_MAP, GOLD_L2_MAP, L2_KEYS
from ft_judge_common import load_gold, training_messages, write_json


# Hard cases observed in previous judge rounds. These are intentionally used for
# calibration and then excluded from holdout evaluation.
KNOWN_HARD_IDS = {
    1, 3, 4, 5, 7, 9, 10, 11, 14, 16, 21, 22, 23, 26, 28, 29,
    30, 31, 35, 36, 43, 48, 49, 53, 56, 57, 58, 60, 62, 65, 67, 68,
    70, 71, 72, 73, 76, 77, 85, 86, 88, 96, 97,
}

# Keep several implicit-NC positives out of calibration so holdout kappa for
# explicit/implicit remains meaningful.
RESERVED_HOLDOUT_IDS = {22, 29, 35, 71}

DIFFICULT_FEATURES = {
    "normative_suggestion",
    "executed_alternative",
    "alternative_offer",
    "negative_stance",
    "explanatory_preface",
    "positive_alignment",
    "role_based",
    "explicit_nc",
    "implicit_nc",
}


def normalized_layer0(item: dict) -> str:
    return GOLD_ACTION_MAP.get(item["gold_action"], item["gold_action"])


def normalized_layer1(item: dict):
    return GOLD_L1_MAP.get(item.get("gold_refusal_basis"), item.get("gold_refusal_basis"))


def feature_value(item: dict, feature: str):
    value = item.get(GOLD_L2_MAP[feature])
    return None if value is None else int(value)


def score_candidate(item: dict, selected_ids: set[int], coverage: Counter) -> tuple:
    hid = int(item["human_eval_id"])
    if hid in selected_ids:
        return (-1, -hid)

    score = 0
    l0 = normalized_layer0(item)
    l1 = normalized_layer1(item)

    if hid in KNOWN_HARD_IDS:
        score += 20
    if l0 == "Non-compliance":
        score += 4
        if l1:
            score += max(0, 3 - coverage[f"l1:{l1}"])
        for feature in DIFFICULT_FEATURES:
            value = feature_value(item, feature)
            if value is not None:
                score += max(0, 2 - coverage[f"{feature}:{value}"])
                if value == 1:
                    score += 1
    else:
        score += max(0, 4 - coverage[f"l0:{l0}"])

    return (score, -hid)


def update_coverage(item: dict, coverage: Counter) -> None:
    l0 = normalized_layer0(item)
    coverage[f"l0:{l0}"] += 1
    l1 = normalized_layer1(item)
    if l1:
        coverage[f"l1:{l1}"] += 1
    if l0 == "Non-compliance":
        for feature in L2_KEYS:
            value = feature_value(item, feature)
            if value is not None:
                coverage[f"{feature}:{value}"] += 1


def select_train_ids(gold: list[dict], train_size: int) -> list[int]:
    by_id = {int(item["human_eval_id"]): item for item in gold}
    selected: list[int] = []
    selected_ids: set[int] = set()
    coverage = Counter()

    for hid in sorted(KNOWN_HARD_IDS):
        if hid in RESERVED_HOLDOUT_IDS:
            continue
        if hid in by_id and len(selected) < train_size:
            selected.append(hid)
            selected_ids.add(hid)
            update_coverage(by_id[hid], coverage)

    while len(selected) < train_size:
        remaining = [
            item for item in gold
            if (
                int(item["human_eval_id"]) not in selected_ids
                and int(item["human_eval_id"]) not in RESERVED_HOLDOUT_IDS
            )
        ]
        if not remaining:
            remaining = [item for item in gold if int(item["human_eval_id"]) not in selected_ids]
        if not remaining:
            break
        best = max(remaining, key=lambda item: score_candidate(item, selected_ids, coverage))
        hid = int(best["human_eval_id"])
        selected.append(hid)
        selected_ids.add(hid)
        update_coverage(best, coverage)

    return sorted(selected)


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Prepare judge fine-tuning JSONL")
    parser.add_argument("--train-size", type=int, default=40)
    parser.add_argument("--train-jsonl", default=str(DATA_DIR / "ft_judge_train.jsonl"))
    parser.add_argument("--validation-jsonl", default=str(DATA_DIR / "ft_judge_validation.jsonl"))
    parser.add_argument("--holdout-json", default=str(DATA_DIR / "ft_judge_holdout.json"))
    args = parser.parse_args()

    gold = load_gold()
    train_ids = select_train_ids(gold, args.train_size)
    train_id_set = set(train_ids)
    holdout = [item for item in gold if int(item["human_eval_id"]) not in train_id_set]
    train = [item for item in gold if int(item["human_eval_id"]) in train_id_set]

    train_rows = [{"messages": training_messages(item)} for item in train]
    validation_rows = [{"messages": training_messages(item)} for item in holdout]

    write_jsonl(Path(args.train_jsonl), train_rows)
    write_jsonl(Path(args.validation_jsonl), validation_rows)
    write_json(Path(args.holdout_json), holdout)
    write_json(DATA_DIR / "ft_judge_train_ids.json", train_ids)
    write_json(DATA_DIR / "ft_judge_holdout_ids.json", [int(item["human_eval_id"]) for item in holdout])

    print(f"Training examples: {len(train)} -> {args.train_jsonl}")
    print(f"Validation/holdout examples: {len(holdout)} -> {args.validation_jsonl}")
    print(f"Holdout JSON: {args.holdout_json}")

    print("\nTraining ID coverage")
    print("  IDs:", train_ids)
    print("  Layer 0:", dict(Counter(normalized_layer0(item) for item in train)))
    print("  Layer 1:", dict(Counter(normalized_layer1(item) for item in train if normalized_layer1(item))))
    for feature in ["normative_suggestion", "executed_alternative", "alternative_offer", "negative_stance", "role_based"]:
        vals = Counter(feature_value(item, feature) for item in train if feature_value(item, feature) is not None)
        print(f"  {feature}: {dict(vals)}")


if __name__ == "__main__":
    main()
