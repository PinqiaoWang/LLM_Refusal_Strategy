#!/usr/bin/env python3
"""Analyze robustness across the independent May and August response runs.

The script reports (1) May 200 versus August 262 and (2) paired repeated-
generation stability on the shared 138 queries for the 13 rerun models from
the main analysis. 
Layer 1 and Layer 2 rates are conditional on responses judged Non-compliance.
Judge errors and missing-response skips are excluded from rate denominators.
"""

import argparse
import json
import sys
import unicodedata
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
CAMERA = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from utils.judge_config import L2_KEYS  # noqa: E402

L0 = ["Full compliance", "Partial compliance", "Non-compliance"]
L1 = ["Bare", "Capacity-based", "Policy-based", "Ethics-based"]
EXPECTED_MODELS = 13
EXPECTED_MAY = 200
EXPECTED_AUGUST = 262
EXPECTED_SHARED = 138
PRIMARY_EXCLUSIONS = set()


def model_key(path):
    return path.name.removeprefix("responses_").removesuffix(".judged.json")


def query_key(value):
    """Normalize formatting only; do not fuzzy-match different prompts."""
    value = unicodedata.normalize("NFKC", value or "")
    return " ".join(value.split()).casefold()


def load(path):
    """Deduplicate resumed attempts, preferring a valid judgment."""
    records = json.loads(path.read_text(encoding="utf-8"))
    grouped = {}
    for record in records:
        key = query_key(record.get("query"))
        if not key:
            raise ValueError(f"{path}: record has no query text")
        grouped.setdefault(key, []).append(record)

    output = []
    for key, attempts in grouped.items():
        valid = [row for row in attempts if not row.get("parse_error")]
        if len(valid) > 1:
            raise ValueError(f"{path}: duplicate valid query: {key[:80]}")
        output.append(valid[0] if valid else attempts[-1])
    return output


def discover(directory):
    return {model_key(path): path for path in Path(directory).glob("responses_*.judged.json")}


def may_paths(primary_dir, extra_dir):
    paths = discover(primary_dir)
    for model, path in discover(extra_dir).items():
        paths.setdefault(model, path)
    return paths


def validate_query_sets(data, label):
    expected = None
    for model, rows in data.items():
        keys = {query_key(row["query"]) for row in rows}
        if len(keys) != len(rows):
            raise ValueError(f"{label}/{model}: duplicate normalized query text")
        if expected is None:
            expected = keys
        elif keys != expected:
            raise ValueError(f"{label}: models do not share one query set ({model} differs)")


def load_datasets(args):
    may_available = may_paths(args.may_dir, args.may_extra_dir)
    august_old = discover(args.august_old_dir)
    august_new = discover(args.august_new_dir)
    if august_old.keys() != august_new.keys():
        missing_old = sorted(august_new.keys() - august_old.keys())
        missing_new = sorted(august_old.keys() - august_new.keys())
        raise ValueError(f"August shard mismatch; missing old={missing_old}, missing new={missing_new}")

    requested = {item.strip() for item in args.models.split(",") if item.strip()}
    models = sorted((august_old.keys() & may_available.keys()) - PRIMARY_EXCLUSIONS)
    if requested:
        missing = requested - set(models)
        if missing:
            raise ValueError("Requested models absent from a run: " + ", ".join(sorted(missing)))
        models = sorted(requested)
    elif len(models) != EXPECTED_MODELS and not args.allow_incomplete:
        raise ValueError(f"Expected {EXPECTED_MODELS} common models; found {len(models)}: {models}")

    may, august = {}, {}
    for model in models:
        may[model] = load(may_available[model])
        august[model] = load(august_old[model]) + load(august_new[model])
        if not args.allow_incomplete and len(may[model]) != EXPECTED_MAY:
            raise ValueError(f"{model}: expected {EXPECTED_MAY} May queries; found {len(may[model])}")
        if not args.allow_incomplete and len(august[model]) != EXPECTED_AUGUST:
            raise ValueError(f"{model}: expected {EXPECTED_AUGUST} August queries; found {len(august[model])}")

    validate_query_sets(may, "May")
    validate_query_sets(august, "August")
    may_queries = {query_key(row["query"]) for row in may[models[0]]}
    august_queries = {query_key(row["query"]) for row in august[models[0]]}
    shared = may_queries & august_queries
    if not args.allow_incomplete and len(shared) != EXPECTED_SHARED:
        raise ValueError(f"Expected {EXPECTED_SHARED} shared queries; found {len(shared)}")
    return models, may, august, may_queries, august_queries, shared


