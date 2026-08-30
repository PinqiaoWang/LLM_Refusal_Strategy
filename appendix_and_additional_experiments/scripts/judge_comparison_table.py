#!/usr/bin/env python3
"""Generate CSV summaries for judge selection and cross-family validation."""

import csv
import math
import sys
from collections import defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from utils.judge_config import DATA_DIR, GOLD_L2_MAP, L0_LABELS, L1_LABELS, L2_KEYS  # noqa: E402
from utils.judge_metrics import cohens_kappa  # noqa: E402
from utils.judge_utils import load_gold, load_json, normalize_layer0, normalize_layer1  # noqa: E402

OUT_DIR = Path(__file__).resolve().parents[1]

JUDGE_SELECTION = [
    ("GPT-5.3, reasoning", DATA_DIR / "judge_calibrated_gold100.json"),
    ("GPT-5.5, non-reasoning", DATA_DIR / "judge_compare_gpt55_currentprompt_gold100_none_reasoning.json"),
]

CROSS_FAMILY = [
    ("Claude Opus 4.8", DATA_DIR / "judge_compare_claude_opus48_gold100_none_reasoning.json"),
    ("GPT-5.5", DATA_DIR / "judge_compare_gpt55_currentprompt_gold100_none_reasoning.json"),
]

LABELS = [
    ("Layer 0 action", "layer0"),
    ("Layer 1 rationale", "layer1"),
    ("Explicit non-compliance", "explicit_nc"),
    ("Implicit non-compliance", "implicit_nc"),
    ("Apology / regret", "apology"),
    ("Hedge / epistemic softener", "hedge"),
    ("Explanatory preface", "explanatory_preface"),
    ("Positive alignment", "positive_alignment"),
    ("Solidarity / empathy", "solidarity"),
    ("Negative stance", "negative_stance"),
    ("Executed alternative", "executed_alternative"),
    ("Alternative offer", "alternative_offer"),
    ("Normative suggestion", "normative_suggestion"),
    ("Statement of principle", "statement_of_principle"),
    ("Role-based self-positioning", "role_based"),
]

OUTPUTS = [
    "judge_selection_kappa.csv",
    "opus48_content_filter_cases.csv",
    "crossfamily_judge_human_kappa.csv",
    "crossfamily_interjudge_kappa.csv",
]


def kappa_with_labels(y_gold, y_pred, labels):
    if not y_gold:
        return None
    kappa, _ = cohens_kappa(y_gold, y_pred, labels=labels)
    no_variation = (
        math.isclose(kappa, 1.0)
        and len(set(y_gold)) == 1
        and len(set(y_pred)) == 1
    )
    return None if kappa != kappa or no_variation else kappa


def fmt_kappa(value):
    return "N/A" if value is None else f"{value:.3f}"


def fmt_cell(value, n_used, n_eligible):
    return f"{fmt_kappa(value)} ({n_used}/{n_eligible})"


def parsed_map(results):
    return {int(row["human_eval_id"]): row for row in results if not row.get("parse_error")}


def gold_nc(record):
    return normalize_layer0(record["gold_action"]) == "Non-compliance"


def judge_human_metrics(gold, results):
    result_map = parsed_map(results)
    metrics = {}

    gold_values, predictions = [], []
    for record in gold:
        human_id = int(record["human_eval_id"])
        if human_id not in result_map:
            continue
        gold_values.append(normalize_layer0(record["gold_action"]))
        predictions.append(result_map[human_id].get("layer0", ""))
    metrics["layer0"] = (
        kappa_with_labels(gold_values, predictions, L0_LABELS),
        len(gold_values),
        len(gold),
    )

    eligible = [record for record in gold if gold_nc(record)]
    gold_values, predictions = [], []
    for record in eligible:
        human_id = int(record["human_eval_id"])
        if human_id not in result_map:
            continue
        gold_layer1 = normalize_layer1(record.get("gold_refusal_basis"))
        if gold_layer1 is None:
            continue
        gold_values.append(gold_layer1)
        predictions.append(result_map[human_id].get("layer1", ""))
    metrics["layer1"] = (
        kappa_with_labels(gold_values, predictions, L1_LABELS),
        len(gold_values),
        len(eligible),
    )

    for feature in L2_KEYS:
        gold_values, predictions = [], []
        gold_key = GOLD_L2_MAP[feature]
        for record in eligible:
            human_id = int(record["human_eval_id"])
            if human_id not in result_map:
                continue
            prediction = result_map[human_id].get(feature)
            if prediction is None:
                continue
            gold_values.append(int(record[gold_key]))
            predictions.append(int(prediction))
        metrics[feature] = (
            kappa_with_labels(gold_values, predictions, [0, 1]),
            len(gold_values),
            len(eligible),
        )
    return metrics


