#!/usr/bin/env python3
"""Create summary tables and plots for judge reliability and validation outputs."""

import argparse
import contextlib
import io
import json
from collections import Counter
from pathlib import Path

import matplotlib
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from utils.judge_config import DATA_DIR, L2_KEYS
from utils.judge_utils import load_gold
from utils.judge_metrics import compute_agreement


MODEL_ORDER = [
    "Llama 3.1 8B",
    "Llama 3.1 70B",
    "Qwen3-8B",
    "Qwen3-8B + reasoning",
    "Qwen3-32B",
    "Qwen3-32B + reasoning",
    "Claude Opus 4.6",
    "Claude Opus 4.6 + reasoning",
    "GPT 5.3",
    "GPT-5.3 + reasoning",
    "Grok 4.20",
    "Gemini 2.5 Pro",
    "GPT-4o",
    "GPT-5",
    "Claude Sonnet 3.7",
    "Claude Sonnet 4.6",
]


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def safe_model_label(records, fallback):
    for record in records:
        value = record.get("model_label") or record.get("model") or record.get("model_key")
        if value:
            return str(value)
    return fallback


def sorted_models(df):
    present = set(df["model"])
    ordered = [model for model in MODEL_ORDER if model in present]
    leftovers = sorted(present - set(ordered))
    return ordered + leftovers


def summarize_validation(judgments_dir):
    model_rows = []
    l1_rows = []
    l2_rows = []

    for path in sorted(judgments_dir.glob("*.judged.json")):
        records = load_json(path)
        model = safe_model_label(records, path.stem)
        judged = [r for r in records if not r.get("parse_error") and not r.get("judge_skipped")]
        skipped = [r for r in records if r.get("judge_skipped")]
        parse_errors = [r for r in records if r.get("parse_error")]
        l0_counts = Counter(r.get("layer0") for r in judged)
        nc = [r for r in judged if r.get("layer0") == "Non-compliance"]
        l1_counts = Counter(r.get("layer1") for r in nc)

        model_rows.append({
            "model": model,
            "file": path.name,
            "n_total": len(records),
            "n_judged": len(judged),
            "n_skipped_missing_response": len(skipped),
            "n_parse_error": len(parse_errors),
            "full_compliance": l0_counts.get("Full compliance", 0),
            "partial_compliance": l0_counts.get("Partial compliance", 0),
            "non_compliance": l0_counts.get("Non-compliance", 0),
            "full_compliance_rate": l0_counts.get("Full compliance", 0) / len(judged) if judged else 0,
            "partial_compliance_rate": l0_counts.get("Partial compliance", 0) / len(judged) if judged else 0,
            "non_compliance_rate": l0_counts.get("Non-compliance", 0) / len(judged) if judged else 0,
            "bare": l1_counts.get("Bare", 0),
            "capacity_based": l1_counts.get("Capacity-based", 0),
            "policy_based": l1_counts.get("Policy-based", 0),
            "ethics_based": l1_counts.get("Ethics-based", 0),
            "bare_rate_among_nc": l1_counts.get("Bare", 0) / len(nc) if nc else 0,
            "capacity_based_rate_among_nc": l1_counts.get("Capacity-based", 0) / len(nc) if nc else 0,
            "policy_based_rate_among_nc": l1_counts.get("Policy-based", 0) / len(nc) if nc else 0,
            "ethics_based_rate_among_nc": l1_counts.get("Ethics-based", 0) / len(nc) if nc else 0,
        })

        for label in ["Bare", "Capacity-based", "Policy-based", "Ethics-based"]:
            l1_rows.append({
                "model": model,
                "layer1": label,
                "count": l1_counts.get(label, 0),
                "rate_among_non_compliance": l1_counts.get(label, 0) / len(nc) if nc else 0,
            })

        for feature in L2_KEYS:
            count = sum(1 for r in nc if r.get(feature) == 1)
            l2_rows.append({
                "model": model,
                "feature": feature,
                "count": count,
                "n_non_compliance": len(nc),
                "rate_among_non_compliance": count / len(nc) if nc else 0,
            })

    return pd.DataFrame(model_rows), pd.DataFrame(l1_rows), pd.DataFrame(l2_rows)


