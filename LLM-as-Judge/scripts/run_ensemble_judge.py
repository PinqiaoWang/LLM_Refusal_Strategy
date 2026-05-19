#!/usr/bin/env python3
"""Agreement metrics and optional majority vote for judge outputs."""

import argparse
from collections import Counter
from pathlib import Path

from judge_config import DATA_DIR, GOLD_L2_MAP, L0_LABELS, L1_LABELS, L2_KEYS
from judge_utils import load_gold, load_json, normalize_layer0, normalize_layer1, write_json


def cohens_kappa(y_gold, y_pred, labels=None):
    if labels is None:
        labels = sorted(set(y_gold) | set(y_pred))
    n = len(y_gold)
    if n == 0:
        return float("nan"), []
    label_to_idx = {label: idx for idx, label in enumerate(labels)}
    k = len(labels)
    cm = [[0] * k for _ in range(k)]
    for gold, pred in zip(y_gold, y_pred):
        gi = label_to_idx.get(gold)
        pi = label_to_idx.get(pred)
        if gi is not None and pi is not None:
            cm[gi][pi] += 1
    po = sum(cm[i][i] for i in range(k)) / n
    pe = sum((sum(cm[i]) * sum(cm[j][i] for j in range(k))) / (n * n) for i in range(k))
    kappa = 1.0 if pe == 1.0 else (po - pe) / (1 - pe)
    return kappa, cm


def binary_kappa(y_gold, y_pred):
    kappa, _ = cohens_kappa(y_gold, y_pred, labels=[0, 1])
    return kappa


def majority_vote_ensemble(judge_results_list, judge_names):
    judge_maps = []
    for results in judge_results_list:
        jmap = {}
        for result in results:
            if not result.get("parse_error"):
                jmap[int(result["human_eval_id"])] = result
        judge_maps.append(jmap)

    all_ids = sorted(set().union(*(set(jmap) for jmap in judge_maps)))
    ensemble = []
    for hid in all_ids:
        votes = [jmap.get(hid) for jmap in judge_maps]
        votes = [vote for vote in votes if vote is not None]
        if not votes:
            continue

        result = {"human_eval_id": hid, "parse_error": False, "n_judges": len(votes)}
        l0_votes = [vote.get("layer0") for vote in votes if vote.get("layer0")]
        result["layer0"] = Counter(l0_votes).most_common(1)[0][0] if l0_votes else None
        result["layer0_reason"] = next(
            (vote.get("layer0_reason", "") for vote in votes if vote.get("layer0") == result["layer0"]),
            "",
        )

        if result["layer0"] == "Non-compliance":
            nc_votes = [vote for vote in votes if vote.get("layer0") == "Non-compliance"]
            l1_votes = [vote.get("layer1") for vote in nc_votes if vote.get("layer1")]
            result["layer1"] = Counter(l1_votes).most_common(1)[0][0] if l1_votes else None
            result["layer1_reason"] = next(
                (vote.get("layer1_reason", "") for vote in nc_votes if vote.get("layer1") == result["layer1"]),
                "",
            )
            for feature in L2_KEYS:
                feature_votes = [vote.get(feature) for vote in nc_votes if vote.get(feature) is not None]
                result[feature] = Counter(feature_votes).most_common(1)[0][0] if feature_votes else 0
        else:
            result["layer1"] = None
            result["layer1_reason"] = None
            for feature in L2_KEYS:
                result[feature] = None

        for idx, name in enumerate(judge_names):
            vote = judge_maps[idx].get(hid)
            if vote:
                result[f"{name}_l0"] = vote.get("layer0")
                result[f"{name}_l1"] = vote.get("layer1")
        ensemble.append(result)
    return ensemble


