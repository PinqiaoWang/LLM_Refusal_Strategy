#!/usr/bin/env python3
"""
Step 3: Classify all responses at Layer 0 (FC / PC / NC).

Usage:
    # Classify WildChat sample (for motivation figure)
    python scripts/03_classify_layer0.py --input data/responses/wildchat_sample.json

    # Classify model responses on benchmark
    python scripts/03_classify_layer0.py --input data/responses/responses_gpt-4o.json

    # Classify all response files in a directory
    python scripts/03_classify_layer0.py --input-dir data/responses/ --pattern "responses_*.json"
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, ".")

from src.layer0_classifier import classify_batch


def main():
    parser = argparse.ArgumentParser(description="Layer 0 classification")
    parser.add_argument("--input", default=None, help="Single input JSON file")
    parser.add_argument("--input-dir", default=None,
                        help="Directory of JSON files to process")
    parser.add_argument("--pattern", default="responses_*.json",
                        help="Glob pattern for input-dir mode")
    parser.add_argument("--output-dir", default="data/annotations",
                        help="Output directory")
    parser.add_argument("--model", default="gpt-4o-mini",
                        help="Judge model")
    parser.add_argument("--delay", type=float, default=0.3,
                        help="Delay between API calls")
    args = parser.parse_args()

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    if args.input:
        input_path = args.input
        output_path = str(out_dir / Path(input_path).stem) + "_layer0.json"
        print(f"\nProcessing: {input_path}")
        print(f"Output:     {output_path}")
        classify_batch(
            input_path=input_path,
            output_path=output_path,
            model=args.model,
            delay=args.delay,
        )

    elif args.input_dir:
        input_dir = Path(args.input_dir)
        files = sorted(input_dir.glob(args.pattern))
        print(f"Found {len(files)} files matching '{args.pattern}' in {input_dir}")

        for f in files:
            output_path = str(out_dir / f.stem) + "_layer0.json"
            print(f"\n{'='*60}")
            print(f"Processing: {f}")
            print(f"Output:     {output_path}")
            classify_batch(
                input_path=str(f),
                output_path=output_path,
                model=args.model,
                delay=args.delay,
            )
    else:
        print("Provide either --input or --input-dir")
        sys.exit(1)


if __name__ == "__main__":
    main()