def compare_pairs(model_df):
    by_model = {row["model"]: row for _, row in model_df.iterrows()}
    pairs = [
        ("H1_size", "Llama 3.1 8B", "Llama 3.1 70B"),
        ("H1_size", "Qwen3-8B", "Qwen3-32B"),
        ("H2_reasoning", "Qwen3-8B", "Qwen3-8B + reasoning"),
        ("H2_reasoning", "Qwen3-32B", "Qwen3-32B + reasoning"),
        ("H2_reasoning", "Claude Opus 4.6", "Claude Opus 4.6 + reasoning"),
        ("H2_reasoning", "GPT 5.3", "GPT-5.3 + reasoning"),
        ("H3_closed_family", "Claude Opus 4.6", "GPT 5.3"),
        ("H3_closed_family", "Claude Opus 4.6", "Grok 4.20"),
        ("H3_closed_family", "Claude Opus 4.6", "Gemini 2.5 Pro"),
        ("H4_time", "GPT-4o", "GPT-5"),
        ("H4_time", "GPT-5", "GPT 5.3"),
        ("H4_time", "Claude Sonnet 3.7", "Claude Sonnet 4.6"),
    ]
    rows = []
    for hypothesis, a, b in pairs:
        if a not in by_model or b not in by_model:
            continue
        ar = by_model[a]
        br = by_model[b]
        rows.append({
            "hypothesis": hypothesis,
            "model_a": a,
            "model_b": b,
            "refusal_rate_a": ar["non_compliance_rate"],
            "refusal_rate_b": br["non_compliance_rate"],
            "delta_b_minus_a": br["non_compliance_rate"] - ar["non_compliance_rate"],
            "n_judged_a": ar["n_judged"],
            "n_judged_b": br["n_judged"],
        })
    return pd.DataFrame(rows)


def reliability_tables(gold_path, result_paths):
    gold = load_gold(gold_path)
    layer_rows = []
    l2_rows = []
    for path in result_paths:
        label = path.stem.replace("judge_compare_", "").replace("_gold100", "")
        results = load_json(path)
        with contextlib.redirect_stdout(io.StringIO()):
            metrics = compute_agreement(gold, results, label, exclude_ids=set())

        for layer in ["layer0", "layer1"]:
            layer_rows.append({
                "judge_result": label,
                "layer": layer,
                "accuracy": metrics[layer]["accuracy"],
                "kappa": metrics[layer]["kappa"],
                "n": metrics[layer]["n"],
                "match": metrics[layer]["match"],
            })
        for feature in L2_KEYS:
            metric = metrics["layer2"][feature]
            l2_rows.append({
                "judge_result": label,
                "feature": feature,
                "accuracy": metric["accuracy"],
                "kappa": metric["kappa"],
                "n": metric["n"],
                "match": metric["match"],
            })
    return pd.DataFrame(layer_rows), pd.DataFrame(l2_rows)


def save_tables(out_dir, model_df, l1_df, l2_df, hypothesis_df, reliability_layer_df, reliability_l2_df):
    out_dir.mkdir(parents=True, exist_ok=True)
    model_df.to_csv(out_dir / "validation_model_summary.csv", index=False)
    l1_df.to_csv(out_dir / "validation_layer1_distribution.csv", index=False)
    l2_df.to_csv(out_dir / "validation_l2_feature_rates.csv", index=False)
    hypothesis_df.to_csv(out_dir / "hypothesis_refusal_rate_comparisons.csv", index=False)
    reliability_layer_df.to_csv(out_dir / "judge_reliability_layer_accuracy_kappa.csv", index=False)
    reliability_l2_df.to_csv(out_dir / "judge_reliability_l2_accuracy_kappa.csv", index=False)

    xlsx_path = out_dir / "analysis_tables.xlsx"
    with pd.ExcelWriter(xlsx_path, engine="openpyxl") as writer:
        model_df.to_excel(writer, sheet_name="model_summary", index=False)
        l1_df.to_excel(writer, sheet_name="layer1_distribution", index=False)
        l2_df.to_excel(writer, sheet_name="l2_feature_rates", index=False)
        hypothesis_df.to_excel(writer, sheet_name="hypothesis_comparisons", index=False)
        reliability_layer_df.to_excel(writer, sheet_name="judge_reliability_layers", index=False)
        reliability_l2_df.to_excel(writer, sheet_name="judge_reliability_l2", index=False)
    return xlsx_path


