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
judge_calibrated_gold100.json
judge_compare_gpt55_currentprompt_gold100_none_reasoning.json
```

Final prompt snapshot and the gold-100 judge comparison outputs used to select the LLM-as-Judge.

Current default judge configuration:

```text
provider: openrouter
model: openai/gpt-5.5
reasoning_effort: none
```

Gold-100 comparison summary:

| Judge result file | Model setting | Layer 0 accuracy / kappa | Layer 1 accuracy / kappa | Notes |
|---|---|---:|---:|---|
| `judge_calibrated_gold100.json` | `openai/gpt-5.3-chat`, high reasoning | 96.00% / 0.8862 | 89.61% / 0.7771 | Strong Layer 0, but weak sparse-feature alignment for `normative_suggestion` and `statement_of_principle`. |
| `judge_compare_gpt55_currentprompt_gold100_none_reasoning.json` | `openai/gpt-5.5`, no reasoning | 95.00% / 0.8570 | 93.51% / 0.8595 | Selected as the default judge because it improves Layer 1 and key Layer 2 boundary features. |

Selected GPT-5.5 no-reasoning Layer 2 kappas:

```text
explicit_nc             0.8821
implicit_nc             0.8821
apology                 0.9245
hedge                   1.0000
explanatory_preface     0.5515
positive_alignment      0.6462
solidarity              0.9262
negative_stance         0.7905
executed_alternative    0.6054
alternative_offer       0.9165
normative_suggestion    0.5850
statement_of_principle  0.6484
role_based              0.7080
```

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

