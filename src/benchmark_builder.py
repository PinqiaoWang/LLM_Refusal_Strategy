"""
Benchmark builder: assemble prompts from safety benchmarks.

Three conditions:
  1. required_refusal  — clearly harmful (SORRY-Bench, HarmBench)
  2. over_refusal      — benign but sensitive (XSTest, OR-Bench)
  3. context_sensitive  — ambiguous / dual-use

Usage:
    python -m src.benchmark_builder
"""

import json
import random
from pathlib import Path
from typing import Optional

from datasets import load_dataset
from tqdm import tqdm

OUTPUT_DIR = Path("data/prompts")


def load_sorry_bench(n: int = 100) -> list[dict]:
    """Load required-refusal prompts from SORRY-Bench."""
    print("Loading SORRY-Bench...")
    try:
        ds = load_dataset("sorry-bench/sorry-bench-202503", split="train")
    except Exception:
        # Fallback name
        try:
            ds = load_dataset("sorry-bench/sorry-bench", split="train")
        except Exception as e:
            print(f"  Could not load SORRY-Bench: {e}")
            print("  → Download manually from https://huggingface.co/datasets/sorry-bench/sorry-bench")
            return []

    prompts = []
    for item in ds:
        turns = item.get("turns", [])
        if turns:
            text = turns[0] if isinstance(turns[0], str) else turns[0].get("value", "")
        else:
            text = item.get("prompt", "")

        if text and len(text) > 10:
            prompts.append({
                "prompt": text.strip(),
                "condition": "required_refusal",
                "source": "sorry-bench",
                "category": item.get("category", ""),
            })

    random.shuffle(prompts)
    result = prompts[:n]
    print(f"  → {len(result)} required-refusal prompts from SORRY-Bench")
    return result


def load_xstest(n: int = 100) -> list[dict]:
    """Load over-refusal prompts from XSTest (safe prompts only)."""
    print("Loading XSTest...")
    try:
        ds = load_dataset("natolambert/xstest-v2-copy", split="test")
    except Exception:
        try:
            ds = load_dataset("Paul/xstest", split="test")
        except Exception as e:
            print(f"  Could not load XSTest: {e}")
            return []

    prompts = []
    for item in ds:
        label = item.get("label", "")
        # XSTest labels safe prompts that models might over-refuse
        if label in ("safe", "contrast_safe", "safe_targets"):
            text = item.get("prompt", "")
            if text and len(text) > 10:
                prompts.append({
                    "prompt": text.strip(),
                    "condition": "over_refusal",
                    "source": "xstest",
                    "category": item.get("type", item.get("category", "")),
                })

    random.shuffle(prompts)
    result = prompts[:n]
    print(f"  → {len(result)} over-refusal prompts from XSTest")
    return result


def load_or_bench(n: int = 100) -> list[dict]:
    """Load over-refusal prompts from OR-Bench."""
    print("Loading OR-Bench...")
    try:
        ds = load_dataset("bench-llm/or-bench", split="test")
    except Exception:
        try:
            ds = load_dataset("yizhongw/or-bench", split="test")
        except Exception as e:
            print(f"  Could not load OR-Bench: {e}")
            return []

    prompts = []
    for item in ds:
        text = item.get("prompt", item.get("question", ""))
        if text and len(text) > 10:
            prompts.append({
                "prompt": text.strip(),
                "condition": "over_refusal",
                "source": "or-bench",
                "category": item.get("category", ""),
            })

    random.shuffle(prompts)
    result = prompts[:n]
    print(f"  → {len(result)} over-refusal prompts from OR-Bench")
    return result


def load_harmbench(n: int = 50) -> list[dict]:
    """Load additional required-refusal prompts from HarmBench."""
    print("Loading HarmBench...")
    try:
        ds = load_dataset("harmbench/harmbench", split="test")
    except Exception:
        try:
            ds = load_dataset("HarmBench/HarmBench", split="standard")
        except Exception as e:
            print(f"  Could not load HarmBench: {e}")
            return []

    prompts = []
    for item in ds:
        text = item.get("behavior", item.get("prompt", ""))
        if text and len(text) > 10:
            prompts.append({
                "prompt": text.strip(),
                "condition": "required_refusal",
                "source": "harmbench",
                "category": item.get("semantic_category", ""),
            })

    random.shuffle(prompts)
    result = prompts[:n]
    print(f"  → {len(result)} required-refusal prompts from HarmBench")
    return result


def build_benchmark(
    n_required: int = 100,
    n_over: int = 100,
    n_context: int = 100,
    seed: int = 42,
    output_path: Optional[str] = None,
) -> dict:
    """
    Assemble the full benchmark prompt set.

    Returns:
        Dict with keys: required_refusal, over_refusal, context_sensitive,
        each containing a list of prompt dicts.
    """
    random.seed(seed)

    # Required refusal: SORRY-Bench + HarmBench
    sorry = load_sorry_bench(n=n_required)
    harm = load_harmbench(n=50)
    required = sorry + harm
    random.shuffle(required)
    required = required[:n_required]

    # Over-refusal: XSTest + OR-Bench
    xs = load_xstest(n=n_over)
    orb = load_or_bench(n=50)
    over = xs + orb
    random.shuffle(over)
    over = over[:n_over]

    # Context-sensitive: placeholder — needs manual curation
    context = []
    print(f"\n⚠ Context-sensitive prompts ({n_context}) need manual curation.")
    print("  → Add them to data/prompts/context_sensitive.json")

    benchmark = {
        "required_refusal": required,
        "over_refusal": over,
        "context_sensitive": context,
    }

    # Summary
    print(f"\n{'='*50}")
    print(f"Benchmark Summary:")
    print(f"  Required refusal: {len(required)}")
    print(f"  Over-refusal:     {len(over)}")
    print(f"  Context-sensitive: {len(context)} (manual curation needed)")
    print(f"  Total:            {len(required) + len(over) + len(context)}")

    if output_path:
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w") as f:
            json.dump(benchmark, f, indent=2, ensure_ascii=False)
        print(f"\nSaved → {output_path}")

    return benchmark


if __name__ == "__main__":
    build_benchmark(output_path="data/prompts/benchmark.json")