def subset(records, query_keys):
    return [row for row in records if query_key(row["query"]) in query_keys]


def rates(records):
    judged = [r for r in records if not r.get("parse_error") and not r.get("judge_skipped")]
    nc = [r for r in judged if r.get("layer0") == "Non-compliance"]
    l0_counts = Counter(r.get("layer0") for r in judged)
    l1_counts = Counter(r.get("layer1") for r in nc)

    def divide(count, denominator):
        return count / denominator if denominator else float("nan")

    return {
        "n_records": len(records),
        "n_judged": len(judged),
        "n_non_compliance": len(nc),
        "n_judge_skipped": sum(bool(r.get("judge_skipped")) for r in records),
        "n_parse_error": sum(bool(r.get("parse_error")) for r in records),
        "layer0": {label: divide(l0_counts[label], len(judged)) for label in L0},
        "layer1": {label: divide(l1_counts[label], len(nc)) for label in L1},
        "layer2": {
            feature: divide(sum(r.get(feature) == 1 for r in nc), len(nc))
            for feature in L2_KEYS
        },
    }


def summarize(data):
    return {model: rates(rows) for model, rows in data.items()}


def matrix(summaries, layer, features, models):
    return pd.DataFrame(
        {model: [summaries[model][layer][feature] for feature in features] for model in models},
        index=pd.Index(features, name="feature"),
    )


def compare_matrices(first_matrix, second_matrix, first, second, layer, labels):
    rows = []
    for feature in first_matrix.index:
        for model in first_matrix.columns:
            old, new = first_matrix.loc[feature, model], second_matrix.loc[feature, model]
            if pd.isna(old) or pd.isna(new):
                continue
            rows.append({
                "layer": layer, "feature": feature, "model": model,
                f"{labels[0]}_rate": old, f"{labels[1]}_rate": new,
                "delta_pp": 100 * (new - old),
                "absolute_delta_pp": 100 * abs(new - old),
                f"n_non_compliance_{labels[0]}": first[model]["n_non_compliance"],
                f"n_non_compliance_{labels[1]}": second[model]["n_non_compliance"],
            })
    differences = pd.DataFrame(rows)
    first_values = differences[f"{labels[0]}_rate"]
    second_values = differences[f"{labels[1]}_rate"]
    maximum = differences.loc[differences["absolute_delta_pp"].idxmax()]
    summary = {
        "layer": layer,
        "n_cells": len(differences),
        "pearson_r": first_values.corr(second_values, method="pearson"),
        "spearman_rho": first_values.rank(method="average").corr(
            second_values.rank(method="average"), method="pearson"
        ),
        "mean_absolute_pp_difference": differences["absolute_delta_pp"].mean(),
        "maximum_absolute_pp_difference": maximum["absolute_delta_pp"],
        "maximum_model": maximum["model"],
        "maximum_feature": maximum["feature"],
    }
    return differences, summary


def cohen_kappa(left, right):
    if not left:
        return float("nan")
    labels = sorted(set(left) | set(right), key=str)
    observed = np.mean(np.asarray(left, dtype=object) == np.asarray(right, dtype=object))
    expected = sum((left.count(x) / len(left)) * (right.count(x) / len(right)) for x in labels)
    return (observed - expected) / (1 - expected) if expected < 1 else float("nan")


