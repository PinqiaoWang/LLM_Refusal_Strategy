#!/usr/bin/env python3
"""Step 1: Assemble benchmark prompts from safety benchmarks."""

import sys
sys.path.insert(0, ".")

from src.benchmark_builder import build_benchmark

if __name__ == "__main__":
    build_benchmark(
        n_required=100,
        n_over=100,
        n_context=100,
        seed=42,
        output_path="data/prompts/benchmark.json",
    )
