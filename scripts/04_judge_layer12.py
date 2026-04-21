#!/usr/bin/env python3
"""
Step 4: Run Layer 1 + Layer 2 annotation on non-compliance cases.

Usage:
    # Judge a single file
    python scripts/04_judge_layer12.py --input data/annotations/responses_gpt-4o_layer0.json

    # Judge all Layer 0 outputs
    python scripts/04_judge_layer12.py --input-dir data/annotations/ --pattern "*_layer0.json"

    # Judge ALL responses (not just non-compliance)
    python scripts/04_judge_layer12.py --input data/annotations/wildchat_layer0.json --all
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, ".")

from src.layer12_judge import judge_batch


def main():
    parser = argparse.ArgumentParser(description="Layer 1+2 judge")
    parser.add_argument("--input", default=None)
    parser.add_argument("--input-dir", default=None)
    parser.add_argument("--pattern", default="*_layer0.json")
    parser.add_argument("--output-dir", default="data/annotations")
    parser.add_argument("--model", default="gpt-4o")
    parser.add_argument("--delay", type=float, default=0.5)
    parser.add_argument("--all", action="store_true",
                        help="Judge all responses, not just non-compliance")
    args = parser.parse_args()

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    if args.input:
        input_path = args.input
        output_path = str(out_dir / Path(input_path).stem.replace("_layer0", "")) + "_full.json"
        print(f"\nProcessing: {input_path}")
        print(f"Output:     {output_path}")
        judge_batch(
            input_path=input_path,
            output_path=output_path,
            model=args.model,
            delay=args.delay,
            nc_only=not args.all,
        )

    elif args.input_dir:
        input_dir = Path(args.input_dir)
        files = sorted(input_dir.glob(args.pattern))
        print(f"Found {len(files)} files matching '{args.pattern}'")

        for f in files:
            output_path = str(out_dir / f.stem.replace("_layer0", "")) + "_full.json"
            print(f"\n{'='*60}")
            print(f"Processing: {f}")
            judge_batch(
                input_path=str(f),
                output_path=output_path,
                model=args.model,
                delay=args.delay,
                nc_only=not args.all,
            )
    else:
        print("Provide either --input or --input-dir")
        sys.exit(1)


if __name__ == "__main__":
    main()
