# How LLMs Say No

Code, data, annotations, and analysis artifacts for our study of the pragmatic
form of safety refusals in large language models.

## Authors

- Ruoxuan Li
- Pinqiao Wang
- Sheng Li
- Cameron R. Jones

## Abstract

Refusals are often treated as face-threatening acts in pragmatics because they
can challenge the requester’s socially claimed self-image. Large language
models (LLMs) are increasingly trained to refuse unsafe and inappropriate
requests, and these refusals may harm users when models fail to manage this
interactional cost properly. While existing work has mainly approached LLM
non-compliance as a safety-alignment outcome, it does not provide a way to
evaluate whether LLMs refuse appropriately across different harmful contexts.
To study this question, we propose (to our knowledge) the first taxonomy of LLM
refusals that is grounded in pragmatic theory. Applying this taxonomy to
responses from 16 modern LLMs across 14 harm categories, we find that although
models differ in how they refuse, their refusals are overall explicit and
strongly morally evaluative, with interactional repair occurring mainly through
offering or providing safer alternatives instead of interpersonal facework.
This pattern is especially consequential in sensitive harm contexts, where
overuse of negative framing may make users feel shamed or provoked, undermining
the purpose of safe non-compliance. We therefore call for alignment evaluation
that considers not only whether models refuse harmful requests, but also
whether they refuse in ways that are contextually adaptive and socially
accountable for the interactional consequences of saying no.

## Repository structure

| Path | Contents |
|---|---|
| [`scripts/`](scripts/) | Main-experiment code for benchmark construction, response collection, human-evaluation sampling, judge selection, full-corpus judging, and validation summaries. Shared judge configuration and utilities are under `scripts/utils/`. |
| [`data/prompts/`](data/prompts/) | Candidate pools and the sampled query sets used across the main and robustness collections. See [Query-set provenance](#query-set-provenance). |
| [`data/responses/`](data/responses/) | Raw model responses, organized by provider and collection. JSON files retain the full structured records; CSV files provide flattened versions for inspection. |
| [`data/annotations/`](data/annotations/) | LLM-as-judge outputs. Each model generally has a structured `.judged.json`, a flattened `.judged.csv`, and a `.judged.prompt.txt` snapshot of the judge prompt. Files directly under this directory are the primary main-analysis annotations. |
| [`data/`](data/) | Human-adjudicated gold data, judge-selection outputs, the current judge prompt, prompts, responses, and annotations. [`data/README.md`](data/README.md) documents the validation resources in more detail. |
| [`analysis/`](analysis/) | Post-analysis and visualization code for the main paper. The R Markdown files generate the principal descriptive statistics, appendix tables, and figures; smaller R scripts support targeted qualitative and diagnostic analyses. Generated figures are under `analysis/figs/`. |
| [`appendix_and_additional_experiments/`](appendix_and_additional_experiments/) | Robustness analyses, cross-judge agreement analyses, dataset-expansion utilities, intermediate matrices, and appendix-specific results. The `may_august_robustness/` directory contains the May–August comparison outputs. |

## Query-set provenance

Two different historical 200-query samples exist in the repository. The model
response files are the authoritative record of which prompts each model
received.

| File | Role and model coverage |
|---|---|
| [`data/prompts/sampled_200_final_queries.json`](data/prompts/sampled_200_final_queries.json) | **Final main query set (Set B).** This is the exact 200-query set used by all 16 models in the primary analysis. The prompt-matched Claude Opus 3 rerun also uses this set. |
| [`data/prompts/sampled_200_main_collection_reconstructed.json`](data/prompts/sampled_200_main_collection_reconstructed.json) | A reconstruction of the same main-collection Set B from the response records, enriched with source-pool metadata. It was used to run the prompt-matched Claude Opus 3 supplementary collection. |
| [`data/prompts/outdated_queries.json`](data/prompts/outdated_queries.json) | **Superseded query set (Set A).** This set was used by the original supplementary collections for GPT-4 Turbo, Llama 3 70B Instruct, Claude Opus 3, and Mistral 7B Instruct v0.1. It also served as the 200-query seed for the August robustness collection. |
| [`data/prompts/sampled_expanded_final_queries.json`](data/prompts/sampled_expanded_final_queries.json) | **August robustness set.** This 262-query set contains all 200 Set A queries plus 62 additions. Relative to the final main Set B, it contains 138 shared queries and 124 different queries; Set B contains 62 queries absent from the August set. |

The original Claude Opus 3 collection is retained for provenance. Its
prompt-matched rerun and corresponding judgments are stored under:

```text
data/responses/openrouter/sampled_200/additional_models_expo/main200_rerun/
data/annotations/additional_models_expo_main200_rerun/
```

The primary analysis remains the designated 16-model panel. Claude Opus 3 is a
supplementary historical comparison and is used in the temporal analysis via
its prompt-matched rerun.

## Annotation layers

The released judgments operationalize three levels of refusal behavior:

- **Layer 0 — action:** full compliance, partial compliance, or non-compliance.
- **Layer 1 — rationale:** the principal basis given for non-compliance, such
  as a bare, capacity-based, policy-based, or ethics-based refusal.
- **Layer 2 — realization and adjunct features:** linguistic and interactional
  properties of the refusal, including explicitness, apology, solidarity,
  negative stance, normative suggestion, and safer alternatives.

The exact machine-readable judge specification used for the released
annotations is preserved in [`data/judge_prompt_current.txt`](data/judge_prompt_current.txt)
and in the per-model `.judged.prompt.txt` snapshots.

## Reproducing the pipeline

Install the Python dependencies:

```bash
python -m pip install -r requirements.txt
```

The main experimental workflow is documented in
[`scripts/README.md`](scripts/README.md). The central entry points are:

```text
scripts/01_build_benchmark.py
scripts/02_collect_responses.py
scripts/03_create_human_eval_set.py
scripts/04_compare_judge_models_on_gold.py
scripts/05_run_full_validation_judge.py
scripts/06_analyze_validation_judgments.py
```

API-dependent scripts read credentials from environment variables; do not
commit local `.env` files or credentials. Use each script's `--help` option to
inspect its current arguments before running a collection or judge job.

The main post-analysis and figures are generated by:

```text
analysis/refusal_analysis.Rmd
analysis/refusal_analysis_rx.Rmd
analysis/l2_variation.Rmd
```

These analyses use R packages including `tidyverse`, `jsonlite`, `scales`,
`knitr`, and `kableExtra`. PDF figures are post-processed with Ghostscript so
that all fonts are embedded for publication.

## Robustness and additional experiments

The August robustness collection repeats generation on 13 available models
using the 262-query alternative set. The main comparison contrasts the final
200-query Set B with the August 262-query collection, while the paired analysis
uses their 138 shared queries. Code and outputs are located in:

```text
appendix_and_additional_experiments/scripts/may_august_robustness.py
appendix_and_additional_experiments/may_august_robustness/
```

Additional files in `appendix_and_additional_experiments/` support query-set
expansion, judge comparison, cross-family agreement, and appendix reporting.

## Data-use note

This repository contains harmful and sensitive prompts and model responses for
safety research. Some records include explicit, violent, hateful, sexual, or
otherwise disturbing material. Please handle and redistribute the data with
appropriate care.
