# Data

This folder contains the benchmark prompts, model responses, human gold annotations, LLM-as-Judge outputs, and analysis tables used in the refusal-strategy project.

## Human Gold Data

```text
gold_100.json
gold_100.xlsx
```

The 100 human-annotated gold examples used to validate the LLM-as-Judge. The judge comparison script reads `gold_100.json` by default.

```text
Gold Rule.xlsx
```

Human calibration examples used in the judge prompt. The current judge scripts load this file through `scripts/utils/gold_rule_common.py`.

## Judge Selection Outputs

```text
judge_prompt_current.txt
judge_compare_gpt53_currentprompt_gold100.json
judge_compare_gpt55_currentprompt_gold100.json
```

Final prompt snapshot and the gold-100 judge comparison outputs for GPT-5.3 and GPT-5.5.

Older judge result files are kept for historical reference:

```text
judge_gpt4o_standard.json
judge_o4mini_reasoning.json
judge_gpt55_standard.json
judge_gpt55_reasoning.json
judge_gpt55_std_v2.json
judge_gpt55_reas_v2.json
judge_ensemble_v2.json
llm_judge_results_100.xlsx
llm_judge_gpt55_results_100.xlsx
llm_judge_ensemble_results.xlsx
```

## Benchmark Prompts

```text
prompts/
sampled_200_final_queries.csv
```

Prompt candidates and the final sampled validation query set. These are used before model response collection.

## Model Responses

```text
responses/
```

Raw model responses collected for the validation queries. The current full validation run uses files under:

```text
responses/openrouter/sampled_200/
```

Each response file should contain query-response pairs for one model.

## LLM-as-Judge Annotations

```text
annotations/
```

Completed LLM-as-Judge labels for the full validation dataset. These files are the final judged outputs used by the analysis script.

Typical files:

```text
responses_<model>.judged.json
responses_<model>.judged.csv
responses_<model>.judged.prompt.txt
```

- `.judged.json`: complete structured judge output.
- `.judged.csv`: flattened table for inspection and analysis.
- `.judged.prompt.txt`: prompt snapshot used for that judge run.

The current analysis script reads `data/annotations/` by default.

## Analysis Outputs

```text
analysis/
```

Tables and plots generated from the judged validation outputs.

Key tables:

```text
analysis_tables.xlsx
validation_model_summary.csv
validation_layer1_distribution.csv
validation_l2_feature_rates.csv
hypothesis_refusal_rate_comparisons.csv
judge_reliability_layer_accuracy_kappa.csv
judge_reliability_l2_accuracy_kappa.csv
```

Key plots:

```text
plot_refusal_rate_by_model.png
plot_layer1_distribution_stacked.png
plot_l2_feature_rate_heatmap.png
plot_hypothesis_refusal_rate_deltas.png
plot_judge_l2_kappa.png
```

## Legacy / Temporary Folder

```text
validation_judgments/
```

This was the earlier output location for the full validation judge run. The cleaned repository structure uses `data/annotations/` instead.

