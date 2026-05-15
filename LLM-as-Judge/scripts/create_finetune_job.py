#!/usr/bin/env python3
"""Upload judge SFT data and create an OpenAI fine-tuning job."""

import argparse
from pathlib import Path

from openai import OpenAI
from openai import PermissionDeniedError

from ft_judge_common import DATA_DIR


def main() -> None:
    parser = argparse.ArgumentParser(description="Create an OpenAI judge fine-tuning job")
    parser.add_argument("--train-jsonl", default=str(DATA_DIR / "ft_judge_train.jsonl"))
    parser.add_argument("--validation-jsonl", default=str(DATA_DIR / "ft_judge_validation.jsonl"))
    parser.add_argument("--model", default="gpt-4.1-mini")
    parser.add_argument("--suffix", default="refusal-judge-v3")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    train_path = Path(args.train_jsonl)
    validation_path = Path(args.validation_jsonl)
    if not train_path.exists():
        raise FileNotFoundError(f"Missing training file: {train_path}")
    if not validation_path.exists():
        raise FileNotFoundError(f"Missing validation file: {validation_path}")

    print(f"Training file:   {train_path}")
    print(f"Validation file: {validation_path}")
    print(f"Base model:      {args.model}")
    print(f"Suffix:          {args.suffix}")
    if args.dry_run:
        print("Dry run only; no files uploaded and no job created.")
        return

    client = OpenAI()

    with open(train_path, "rb") as f:
        train_file = client.files.create(file=f, purpose="fine-tune")
    print(f"Uploaded training file: {train_file.id}")

    with open(validation_path, "rb") as f:
        validation_file = client.files.create(file=f, purpose="fine-tune")
    print(f"Uploaded validation file: {validation_file.id}")

    try:
        job = client.fine_tuning.jobs.create(
            model=args.model,
            training_file=train_file.id,
            validation_file=validation_file.id,
            suffix=args.suffix,
        )
    except PermissionDeniedError as exc:
        print("\nFine-tuning job creation was denied by the OpenAI API.")
        print(f"Training file was uploaded:   {train_file.id}")
        print(f"Validation file was uploaded: {validation_file.id}")
        print(f"API error: {exc}")
        print("\nFallback for this project:")
        print("  python scripts/run_calibrated_judge.py --model gpt-5.5 --reasoning-effort high")
        raise

    print(f"Fine-tuning job created: {job.id}")
    print("After it succeeds, run:")
    print("  python scripts/run_finetuned_judge.py --model <fine_tuned_model>")


if __name__ == "__main__":
    main()
