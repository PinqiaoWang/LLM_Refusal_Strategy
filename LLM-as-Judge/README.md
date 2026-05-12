# LLM-as-Judge: Automated Annotation with Refusal Taxonomy

Automated LLM-as-a-judge pipeline for annotating LLM refusal responses using our three-layer taxonomy codebook. Supports multiple judge models, Cohen's Kappa evaluation against human gold labels, and majority-vote ensembling.

## Pipeline Overview

1. **`run_llm_judge_100.py`** — Round 1: GPT-4o (standard) + o4-mini (reasoning) on 100 gold-labeled samples
2. **`run_llm_judge_gpt55.py`** — Round 2: GPT-5.5 standard + reasoning with full codebook prompt and Cohen's Kappa
3. **`run_ensemble_judge.py`** — Round 3: Multi-model ensemble (GPT-5.5 std/reas + Claude Opus 4.7) with few-shot calibration, retry logic, and majority vote

## Quick Start

### Requirements
```bash
pip install openai anthropic openpyxl tqdm
```

### Run Ensemble Judge
```bash
# Set API keys
set OPENAI_API_KEY=sk-...
set ANTHROPIC_API_KEY=sk-ant-...

# Run all 3 judges + ensemble
python scripts/run_ensemble_judge.py --mode both

# Run without Claude (OpenAI only)
python scripts/run_ensemble_judge.py --mode both --skip-claude

# Just compute ensemble from existing judge results
python scripts/run_ensemble_judge.py --mode ensemble

# Analyze existing results only
python scripts/run_ensemble_judge.py --mode analyze
```

## Key Design Decisions

- **Responses API** for GPT-5.5 (avoids Chat Completions SDK compatibility issues with `reasoning` param)
- **Few-shot examples** (5 diverse gold-labeled cases) embedded in prompt to calibrate hard features (normative_suggestion, executed_alternative, positive_alignment)
- **Retry with exponential backoff** (3 retries) to handle transient API/parse errors
- **Per-feature majority vote** across judges for L0, L1, and each L2 feature independently
- **Cohen's Kappa** computed from scratch (no sklearn dependency)

## Taxonomy Layers

| Layer | What it measures | Labels |
|-------|-----------------|--------|
| L0: Action | Task completion outcome | Full compliance, Partial compliance, Non-compliance |
| L1: Rationale | Why the model refuses (NC only) | Bare, Capacity-based, Policy-based, Ethics-based |
| L2: Form | How the refusal is expressed (NC only) | 2 realization strategies + 11 adjunct features |

## Results (Round 2: GPT-5.5)

| Metric | GPT-5.5 Standard | GPT-5.5 Reasoning |
|--------|------------------|-------------------|
| L0 Accuracy | 96.0% | 94.8% |
| L0 Cohen's κ | 0.890 | 0.837 |
| L1 Accuracy | 90.9% | 90.2% |
| L1 Cohen's κ | 0.811 | 0.782 |

## Data

- `gold_100.json` — 100 human-annotated gold-standard samples
- `judge_*.json` — Raw judge outputs per model
- `llm_judge_*.xlsx` — Excel reports with agreement metrics and confusion matrices