def paired_agreement(may, august, models, shared):
    l0_rows, l1_rows, l2_rows, transitions = [], [], [], []
    for model in models:
        may_map = {query_key(row["query"]): row for row in subset(may[model], shared)}
        aug_map = {query_key(row["query"]): row for row in subset(august[model], shared)}
        valid_pairs = [
            (may_map[key], aug_map[key]) for key in sorted(shared)
            if not may_map[key].get("parse_error") and not may_map[key].get("judge_skipped")
            and not aug_map[key].get("parse_error") and not aug_map[key].get("judge_skipped")
        ]
        left = [a.get("layer0") for a, _ in valid_pairs]
        right = [b.get("layer0") for _, b in valid_pairs]
        left_nc = [x == "Non-compliance" for x in left]
        right_nc = [x == "Non-compliance" for x in right]
        l0_rows.append({
            "model": model, "n_shared": len(shared), "n_valid_pairs": len(valid_pairs),
            "layer0_exact_agreement": np.mean(np.asarray(left) == np.asarray(right)) if left else np.nan,
            "layer0_kappa": cohen_kappa(left, right),
            "binary_nc_agreement": np.mean(np.asarray(left_nc) == np.asarray(right_nc)) if left else np.nan,
            "binary_nc_kappa": cohen_kappa(left_nc, right_nc),
            "both_nc": sum(a and b for a, b in zip(left_nc, right_nc)),
            "may_nc_august_not_nc": sum(a and not b for a, b in zip(left_nc, right_nc)),
            "may_not_nc_august_nc": sum(not a and b for a, b in zip(left_nc, right_nc)),
        })
        counts = Counter(zip(left, right))
        transitions.extend({
            "model": model, "may_layer0": a, "august_layer0": b,
            "count": n, "rate_among_valid_pairs": n / len(valid_pairs),
        } for (a, b), n in sorted(counts.items()))

        both_nc = [(a, b) for a, b in valid_pairs if a.get("layer0") == b.get("layer0") == "Non-compliance"]
        l1_left = [a.get("layer1") for a, _ in both_nc]
        l1_right = [b.get("layer1") for _, b in both_nc]
        l1_rows.append({
            "model": model, "n_both_non_compliance": len(both_nc),
            "layer1_exact_agreement": np.mean(np.asarray(l1_left) == np.asarray(l1_right)) if l1_left else np.nan,
            "layer1_kappa": cohen_kappa(l1_left, l1_right),
        })
        for feature in L2_KEYS:
            feature_left = [a.get(feature) == 1 for a, _ in both_nc]
            feature_right = [b.get(feature) == 1 for _, b in both_nc]
            l2_rows.append({
                "model": model, "feature": feature, "n_both_non_compliance": len(both_nc),
                "agreement": np.mean(np.asarray(feature_left) == np.asarray(feature_right)) if feature_left else np.nan,
                "kappa": cohen_kappa(feature_left, feature_right),
                "may_rate": np.mean(feature_left) if feature_left else np.nan,
                "august_rate": np.mean(feature_right) if feature_right else np.nan,
            })
    return tuple(pd.DataFrame(rows) for rows in (l0_rows, l1_rows, l2_rows, transitions))


def write_rate_rows(path, datasets):
    rows = []
    for dataset, summaries in datasets:
        for model, summary in summaries.items():
            rows.append({
                "dataset": dataset, "model": model,
                **{name: summary[name] for name in (
                    "n_records", "n_judged", "n_non_compliance",
                    "n_judge_skipped", "n_parse_error",
                )},
                **{f"{label}_rate": summary["layer0"][label] for label in L0},
            })
    pd.DataFrame(rows).to_csv(path, index=False)


def run_profile_comparison(prefix, first_name, second_name, first, second, models, out):
    labels = (first_name.lower(), second_name.lower())
    write_rate_rows(out / f"{prefix}_response_rates.csv", [(first_name, first), (second_name, second)])
    differences, summaries = [], []
    for layer, features in (("layer0", L0), ("layer1", L1), ("layer2", L2_KEYS)):
        first_matrix = matrix(first, layer, features, models)
        second_matrix = matrix(second, layer, features, models)
        first_matrix.to_csv(out / f"{prefix}_{layer}_{labels[0]}_matrix.csv")
        second_matrix.to_csv(out / f"{prefix}_{layer}_{labels[1]}_matrix.csv")
        diff, summary = compare_matrices(first_matrix, second_matrix, first, second, layer, labels)
        differences.append(diff)
        summaries.append(summary)
    pd.concat(differences, ignore_index=True).to_csv(out / f"{prefix}_cell_differences.csv", index=False)
    pd.DataFrame(summaries).to_csv(out / f"{prefix}_stability_summary.csv", index=False)
    return summaries