def plot_refusal_rates(model_df, out_dir):
    df = model_df.copy()
    df["model"] = pd.Categorical(df["model"], categories=sorted_models(df), ordered=True)
    df = df.sort_values("non_compliance_rate", ascending=True)
    fig, ax = plt.subplots(figsize=(9, 6))
    ax.barh(df["model"], df["non_compliance_rate"], color="#4C78A8")
    ax.set_xlabel("Non-compliance rate")
    ax.set_ylabel("")
    ax.set_title("Refusal / Non-compliance Rate by Model")
    ax.xaxis.set_major_formatter(lambda x, pos: f"{x:.0%}")
    fig.tight_layout()
    fig.savefig(out_dir / "plot_refusal_rate_by_model.png", dpi=200)
    plt.close(fig)


def plot_l1_stacked(model_df, out_dir):
    df = model_df.copy()
    order = sorted_models(df)
    df["model"] = pd.Categorical(df["model"], categories=order, ordered=True)
    df = df.sort_values("model")
    cols = [
        "bare_rate_among_nc",
        "capacity_based_rate_among_nc",
        "policy_based_rate_among_nc",
        "ethics_based_rate_among_nc",
    ]
    labels = ["Bare", "Capacity-based", "Policy-based", "Ethics-based"]
    colors = ["#72B7B2", "#F58518", "#54A24B", "#E45756"]
    fig, ax = plt.subplots(figsize=(11, 6))
    bottom = [0] * len(df)
    for col, label, color in zip(cols, labels, colors):
        values = df[col].tolist()
        ax.bar(df["model"], values, bottom=bottom, label=label, color=color)
        bottom = [b + v for b, v in zip(bottom, values)]
    ax.set_ylabel("Share among non-compliance")
    ax.set_title("Layer 1 Rationale Distribution Among Non-compliance")
    ax.yaxis.set_major_formatter(lambda x, pos: f"{x:.0%}")
    ax.tick_params(axis="x", rotation=45)
    ax.legend(loc="upper left", bbox_to_anchor=(1.01, 1.0))
    fig.tight_layout()
    fig.savefig(out_dir / "plot_layer1_distribution_stacked.png", dpi=200)
    plt.close(fig)


def plot_l2_heatmap(l2_df, out_dir):
    pivot = l2_df.pivot(index="model", columns="feature", values="rate_among_non_compliance")
    order = [model for model in MODEL_ORDER if model in pivot.index] + sorted(set(pivot.index) - set(MODEL_ORDER))
    pivot = pivot.loc[order, L2_KEYS]
    fig, ax = plt.subplots(figsize=(13, 7))
    im = ax.imshow(pivot.values, aspect="auto", cmap="Blues", vmin=0, vmax=1)
    ax.set_xticks(range(len(pivot.columns)))
    ax.set_xticklabels(pivot.columns, rotation=45, ha="right")
    ax.set_yticks(range(len(pivot.index)))
    ax.set_yticklabels(pivot.index)
    ax.set_title("Layer 2 Feature Rates Among Non-compliance")
    cbar = fig.colorbar(im, ax=ax)
    cbar.ax.set_ylabel("Rate", rotation=270, labelpad=15)
    fig.tight_layout()
    fig.savefig(out_dir / "plot_l2_feature_rate_heatmap.png", dpi=200)
    plt.close(fig)


