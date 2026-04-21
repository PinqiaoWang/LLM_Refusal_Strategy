"""
Analysis: distribution plots, cross-model comparisons, statistical tests.

Usage:
    python -m src.analysis --input data/annotations/
"""

import json
from collections import Counter
from pathlib import Path
from typing import Optional

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from scipy import stats

FEATURE_KEYS = [
    "explicit_noncompliance", "implicit_noncompliance",
    "apology", "hedge", "preface_delay", "positive_alignment",
    "solidarity", "alternative_offer", "normative_suggestion",
    "principle_invocation", "negative_stance", "role_based",
]

FEATURE_LABELS = {
    "explicit_noncompliance": "Explicit NC",
    "implicit_noncompliance": "Implicit NC",
    "apology": "Apology",
    "hedge": "Hedge",
    "preface_delay": "Preface/Delay",
    "positive_alignment": "Positive Align",
    "solidarity": "Solidarity",
    "alternative_offer": "Alt. Offer",
    "normative_suggestion": "Norm. Suggest",
    "principle_invocation": "Principle Inv.",
    "negative_stance": "Neg. Stance",
    "role_based": "Role-based",
}


def load_results(input_path: str) -> pd.DataFrame:
    """Load annotated results into a DataFrame."""
    path = Path(input_path)

    if path.is_dir():
        # Load all JSON files in directory
        all_data = []
        for f in sorted(path.glob("*.json")):
            if "checkpoint" in f.name:
                continue
            with open(f) as fh:
                all_data.extend(json.load(fh))
        df = pd.DataFrame(all_data)
    else:
        with open(path) as f:
            df = pd.DataFrame(json.load(f))

    print(f"Loaded {len(df)} responses")
    return df


# ── Layer 0 analysis ─────────────────────────────────────────────────────────

def plot_layer0_distribution(df: pd.DataFrame, save_path: Optional[str] = None):
    """Plot Layer 0 (FC/PC/NC) distribution, optionally by model."""
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))

    # Overall distribution
    dist = df["layer0_label"].value_counts()
    colors = {"FULL_COMPLIANCE": "#4CAF50", "PARTIAL_COMPLIANCE": "#FFC107",
              "NON_COMPLIANCE": "#F44336", "UNKNOWN": "#9E9E9E", "ERROR": "#9E9E9E"}
    ax = axes[0]
    bars = ax.bar(dist.index, dist.values,
                  color=[colors.get(l, "#9E9E9E") for l in dist.index])
    ax.set_title("Layer 0: Action Distribution (Overall)", fontsize=13)
    ax.set_ylabel("Count")
    for bar, val in zip(bars, dist.values):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 2,
                f"{val}\n({val/len(df)*100:.1f}%)", ha="center", fontsize=9)

    # By model
    if "model" in df.columns:
        ax = axes[1]
        ct = pd.crosstab(df["model"], df["layer0_label"], normalize="index")
        order = ["FULL_COMPLIANCE", "PARTIAL_COMPLIANCE", "NON_COMPLIANCE"]
        cols = [c for c in order if c in ct.columns]
        ct[cols].plot(kind="barh", stacked=True, ax=ax,
                      color=[colors.get(c, "#9E9E9E") for c in cols])
        ax.set_title("Layer 0 by Model", fontsize=13)
        ax.set_xlabel("Proportion")
        ax.legend(loc="lower right", fontsize=8)

    plt.tight_layout()
    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches="tight")
        print(f"Saved → {save_path}")
    plt.show()


# ── Layer 1 analysis ─────────────────────────────────────────────────────────

def plot_layer1_distribution(df: pd.DataFrame, save_path: Optional[str] = None):
    """Plot Layer 1 (refusal basis) distribution across models."""
    nc = df[df["layer0_label"] == "NON_COMPLIANCE"].copy()
    if nc.empty:
        nc = df[df["layer1"].notna()].copy()

    fig, axes = plt.subplots(1, 2, figsize=(14, 5))

    # Overall
    dist = nc["layer1"].value_counts()
    ax = axes[0]
    ax.barh(dist.index, dist.values, color="#5C6BC0")
    ax.set_title("Layer 1: Refusal Basis (Overall)", fontsize=13)
    ax.set_xlabel("Count")

    # By model
    if "model" in nc.columns:
        ax = axes[1]
        ct = pd.crosstab(nc["model"], nc["layer1"], normalize="index")
        ct.plot(kind="barh", stacked=True, ax=ax, colormap="Set2")
        ax.set_title("Refusal Basis by Model", fontsize=13)
        ax.set_xlabel("Proportion")
        ax.legend(loc="lower right", fontsize=8)

    plt.tight_layout()
    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches="tight")
    plt.show()


# ── Layer 2 analysis ─────────────────────────────────────────────────────────

def plot_layer2_heatmap(df: pd.DataFrame, save_path: Optional[str] = None):
    """Plot Layer 2 feature prevalence heatmap across models."""
    nc = df[df["layer0_label"] == "NON_COMPLIANCE"].copy()
    if nc.empty:
        nc = df[df["layer1"].notna()].copy()

    if "model" not in nc.columns or nc.empty:
        print("No model column or no data for heatmap")
        return

    # Compute feature prevalence by model
    models = sorted(nc["model"].unique())
    matrix = []
    for model in models:
        model_data = nc[nc["model"] == model]
        row = []
        for feat in FEATURE_KEYS:
            vals = model_data[feat].dropna()
            vals = vals[vals >= 0]
            rate = vals.mean() if len(vals) > 0 else 0
            row.append(rate)
        matrix.append(row)

    matrix = np.array(matrix)
    labels = [FEATURE_LABELS.get(f, f) for f in FEATURE_KEYS]

    fig, ax = plt.subplots(figsize=(14, 6))
    sns.heatmap(matrix, annot=True, fmt=".2f", cmap="YlOrRd",
                xticklabels=labels, yticklabels=models, ax=ax,
                vmin=0, vmax=1, linewidths=0.5)
    ax.set_title("Layer 2: Feature Prevalence by Model", fontsize=13)
    ax.set_xlabel("Communicative Form Feature")
    plt.xticks(rotation=45, ha="right")
    plt.tight_layout()

    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches="tight")
    plt.show()