def compute_agreement(gold_data, judge_results, label="", exclude_ids=None):
    if exclude_ids is None:
        exclude_ids = set()
    judge_map = {int(r["human_eval_id"]): r for r in judge_results if not r.get("parse_error")}
    metrics = {}

    l0_gold, l0_pred = [], []
    for gold in gold_data:
        hid = int(gold["human_eval_id"])
        if hid in exclude_ids or hid not in judge_map:
            continue
        l0_gold.append(normalize_layer0(gold["gold_action"]))
        l0_pred.append(judge_map[hid].get("layer0", ""))

    l0_kappa, l0_cm = cohens_kappa(l0_gold, l0_pred, labels=L0_LABELS)
    l0_match = sum(1 for gold, pred in zip(l0_gold, l0_pred) if gold == pred)
    metrics["layer0"] = {
        "accuracy": l0_match / len(l0_gold) if l0_gold else 0,
        "kappa": l0_kappa,
        "n": len(l0_gold),
        "match": l0_match,
        "confusion": l0_cm,
        "labels": L0_LABELS,
    }

    l1_gold, l1_pred = [], []
    for gold in gold_data:
        hid = int(gold["human_eval_id"])
        if hid in exclude_ids or hid not in judge_map:
            continue
        if normalize_layer0(gold["gold_action"]) != "Non-compliance":
            continue
        gold_l1 = normalize_layer1(gold.get("gold_refusal_basis"))
        if gold_l1 is None:
            continue
        l1_gold.append(gold_l1)
        l1_pred.append(judge_map[hid].get("layer1", ""))

    l1_kappa, l1_cm = cohens_kappa(l1_gold, l1_pred, labels=L1_LABELS)
    l1_match = sum(1 for gold, pred in zip(l1_gold, l1_pred) if gold == pred)
    metrics["layer1"] = {
        "accuracy": l1_match / len(l1_gold) if l1_gold else 0,
        "kappa": l1_kappa,
        "n": len(l1_gold),
        "match": l1_match,
        "confusion": l1_cm,
        "labels": L1_LABELS,
    }

    l2_metrics = {}
    for feature, gold_key in GOLD_L2_MAP.items():
        y_gold, y_pred = [], []
        for gold in gold_data:
            hid = int(gold["human_eval_id"])
            if hid in exclude_ids or hid not in judge_map:
                continue
            if normalize_layer0(gold["gold_action"]) != "Non-compliance":
                continue
            gv = gold.get(gold_key)
            pv = judge_map[hid].get(feature)
            if gv is None or pv is None:
                continue
            y_gold.append(int(gv))
            y_pred.append(int(pv))

        match = sum(1 for gold, pred in zip(y_gold, y_pred) if gold == pred)
        l2_metrics[feature] = {
            "accuracy": match / len(y_gold) if y_gold else 0,
            "kappa": binary_kappa(y_gold, y_pred) if y_gold else float("nan"),
            "n": len(y_gold),
            "match": match,
        }
    metrics["layer2"] = l2_metrics

    print(f"\n{'=' * 70}")
    print(f"Agreement Summary: {label}")
    print(f"{'=' * 70}")
    m0 = metrics["layer0"]
    print(f"Layer 0  Accuracy: {m0['accuracy']:.2%} ({m0['match']}/{m0['n']})  Cohen's Kappa: {m0['kappa']:.4f}")
    m1 = metrics["layer1"]
    print(f"Layer 1  Accuracy: {m1['accuracy']:.2%} ({m1['match']}/{m1['n']})  Cohen's Kappa: {m1['kappa']:.4f}")

    print(f"\nLayer 0 Confusion Matrix ({' / '.join(m0['labels'])}):")
    for idx, row in enumerate(m0["confusion"]):
        print(f"  {m0['labels'][idx]:20s}: {row}")

    print(f"\nLayer 1 Confusion Matrix ({' / '.join(m1['labels'])}):")
    for idx, row in enumerate(m1["confusion"]):
        print(f"  {m1['labels'][idx]:15s}: {row}")

    print("\nLayer 2 Feature Agreement (non-compliance only):")
    print(f"  {'Feature':30s} {'Accuracy':>10s} {'Kappa':>10s} {'N':>6s}")
    print(f"  {'-' * 30} {'-' * 10} {'-' * 10} {'-' * 6}")
    for feature in L2_KEYS:
        metric = l2_metrics[feature]
        kappa = metric["kappa"]
        kstr = f"{kappa:.4f}" if not (kappa != kappa) else "N/A"
        print(f"  {feature:30s} {metric['accuracy']:>9.2%} {kstr:>10s} {metric['n']:>6d}")

    return metrics


def main() -> None:
    parser = argparse.ArgumentParser(description="Analyze judge output agreement or build majority vote")
    parser.add_argument("--gold", default=str(DATA_DIR / "gold_100.json"))
    parser.add_argument("--results", nargs="+", required=True,
                        help="One or more judge result JSON files.")
    parser.add_argument("--names", nargs="*", default=None,
                        help="Display names matching --results.")
    parser.add_argument("--ensemble-output", default=None,
                        help="Optional path for majority-vote output when 2+ result files are provided.")
    args = parser.parse_args()

    gold = load_gold(args.gold)
    result_paths = [Path(path) for path in args.results]
    names = args.names or [path.stem for path in result_paths]
    if len(names) != len(result_paths):
        raise ValueError("--names must have the same length as --results.")

    all_results = [load_json(path) for path in result_paths]
    for name, results in zip(names, all_results):
        compute_agreement(gold, results, name)

    if len(all_results) >= 2 and args.ensemble_output:
        ensemble = majority_vote_ensemble(all_results, names)
        write_json(args.ensemble_output, ensemble)
        compute_agreement(gold, ensemble, "ENSEMBLE")
        print(f"Saved ensemble -> {args.ensemble_output}")


if __name__ == "__main__":
    main()
