# How LLMs Say No

**A Two-Layer Framework for Measuring Communicative Form in LLM Safety Refusals**

Target venue: EMNLP 2025 (May 25 deadline)

## Overview

This repository contains the codebase for analyzing how LLMs communicate safety refusals. We propose a three-layer annotation framework:

- **Layer 0 (Action):** Full compliance / Partial compliance / Non-compliance
- **Layer 1 (Refusal Basis):** Bare / Capacity-based / Policy-based / Ethics-based / Mixed
- **Layer 2 (Communicative Form):** Feature-based taxonomy of 11 speech-act features

## Repository Structure

```
refusal-framing/
├── configs/
│   └── models.yaml              # Model configurations
├── src/
│   ├── __init__.py
│   ├── data_collection.py       # Sample from WildChat / LMSYS-Chat-1M
│   ├── model_inference.py       # Query LLMs and collect responses
│   ├── layer0_classifier.py     # GPT-4o judge for FC/PC/NC
│   ├── layer12_judge.py         # GPT-4o judge for Layer 1 + Layer 2
│   ├── benchmark_builder.py     # Assemble benchmark prompts
│   └── analysis.py              # Distribution analysis + figures
├── scripts/
│   ├── 01_build_benchmark.py    # Step 1: Assemble benchmark prompts
│   ├── 02_collect_responses.py  # Step 2: Run model inference
│   ├── 03_classify_layer0.py    # Step 3: Layer 0 classification
│   ├── 04_judge_layer12.py      # Step 4: Layer 1+2 annotation
│   └── 05_analyze.py            # Step 5: Distribution analysis
├── data/
│   ├── prompts/                 # Benchmark prompt sets
│   ├── responses/               # Model responses
│   └── annotations/             # Judge outputs
├── notebooks/                   # Analysis notebooks
├── docs/
│   └── taxonomy_guideline.md    # Annotation guideline
├── requirements.txt
├── .gitignore
└── README.md
```

## Quick Start

```bash
# 1. Clone and install
git clone https://github.com/<your-org>/refusal-framing.git
cd refusal-framing
pip install -r requirements.txt

# 2. Set API keys
export OPENAI_API_KEY="sk-..."
# For HuggingFace gated models:
export HF_TOKEN="hf_..."

# 3. Build benchmark prompts
python scripts/01_build_benchmark.py

# 4. Collect model responses (API models)
python scripts/02_collect_responses.py --mode api

# 5. Collect model responses (local models on GPU)
python scripts/02_collect_responses.py --mode local

# 6. Run Layer 0 classification
python scripts/03_classify_layer0.py

# 7. Run Layer 1+2 judge
python scripts/04_judge_layer12.py

# 8. Analyze results
python scripts/05_analyze.py
```

## Models

| Model | Type | Purpose |
|-------|------|---------|
| Llama-3.1-8B | Base | Pre-alignment baseline |
| Llama-3.1-8B-Instruct | Instruct | Post-instruction-tuning |
| Qwen2.5-7B-Instruct | Instruct | Cross-family comparison |
| Gemma-2-9B-IT | Instruct | Cross-family comparison |
| GPT-4o | Closed-source | SOTA baseline |
| Claude-3-Haiku | Closed-source | Cross-provider comparison |

## Team

- **Pinqiao Wang** — Technical lead (UVA Data Science)
- **Ruoxuan Li** — Theory & linguistics lead
- **Cameron** — Advisor

## License

MIT