def plot_layer2_by_condition(df: pd.DataFrame, save_path: Optional[str] = None):
    """Plot Layer 2 feature prevalence by benchmark condition."""
    nc = df[df["layer0_label"] == "NON_COMPLIANCE"].copy()
    if nc.empty:
        nc = df[df["layer1"].notna()].copy()

    if "condition" not in nc.columns:
        print("No condition column")
        return

    conditions = sorted(nc["condition"].unique())
    matrix = []
    for cond in conditions:
        cond_data = nc[nc["condition"] == cond]
        row = []
        for feat in FEATURE_KEYS:
            vals = cond_data[feat].dropna()
            vals = vals[vals >= 0]
            rate = vals.mean() if len(vals) > 0 else 0
            row.append(rate)
        matrix.append(row)

    matrix = np.array(matrix)
    labels = [FEATURE_LABELS.get(f, f) for f in FEATURE_KEYS]

    fig, ax = plt.subplots(figsize=(14, 4))
    sns.heatmap(matrix, annot=True, fmt=".2f", cmap="YlGnBu",
                xticklabels=labels, yticklabels=conditions, ax=ax,
                vmin=0, vmax=1, linewidths=0.5)
    ax.set_title("Layer 2: Feature Prevalence by Benchmark Condition", fontsize=13)
    plt.xticks(rotation=45, ha="right")
    plt.tight_layout()

    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches="tight")
    plt.show()


# ── Statistical tests ────────────────────────────────────────────────────────

def test_form_variation_across_conditions(df: pd.DataFrame) -> pd.DataFrame:
    """
    Test whether Layer 2 feature distributions differ across conditions.
    Uses chi-squared test for each feature.
    """
    nc = df[df["layer0_label"] == "NON_COMPLIANCE"].copy()
    if "condition" not in nc.columns:
        print("No condition column")
        return pd.DataFrame()

    results = []
    for feat in FEATURE_KEYS:
        vals = nc[[feat, "condition"]].dropna()
        vals = vals[vals[feat] >= 0]
        if len(vals) < 10:
            continue

        ct = pd.crosstab(vals["condition"], vals[feat])
        if ct.shape[1] < 2:
            continue

        chi2, p, dof, expected = stats.chi2_contingency(ct)
        results.append({
            "feature": feat,
            "chi2": round(chi2, 3),
            "p_value": round(p, 4),
            "dof": dof,
            "significant": p < 0.05,
        })

    result_df = pd.DataFrame(results)
    if not result_df.empty:
        result_df = result_df.sort_values("p_value")
        print("\nChi-squared tests: Feature ~ Condition")
        print(result_df.to_string(index=False))

    return result_df


def compute_kl_divergence(df: pd.DataFrame,
                          reference_dist: Optional[dict] = None) -> pd.DataFrame:
    """
    Compute KL divergence between each model's Layer 2 feature distribution
    and a reference distribution (human-preferred or uniform).
    """
    nc = df[df["layer0_label"] == "NON_COMPLIANCE"].copy()
    if "model" not in nc.columns:
        return pd.DataFrame()

    models = sorted(nc["model"].unique())

    if reference_dist is None:
        # Default: uniform distribution as baseline
        reference_dist = {f: 0.5 for f in FEATURE_KEYS}

    results = []
    for model in models:
        model_data = nc[nc["model"] == model]
        model_dist = {}
        for feat in FEATURE_KEYS:
            vals = model_data[feat].dropna()
            vals = vals[vals >= 0]
            model_dist[feat] = vals.mean() if len(vals) > 0 else 0.5

        # Compute KL divergence
        p = np.array([model_dist[f] for f in FEATURE_KEYS])
        q = np.array([reference_dist[f] for f in FEATURE_KEYS])
        # Clip to avoid log(0)
        p = np.clip(p, 1e-6, 1 - 1e-6)
        q = np.clip(q, 1e-6, 1 - 1e-6)
        # Treat as independent Bernoulli features
        kl = np.sum(p * np.log(p / q) + (1 - p) * np.log((1 - p) / (1 - q)))

        results.append({"model": model, "kl_divergence": round(kl, 4)})

    result_df = pd.DataFrame(results).sort_values("kl_divergence", ascending=False)
    print("\nKL Divergence from reference distribution:")
    print(result_df.to_string(index=False))
    return result_df


# ── Main ─────────────────────────────────────────────────────────────────────

def run_full_analysis(input_path: str, output_dir: str = "figures"):
    """Run all analyses and save figures."""
    df = load_results(input_path)
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    if "layer0_label" in df.columns:
        plot_layer0_distribution(df, save_path=str(out / "layer0_distribution.png"))

    if "layer1" in df.columns:
        plot_layer1_distribution(df, save_path=str(out / "layer1_distribution.png"))

    feat_cols = [f for f in FEATURE_KEYS if f in df.columns]
    if feat_cols:
        plot_layer2_heatmap(df, save_path=str(out / "layer2_heatmap.png"))

        if "condition" in df.columns:
            plot_layer2_by_condition(df,
                                     save_path=str(out / "layer2_by_condition.png"))
            test_form_variation_across_conditions(df)

        if "model" in df.columns:
            compute_kl_divergence(df)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output-dir", default="figures")
    args = parser.parse_args()

    run_full_analysis(args.input, args.output_dir)
