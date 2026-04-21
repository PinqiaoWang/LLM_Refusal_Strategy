#!/usr/bin/env python3
"""
Step 2: Query LLMs and collect responses on benchmark prompts.

Usage:
    # API models (GPT-4o, Claude)
    python scripts/02_collect_responses.py --mode api

    # Specific API model
    python scripts/02_collect_responses.py --mode api --model gpt-4o

    # Local models on GPU (Llama, Qwen, Gemma)
    python scripts/02_collect_responses.py --mode local

    # Specific local model
    python scripts/02_collect_responses.py --mode local --model llama-3.1-8b-instruct

    # Also collect WildChat sample for Layer 0 analysis
    python scripts/02_collect_responses.py --wildchat --n 1000
"""

import argparse
import sys

sys.path.insert(0, ".")


def main():
    parser = argparse.ArgumentParser(description="Collect model responses")
    parser.add_argument("--mode", choices=["api", "local"], default="api",
                        help="API models or local vLLM models")
    parser.add_argument("--model", default=None,
                        help="Specific model name from config")
    parser.add_argument("--prompts", default="data/prompts/benchmark.json",
                        help="Path to benchmark prompts")
    parser.add_argument("--config", default="configs/models.yaml",
                        help="Path to model config")
    parser.add_argument("--output-dir", default="data/responses",
                        help="Output directory for responses")
    parser.add_argument("--wildchat", action="store_true",
                        help="Also sample from WildChat for Layer 0 analysis")
    parser.add_argument("--n", type=int, default=1000,
                        help="Number of WildChat samples")
    args = parser.parse_args()

    if args.wildchat:
        from src.data_collection import sample_wildchat
        print("=" * 60)
        print("Sampling from WildChat for Layer 0 analysis")
        print("=" * 60)
        sample_wildchat(
            n=args.n,
            output_path="data/responses/wildchat_sample.json",
        )
        print()

    from src.model_inference import collect_responses
    print("=" * 60)
    print(f"Collecting responses (mode={args.mode})")
    print("=" * 60)
    collect_responses(
        prompts_path=args.prompts,
        config_path=args.config,
        mode=args.mode,
        model_name=args.model,
        output_dir=args.output_dir,
    )


if __name__ == "__main__":
    main()
