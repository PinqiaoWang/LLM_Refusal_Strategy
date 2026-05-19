# Scripts

This folder contains the code used for the refusal-strategy benchmark, model response collection, LLM-as-Judge labeling, and analysis.

## Current LLM-as-Judge Pipeline

The main judge pipeline for the current experiment is:

1. `04_compare_judge_models_on_gold.py`
   - Evaluates candidate judge models on `data/gold_100.json`.
   - Reports Layer 0, Layer 1, and Layer 2 accuracy / Cohen's kappa.
   - Used to compare GPT-5.3 and GPT-5.5 before choosing the final judge.

2. `05_run_full_validation_judge.py`
   - Runs the selected judge over the full validation response files.
   - Input files must contain `query` and `response` fields.
   - Produces judged `.json` and `.csv` files with Layer 0, Layer 1, and Layer 2 labels.

3. `06_analyze_validation_judgments.py`
   - Summarizes the judged validation outputs.
   - Produces model-level tables, Layer 1 distributions, Layer 2 feature rates, judge reliability tables, and plots.

These scripts depend on the shared utilities in:

```text
scripts/utils/
```

Required utility files:

```text
scripts/utils/__init__.py
scripts/utils/judge_config.py
scripts/utils/judge_utils.py
scripts/utils/gold_rule_common.py
scripts/utils/judge_metrics.py
```

Together, the minimum code package needed to reproduce the LLM-as-Judge part of the experiment is:

```text
scripts/04_compare_judge_models_on_gold.py
scripts/05_run_full_validation_judge.py
scripts/06_analyze_validation_judgments.py
scripts/utils/
```

## Supporting Scripts

These scripts are useful for reproducing earlier stages of the project:

```text
scripts/01_build_benchmark.py
scripts/02_collect_responses.py
scripts/03_create_human_eval_set.py
```

- `01_build_benchmark.py` builds and samples benchmark prompts.
- `02_collect_responses.py` collects model responses through OpenRouter / API calls.
- `03_create_human_eval_set.py` samples model responses for human annotation and gold-set creation.

## Legacy Scripts

The following scripts belong to an older two-stage judge pipeline and are not the current analysis path:

```text
scripts/03_classify_layer0.py
scripts/04_judge_layer12.py
scripts/05_analyze.py
```

They are kept only for historical reference unless explicitly needed.

## Important Data Inputs

The current judge pipeline expects:

```text
data/gold_100.json
data/Gold Rule.xlsx
data/responses/openrouter/sampled_200/
```

The completed LLM-as-Judge labels can be stored in:

```text
data/annotations/
```

Analysis outputs are written to:

```text
data/analysis/
```
