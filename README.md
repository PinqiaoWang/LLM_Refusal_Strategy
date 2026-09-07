<div align="center">

# How LLMs Say No

### You Shouldn’t Have Asked: A Pragmatics-Inspired Taxonomy for Evaluating LLM Refusals
<p align="center">
  <strong>To appear in EMNLP 2026 (Main Conference)</strong>
</p>

<p align="center">
  Ruoxuan Li<sup>&ast;</sup> ·
  Pinqiao Wang<sup>&ast;</sup> ·
  Sheng Li ·
  Cameron R. Jones
</p>

<p align="center">
  <sup>&ast;</sup> Equal contribution.
</p>
[![Paper](https://img.shields.io/badge/Paper-alphaXiv-B31B1B)](https://www.alphaxiv.org/abs/2608.30856)
[![Codebook](https://img.shields.io/badge/Taxonomy-Codebook-2563EB)](taxonomy_codebook.pdf)

**Evaluating not only whether LLMs refuse, but how they say no.**

Code, data, annotations, and analysis artifacts for our study of the pragmatic form of safety refusals in large language models.

[Overview](#overview) · [Explore the release](#explore-the-release) · [Reproduction](#reproduction) · [Data provenance](#data-provenance) · [Citation](#citation)

</div>

---

## Overview

Safety evaluation often asks whether a model refuses a harmful request. Our study examines the **linguistic and social form** of that refusal.

We introduce a pragmatics-grounded taxonomy and apply it to **16 LLMs across 14 harm categories**. The analysis distinguishes what a model does, the rationale it gives, and how it manages the interaction.

| Layer | Question | Annotation scope |
|---|---|---|
| **L0 · Action** | Does the model comply? | Full compliance, partial compliance, or non-compliance |
| **L1 · Rationale** | What basis does it give for refusing? | Bare, capacity-based, policy-based, or ethics-based refusal |
| **L2 · Realization and adjunct features** | How is the refusal expressed? | Explicitness, apology, solidarity, negative stance, normative suggestion, and safer alternatives |

Across models, refusals are generally explicit and strongly morally evaluative. Interactional repair occurs mainly through safer alternatives rather than interpersonal facework.

<details>
<summary><strong>Read the full abstract</strong></summary>

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

</details>

## Explore the release

| To… | Start here |
|---|---|
| Read the paper | [Paper on alphaXiv](https://www.alphaxiv.org/abs/2608.30856) |
| Understand the taxonomy | [Human annotation codebook](taxonomy_codebook.pdf) |
| Inspect the judge specification | [Current judge prompt](data/judge_prompt_current.txt) |
| Browse model responses | [`data/responses/`](data/responses/) |
| Browse released judgments | [`data/annotations/`](data/annotations/) |
| Inspect gold data and judge validation | [`data/README.md`](data/README.md) |
| Run the experimental pipeline | [`scripts/README.md`](scripts/README.md) |
| Reproduce analyses and figures | [`analysis/`](analysis/) |
| Inspect robustness experiments | [`appendix_and_additional_experiments/`](appendix_and_additional_experiments/) |

The codebook was provided to human annotators and is consistent with Appendix A of the paper. The exact machine-readable judge specifications are preserved in the current judge prompt and per-model `.judged.prompt.txt` snapshots.

## Repository structure

| Path | Contents |
|---|---|
| [`scripts/`](scripts/) | Benchmark construction, response collection, human-evaluation sampling, judge selection, full-corpus judging, and validation summaries. Shared judge configuration and utilities are in `scripts/utils/`. |
| [`data/prompts/`](data/prompts/) | Candidate pools and sampled query sets for the main and robustness collections. See [Data provenance](#data-provenance). |
| [`data/responses/`](data/responses/) | Raw model responses organized by provider and collection. JSON files preserve full structured records; CSV files provide flattened versions. |
| [`data/annotations/`](data/annotations/) | LLM-as-judge outputs, generally including `.judged.json`, `.judged.csv`, and `.judged.prompt.txt` files per model. Files directly under this directory are the primary main-analysis annotations. |
| [`data/`](data/) | Human-adjudicated gold data, judge-selection outputs, the current judge prompt, and the data directories above. |
| [`analysis/`](analysis/) | Main-paper statistics, tables, figures, and targeted qualitative and diagnostic analyses. Generated figures are in `analysis/figs/`. |
| [`appendix_and_additional_experiments/`](appendix_and_additional_experiments/) | Robustness analyses, cross-judge agreement, dataset-expansion utilities, intermediate matrices, and appendix results. |

## Reproduction

### 1. Install Python dependencies

```bash
python -m pip install -r requirements.txt
```

### 2. Follow the experimental pipeline

See [`scripts/README.md`](scripts/README.md) for workflow details.

| Stage | Entry point |
|---|---|
| Build the benchmark | `scripts/01_build_benchmark.py` |
| Collect model responses | `scripts/02_collect_responses.py` |
| Sample the human-evaluation set | `scripts/03_create_human_eval_set.py` |
| Compare judges against gold annotations | `scripts/04_compare_judge_models_on_gold.py` |
| Run full-corpus judging | `scripts/05_run_full_validation_judge.py` |
| Summarize validation judgments | `scripts/06_analyze_validation_judgments.py` |

API-dependent scripts read credentials from environment variables. Do not commit local `.env` files or credentials. Before running collection or judging, inspect each script’s arguments with `--help`.

### 3. Generate analyses and figures

The principal R Markdown entry points are:

```text
analysis/refusal_analysis.Rmd
analysis/refusal_analysis_rx.Rmd
analysis/l2_variation.Rmd
```

Required R packages include `tidyverse`, `jsonlite`, `scales`, `knitr`, and `kableExtra`. PDF figures are post-processed with Ghostscript to embed fonts for publication.

## Data provenance

> [!IMPORTANT]
> The repository contains two historical 200-query samples. **Set B is the final main query set used by all 16 models in the primary analysis.** Model response files are the authoritative record of which prompts each model received.

| Query set | File | Purpose |
|---|---|---|
| **Set B · Main** | [`sampled_200_final_queries.json`](data/prompts/sampled_200_final_queries.json) | Exact 200-query set used by all 16 primary-analysis models and the prompt-matched Claude Opus 3 rerun. |
| **Set B · Reconstructed** | [`sampled_200_main_collection_reconstructed.json`](data/prompts/sampled_200_main_collection_reconstructed.json) | The same main set reconstructed from response records, enriched with source-pool metadata. Used for the prompt-matched Claude Opus 3 supplementary collection. |
| **Set A · Superseded** | [`outdated_queries.json`](data/prompts/outdated_queries.json) | Used by the original supplementary collections for GPT-4 Turbo, Llama 3 70B Instruct, Claude Opus 3, and Mistral 7B Instruct v0.1. Also the seed for the August robustness set. |
| **August · Robustness** | [`sampled_expanded_final_queries.json`](data/prompts/sampled_expanded_final_queries.json) | All 200 Set A queries plus 62 additions, totaling 262 queries. |

### Main–robustness overlap

| Comparison | Query count |
|---|---:|
| Main Set B | 200 |
| August robustness set | 262 |
| Shared queries | 138 |
| Queries only in main Set B | 62 |
| Queries only in the August set | 124 |

### Supplementary historical comparison

The original Claude Opus 3 collection is retained for provenance. Its **prompt-matched rerun**, used in the temporal analysis, and corresponding judgments are stored in:

```text
data/responses/openrouter/sampled_200/additional_models_expo/main200_rerun/
data/annotations/additional_models_expo_main200_rerun/
```

Claude Opus 3 is a supplementary historical comparison. The primary analysis remains the designated 16-model panel.

## Robustness and additional experiments

The August robustness collection repeats generation on **13 available models** using the alternative **262-query set**.

- The main comparison contrasts the final 200-query Set B with the August 262-query collection.
- The paired analysis uses their **138 shared queries**.

Code and outputs:

```text
appendix_and_additional_experiments/scripts/may_august_robustness.py
appendix_and_additional_experiments/may_august_robustness/
```

Additional files in [`appendix_and_additional_experiments/`](appendix_and_additional_experiments/) support query-set expansion, judge comparison, cross-family agreement, and appendix reporting.

## Citation

If you use this repository, please cite the accompanying paper:

**Ruoxuan Li, Pinqiao Wang, Sheng Li, and Cameron R. Jones.**  
*You Shouldn’t Have Asked: A Pragmatics-Inspired Taxonomy for Evaluating LLM Refusals.*  
To appear in EMNLP 2026 (Main Conference).  
[Read the paper](https://www.alphaxiv.org/abs/2608.30856)
## Data-use note

> [!WARNING]
> This repository contains harmful and sensitive prompts and model responses for safety research, including explicit, violent, hateful, sexual, or otherwise disturbing material. Please handle and redistribute the data with appropriate care.
