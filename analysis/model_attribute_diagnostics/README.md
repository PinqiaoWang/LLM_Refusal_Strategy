# Model Attribute Diagnostics

This folder contains a standalone diagnostic analysis for checking whether broad
model attributes explain differences in refusal style. The goal is not to make a
main-paper causal claim, but to support the appendix statement that size,
reasoning mode, release period, and open/closed access do not explain refusal
style in a simple one-factor way.

## Script

- `model_attribute_diagnostics.R`

Run from the repository root:

```bash
/usr/local/bin/Rscript analysis/model_attribute_diagnostics/model_attribute_diagnostics.R
```

The script reads the judged annotation files from `data/annotations`, excludes
the legacy/out-of-main-scope models used only for appendix context, filters to
the current judge prompt hash, and writes all outputs back into this folder.

## What Was Calculated

The analysis starts from two model-level summaries:

- Layer 0 non-compliance rate for each model, using successfully judged rows.
- Layer 2 feature rates for each model, conditioned on in-voice
  non-compliance responses.

It then compares models along four axes:

- **Size:** within-family size pairs, such as Llama 3.1 8B vs 70B and Qwen3 8B
  vs 32B.
- **Reasoning mode:** standard vs reasoning variants for Qwen3, Claude Opus
  4.6, and GPT-5.3.
- **Temporal change:** newer vs older releases within OpenAI and Anthropic.
- **Closed-family contrasts:** GPT-5.3, Claude Opus 4.6, Gemini 2.5 Pro, and
  Grok 4.20.

For each pair, the script computes:

- Difference in Layer 0 non-compliance rate.
- Mean absolute difference across all Layer 2 feature rates.
- The single Layer 2 feature with the largest pairwise difference.

Because the same sampled prompts were sent to every model, the script also runs
paired McNemar tests for pairwise Layer 0 and Layer 2 binary outcomes where the
same prompt appears for both models. The prompt-alignment check confirms that
joined pairs have matching prompt text; joined counts differ slightly below 200
when a model has parse errors, skips, or missing judged rows.

For the open/closed comparison, the script computes exploratory permutation
tests over model-level rates. These should be read cautiously because access
type is confounded with model family and provider.

## Main Takeaways

**Reasoning mode has the weakest effect.** Across the four standard/reasoning
pairs, the mean pairwise Layer 2 difference is about 2.0 percentage points, and
the mean absolute Layer 0 difference is about 1.2 percentage points. The clearest
exception is Qwen3-32B, where reasoning mode shifts the style toward more
articulated ethical/normative refusal language.

**Size is inconsistent.** The Llama size pair shows a large Layer 0 refusal-rate
difference but a small Layer 2 style difference. The Qwen size pairs show larger
Layer 2 style differences, especially apology, but the direction is not a
general size law. This supports the wording that size alone does not reliably
explain refusal style.

**Release period produces larger within-family changes.** Temporal pairs show
the largest average Layer 2 difference among the tested axes. The most visible
pattern is apology decay: GPT-4o to GPT-5.3 and Claude Sonnet 3.7 to Sonnet 4.6
show large drops in apology use. This is a stronger appendix point than either
size or reasoning mode.

**Open vs closed shows some aggregate separation, but it is confounded.** In the
model-level permutation tests, closed/proprietary models are more explicit and
open-weight models are more implicit and more likely to use statement of
principle. However, this is not a clean access-type effect because the open set
is mostly Llama/Qwen and the closed set contains several distinct providers.

**Provider/family remains the more plausible explanation.** Closed proprietary
systems differ substantially from each other, especially Gemini versus GPT or
Claude. That makes a simple explanation based only on access type, size, or
reasoning mode too coarse.

## Appendix-Ready Interpretation

A concise version for the appendix:

> We conducted diagnostic comparisons across model size, reasoning mode, release
> period, and open- versus closed-weight access. Reasoning mode produced only
> small changes in overall non-compliance and Layer 2 feature use, with the main
> exception of Qwen3-32B, where reasoning reduced bare refusals and increased
> more explicit ethical/normative justification. Size comparisons were
> inconsistent: Llama size variants differed substantially in refusal rate but
> only modestly in refusal form, while Qwen size variants differed more strongly
> in selected features such as apology. Temporal comparisons showed the largest
> within-family stylistic shifts, especially the decline of apology in newer
> OpenAI and Anthropic releases. Open/closed access showed exploratory aggregate
> differences, but these are confounded with provider and model family. Overall,
> the results suggest that refusal style is better explained by provider- and
> release-specific alignment choices than by any single model attribute.

## Output Files

- `model_level_l2_rates_for_attributes.csv`: model-level Layer 0 and Layer 2
  rates used for the comparisons.
- `model_attribute_pair_differences.csv`: pairwise differences for size,
  reasoning, temporal, and closed-family comparisons.
- `model_attribute_pair_summary.csv`: average pairwise difference by comparison
  type.
- `attribute_effect_size_direction_table.csv`: compact size/reasoning table
  reporting effect size and direction, with the direction defined as the second
  model minus the first model.
- `attribute_effect_size_direction_table.tex`: LaTeX version of the compact
  effect-size/direction table.
- `model_pair_prompt_alignment_check.csv`: verifies that paired tests compare
  the same prompts.
- `model_pair_l0_mcnemar_tests.csv`: McNemar tests for paired Layer 0
  non-compliance outcomes.
- `model_pair_l2_mcnemar_tests.csv`: McNemar tests for paired Layer 2 feature
  outcomes.
- `open_closed_l2_summary.csv`: model-level open/closed aggregate summary.
- `open_closed_permutation_tests.csv`: exploratory permutation tests for
  open/closed differences.
- `reasoning_pair_tests.csv`: focused reasoning-mode pair tests.
- `*_appendix_l0_l1.csv` and `*_appendix_l2.csv`: appendix-ready tables split by
  comparison type.
- `temporal_affiliative_features.csv` and
  `temporal_affiliative_features_table.tex`: temporal comparison for apology,
  positive alignment, solidarity, explanatory preface, and hedge.
- `reasoning_layer0_layer1_table.csv`, `reasoning_l2_selected_table.csv`, and
  `reasoning_mode_comparison_tables.csv`: tables matching the reasoning-mode
  appendix draft.
