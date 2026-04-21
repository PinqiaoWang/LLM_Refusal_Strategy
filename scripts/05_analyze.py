#!/usr/bin/env python3
"""
Step 5: Run all analyses and generate figures.

Usage:
    # Analyze all annotated data
    python scripts/05_analyze.py --input data/annotations/

    # Analyze a specific file
    python scripts/05_analyze.py --input data/annotations/wildchat_full.json

    # Custom output directory
    python scripts/05_analyze.py --input data/annotations/ --output-dir figures/
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, ".")

from src.analysis import (
    load_results,
    plot_layer0_distribution,
    plot_layer1_distribution,
    plot_layer2_heatmap,
    plot_layer2_by_condition,
    test_form_variation_across_conditions,
    compute_kl_divergence,
    run_full_analysis,
)


def main():
    parser = argparse.ArgumentParser(description="Run analysis and generate figures")
    parser.add_argument("--input", required=True,
                        help="Input file or directory")
    parser.add_argument("--output-dir", default="figures",
                        help="Output directory for figures")
    args = parser.parse_args()

    run_full_analysis(args.input, args.output_dir)


if __name__ == "__main__":
    main()