def plot_hypothesis_deltas(hypothesis_df, out_dir):
    if hypothesis_df.empty:
        return
    df = hypothesis_df.copy()
    df["comparison"] = df["model_a"] + " -> " + df["model_b"]
    fig, ax = plt.subplots(figsize=(10, 5))
    colors = ["#E45756" if x > 0 else "#4C78A8" for x in df["delta_b_minus_a"]]
    ax.barh(df["comparison"], df["delta_b_minus_a"], color=colors)
    ax.axvline(0, color="black", linewidth=0.8)
    ax.set_xlabel("Delta in non-compliance rate, model_b - model_a")
    ax.set_title("Hypothesis Pairwise Refusal Rate Differences")
    ax.xaxis.set_major_formatter(lambda x, pos: f"{x:.0%}")
    fig.tight_layout()
    fig.savefig(out_dir / "plot_hypothesis_refusal_rate_deltas.png", dpi=200)
    plt.close(fig)


def plot_reliability(reliability_l2_df, out_dir):
    if reliability_l2_df.empty:
        return
    pivot = reliability_l2_df.pivot(index="feature", columns="judge_result", values="kappa").loc[L2_KEYS]
    fig, ax = plt.subplots(figsize=(12, 5))
    x = range(len(pivot.index))
    width = 0.8 / max(len(pivot.columns), 1)
    for idx, col in enumerate(pivot.columns):
        offsets = [v + idx * width - 0.4 + width / 2 for v in x]
        ax.bar(offsets, pivot[col], width=width, label=col)
    ax.axhline(0.5, color="#999999", linestyle="--", linewidth=1)
    ax.axhline(0.7, color="#666666", linestyle=":", linewidth=1)
    ax.set_xticks(list(x))
    ax.set_xticklabels(pivot.index, rotation=45, ha="right")
    ax.set_ylabel("Cohen's kappa")
    ax.set_title("Judge Reliability by Layer 2 Feature")
    ax.legend(loc="upper left", bbox_to_anchor=(1.01, 1.0))
    fig.tight_layout()
    fig.savefig(out_dir / "plot_judge_l2_kappa.png", dpi=200)
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description="Analyze validation judge outputs")
    parser.add_argument("--judgments-dir", default=str(DATA_DIR / "validation_judgments"))
    parser.add_argument("--out-dir", default=str(DATA_DIR / "analysis"))
    parser.add_argument("--gold", default=str(DATA_DIR / "gold_100.json"))
    parser.add_argument("--judge-results", nargs="*", default=[
        str(DATA_DIR / "judge_compare_gpt53_currentprompt_gold100.json"),
        str(DATA_DIR / "judge_compare_gpt55_currentprompt_gold100.json"),
    ])
    args = parser.parse_args()

    judgments_dir = Path(args.judgments_dir)
    out_dir = Path(args.out_dir)
    model_df, l1_df, l2_df = summarize_validation(judgments_dir)
    hypothesis_df = compare_pairs(model_df)

    existing_judge_results = [Path(path) for path in args.judge_results if Path(path).exists()]
    reliability_layer_df, reliability_l2_df = reliability_tables(Path(args.gold), existing_judge_results)

    xlsx_path = save_tables(
        out_dir,
        model_df,
        l1_df,
        l2_df,
        hypothesis_df,
        reliability_layer_df,
        reliability_l2_df,
    )
    plot_refusal_rates(model_df, out_dir)
    plot_l1_stacked(model_df, out_dir)
    plot_l2_heatmap(l2_df, out_dir)
    plot_hypothesis_deltas(hypothesis_df, out_dir)
    plot_reliability(reliability_l2_df, out_dir)

    print(f"Analysis tables -> {xlsx_path}")
    print(f"CSV/plots -> {out_dir}")
    print(f"Models analyzed: {len(model_df)}")
    print(f"Total judged rows: {int(model_df['n_judged'].sum())}")
    print(f"Total skipped missing responses: {int(model_df['n_skipped_missing_response'].sum())}")


if __name__ == "__main__":
    main()