def interjudge_metrics(gpt_results, opus_results):
    gpt = parsed_map(gpt_results)
    opus = parsed_map(opus_results)
    overlap = sorted(set(gpt) & set(opus))
    metrics = {}

    gpt_values = [gpt[i].get("layer0") for i in overlap]
    opus_values = [opus[i].get("layer0") for i in overlap]
    metrics["layer0"] = kappa_with_labels(gpt_values, opus_values, L0_LABELS)

    both_nc = [
        i for i in overlap
        if gpt[i].get("layer0") == "Non-compliance"
        and opus[i].get("layer0") == "Non-compliance"
    ]
    gpt_values = [gpt[i].get("layer1") for i in both_nc]
    opus_values = [opus[i].get("layer1") for i in both_nc]
    metrics["layer1"] = kappa_with_labels(gpt_values, opus_values, L1_LABELS)

    for feature in L2_KEYS:
        pairs = [
            (gpt[i].get(feature), opus[i].get(feature))
            for i in both_nc
            if gpt[i].get(feature) is not None and opus[i].get(feature) is not None
        ]
        metrics[feature] = kappa_with_labels(
            [int(left) for left, _ in pairs],
            [int(right) for _, right in pairs],
            [0, 1],
        )
    return metrics


def write_csv(path, rows, fieldnames):
    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_judge_selection(gold):
    per_judge = {
        name: judge_human_metrics(gold, load_json(path))
        for name, path in JUDGE_SELECTION
    }
    rows = []
    for display, key in LABELS:
        row = {"label": display}
        for name, _ in JUDGE_SELECTION:
            kappa, n_used, n_eligible = per_judge[name][key]
            row[name] = fmt_cell(kappa, n_used, n_eligible)
        rows.append(row)
    write_csv(
        OUT_DIR / "judge_selection_kappa.csv",
        rows,
        ["label", *[name for name, _ in JUDGE_SELECTION]],
    )


def write_content_filter_cases(gold, opus_results):
    errors = {int(row["human_eval_id"]) for row in opus_results if row.get("parse_error")}
    grouped = defaultdict(lambda: {"n": 0, "category": "", "query": ""})
    for record in gold:
        human_id = int(record["human_eval_id"])
        if human_id not in errors:
            continue
        key = (record.get("category"), " ".join(str(record.get("query", "")).split()))
        grouped[key]["n"] += 1
        grouped[key]["category"] = record.get("category")
        grouped[key]["query"] = key[1]
    rows = sorted(grouped.values(), key=lambda row: (-row["n"], row["category"], row["query"]))
    write_csv(OUT_DIR / "opus48_content_filter_cases.csv", rows, ["category", "n", "query"])


def write_crossfamily_human(gold):
    per_judge = {
        name: judge_human_metrics(gold, load_json(path))
        for name, path in CROSS_FAMILY
    }
    rows = []
    for display, key in LABELS:
        row = {"label": display}
        for name, _ in CROSS_FAMILY:
            kappa, n_used, n_eligible = per_judge[name][key]
            row[name] = fmt_cell(kappa, n_used, n_eligible)
        rows.append(row)
    write_csv(
        OUT_DIR / "crossfamily_judge_human_kappa.csv",
        rows,
        ["label", *[name for name, _ in CROSS_FAMILY]],
    )


def write_interjudge(gold, gpt_results, opus_results):
    interjudge = interjudge_metrics(gpt_results, opus_results)
    opus_human = judge_human_metrics(gold, opus_results)
    rows = []
    for display, key in LABELS:
        human_kappa, _, _ = opus_human[key]
        rows.append({
            "label": display,
            "interjudge_kappa": fmt_kappa(interjudge[key]),
            "claude_human_kappa": fmt_kappa(human_kappa),
        })
    write_csv(
        OUT_DIR / "crossfamily_interjudge_kappa.csv",
        rows,
        ["label", "interjudge_kappa", "claude_human_kappa"],
    )


def main():
    gold = load_gold(DATA_DIR / "gold_100.json")
    opus_results = load_json(DATA_DIR / "judge_compare_claude_opus48_gold100_none_reasoning.json")
    gpt55_results = load_json(DATA_DIR / "judge_compare_gpt55_currentprompt_gold100_none_reasoning.json")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    write_judge_selection(gold)
    write_content_filter_cases(gold, opus_results)
    write_crossfamily_human(gold)
    write_interjudge(gold, gpt55_results, opus_results)
    for output in OUTPUTS:
        print(f"wrote {OUT_DIR / output}")


if __name__ == "__main__":
    main()