def overlap_audit(may, august, model, may_queries, august_queries):
    may_map = {query_key(row["query"]): row for row in may[model]}
    aug_map = {query_key(row["query"]): row for row in august[model]}
    rows = []
    for key in sorted(may_queries | august_queries):
        left, right = may_map.get(key), aug_map.get(key)
        row = left or right
        rows.append({
            "query_key": key, "query": row.get("query"),
            "membership": "shared" if left and right else ("may_only" if left else "august_only"),
            "source": row.get("source"), "candidate_id": row.get("candidate_id"),
            "harm_category": row.get("primary_llama_guard_category_name"),
            "may_final_sample_id": left.get("final_sample_id") if left else None,
            "august_final_sample_id": right.get("final_sample_id") if right else None,
        })
    return pd.DataFrame(rows)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--may-dir", default=str(ROOT / "data/annotations"))
    parser.add_argument("--may-extra-dir", default=str(ROOT / "data/annotations/additional_models_expo_may2025"))
    parser.add_argument("--august-old-dir", default=str(ROOT / "data/annotations/expanded_aug2026_old200"))
    parser.add_argument("--august-new-dir", default=str(ROOT / "data/annotations/expanded_aug2026_new62"))
    parser.add_argument("--out-dir", default=str(CAMERA / "may_august_robustness"))
    parser.add_argument("--models", default="", help="Comma-separated model keys")
    parser.add_argument("--allow-incomplete", action="store_true")
    args = parser.parse_args()

    models, may, august, may_queries, august_queries, shared = load_datasets(args)
    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    overlap_audit(may, august, models[0], may_queries, august_queries).to_csv(
        out / "query_overlap_audit.csv", index=False
    )

    overall_summaries = run_profile_comparison(
        "overall", "May200", "August262", summarize(may), summarize(august), models, out
    )
    may_shared = {model: subset(rows, shared) for model, rows in may.items()}
    august_shared = {model: subset(rows, shared) for model, rows in august.items()}
    shared_summaries = run_profile_comparison(
        "shared138", "May", "August", summarize(may_shared), summarize(august_shared), models, out
    )

    l0, l1, l2, transitions = paired_agreement(may, august, models, shared)
    l0.to_csv(out / "shared138_layer0_agreement_by_model.csv", index=False)
    l1.to_csv(out / "shared138_layer1_agreement_by_model.csv", index=False)
    l2.to_csv(out / "shared138_layer2_agreement_by_model_feature.csv", index=False)
    transitions.to_csv(out / "shared138_layer0_transitions.csv", index=False)

    overall_l2 = next(row for row in overall_summaries if row["layer"] == "layer2")
    shared_l2 = next(row for row in shared_summaries if row["layer"] == "layer2")
    lines = [
        "# May-August robustness analysis", "", f"Models compared: {len(models)}", "",
        f"Query overlap: {len(shared)} shared, {len(may_queries - shared)} May-only, "
        f"{len(august_queries - shared)} August-only.", "",
        "## May 200 versus August 262", "",
        f"- Layer 2 Pearson r: {overall_l2['pearson_r']:.4f}",
        f"- Layer 2 Spearman rho: {overall_l2['spearman_rho']:.4f}",
        f"- Layer 2 mean absolute difference: {overall_l2['mean_absolute_pp_difference']:.2f} pp",
        f"- Layer 2 maximum absolute difference: {overall_l2['maximum_absolute_pp_difference']:.2f} pp "
        f"({overall_l2['maximum_model']} x {overall_l2['maximum_feature']})", "",
        "## Shared 138 repeated generation", "",
        f"- Layer 2 Pearson r: {shared_l2['pearson_r']:.4f}",
        f"- Layer 2 Spearman rho: {shared_l2['spearman_rho']:.4f}",
        f"- Layer 2 mean absolute difference: {shared_l2['mean_absolute_pp_difference']:.2f} pp",
        f"- Mean Layer 0 exact agreement across models: {l0['layer0_exact_agreement'].mean():.4f}",
        f"- Mean binary NC agreement across models: {l0['binary_nc_agreement'].mean():.4f}", "",
        "Rates exclude judge/API errors and missing-response skips. Layer 1 and Layer 2 rates "
        "are conditional on Non-compliance within each run. Response-level Layer 1 and Layer 2 "
        "agreement is restricted to pairs judged Non-compliance in both runs.",
    ]
    (out / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"Compared {len(models)} models: May={len(may_queries)}, August={len(august_queries)}")
    print(f"Overlap: shared={len(shared)}, May-only={len(may_queries-shared)}, "
          f"August-only={len(august_queries-shared)}")
    print(f"Overall Layer 2 Pearson r: {overall_l2['pearson_r']:.4f}")
    print(f"Shared-138 Layer 2 Pearson r: {shared_l2['pearson_r']:.4f}")
    print(f"Wrote outputs to {out}")


if __name__ == "__main__":
    main()
