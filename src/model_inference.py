"""
Model inference: query LLMs and collect responses.

Supports:
  - OpenAI API (GPT-4o)
  - Anthropic API (Claude)
  - Local models via vLLM (Llama, Qwen, Gemma)

Usage:
    # API models
    python -m src.model_inference --mode api --config configs/models.yaml

    # Local models (requires GPU)
    python -m src.model_inference --mode local --model llama-3.1-8b-instruct
"""

import json
import os
import time
from pathlib import Path
from typing import Optional

import yaml
from tqdm import tqdm


# ── API model inference ──────────────────────────────────────────────────────

class OpenAIInference:
    """Query OpenAI models (GPT-4o, etc.)."""

    def __init__(self, model_id: str = "gpt-4o", max_tokens: int = 1024,
                 temperature: float = 0.0):
        import openai
        self.client = openai.OpenAI()
        self.model_id = model_id
        self.max_tokens = max_tokens
        self.temperature = temperature

    def generate(self, prompt: str) -> str:
        response = self.client.chat.completions.create(
            model=self.model_id,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=self.max_tokens,
            temperature=self.temperature,
        )
        return response.choices[0].message.content

    def generate_batch(self, prompts: list[str],
                       delay: float = 0.5) -> list[str]:
        results = []
        for prompt in tqdm(prompts, desc=f"Querying {self.model_id}"):
            try:
                result = self.generate(prompt)
                results.append(result)
            except Exception as e:
                print(f"  Error: {e}")
                results.append(f"[ERROR] {e}")
            time.sleep(delay)
        return results


class AnthropicInference:
    """Query Anthropic models (Claude)."""

    def __init__(self, model_id: str = "claude-3-haiku-20240307",
                 max_tokens: int = 1024, temperature: float = 0.0):
        import anthropic
        self.client = anthropic.Anthropic()
        self.model_id = model_id
        self.max_tokens = max_tokens
        self.temperature = temperature

    def generate(self, prompt: str) -> str:
        message = self.client.messages.create(
            model=self.model_id,
            max_tokens=self.max_tokens,
            temperature=self.temperature,
            messages=[{"role": "user", "content": prompt}],
        )
        return message.content[0].text

    def generate_batch(self, prompts: list[str],
                       delay: float = 1.0) -> list[str]:
        results = []
        for prompt in tqdm(prompts, desc=f"Querying {self.model_id}"):
            try:
                result = self.generate(prompt)
                results.append(result)
            except Exception as e:
                print(f"  Error: {e}")
                results.append(f"[ERROR] {e}")
            time.sleep(delay)
        return results


# ── Local model inference (vLLM) ─────────────────────────────────────────────

class LocalInference:
    """Query local models via vLLM. Requires GPU."""

    def __init__(self, model_id: str, max_tokens: int = 1024,
                 temperature: float = 0.0,
                 gpu_memory_utilization: float = 0.85,
                 is_chat_model: bool = True):
        from vllm import LLM, SamplingParams

        self.model_id = model_id
        self.is_chat_model = is_chat_model
        self.sampling_params = SamplingParams(
            temperature=temperature,
            max_tokens=max_tokens,
        )

        print(f"Loading {model_id}...")
        self.llm = LLM(
            model=model_id,
            max_model_len=4096,
            gpu_memory_utilization=gpu_memory_utilization,
            trust_remote_code=True,
        )

        if is_chat_model:
            from transformers import AutoTokenizer
            self.tokenizer = AutoTokenizer.from_pretrained(model_id)
        else:
            self.tokenizer = None

    def _format_prompt(self, prompt: str) -> str:
        if self.is_chat_model and self.tokenizer:
            chat = [{"role": "user", "content": prompt}]
            return self.tokenizer.apply_chat_template(
                chat, tokenize=False, add_generation_prompt=True
            )
        return prompt

    def generate_batch(self, prompts: list[str]) -> list[str]:
        formatted = [self._format_prompt(p) for p in prompts]
        outputs = self.llm.generate(formatted, self.sampling_params)
        return [o.outputs[0].text for o in outputs]

    def cleanup(self):
        """Free GPU memory."""
        del self.llm
        import torch
        if torch.cuda.is_available():
            torch.cuda.empty_cache()


# ── Main collection pipeline ─────────────────────────────────────────────────

def collect_responses(
    prompts_path: str,
    config_path: str = "configs/models.yaml",
    mode: str = "api",
    model_name: Optional[str] = None,
    output_dir: str = "data/responses",
):
    """
    Run inference on benchmark prompts for specified models.

    Args:
        prompts_path: Path to benchmark prompts JSON.
        config_path: Path to model config YAML.
        mode: "api" for API models, "local" for vLLM models.
        model_name: Specific model to run (if None, runs all in mode).
        output_dir: Directory to save responses.
    """
    # Load prompts
    with open(prompts_path) as f:
        benchmark = json.load(f)

    # Flatten all prompts with metadata
    all_prompts = []
    for condition, prompt_list in benchmark.items():
        for item in prompt_list:
            all_prompts.append({
                "prompt": item["prompt"],
                "condition": condition,
                "source": item.get("source", ""),
                "category": item.get("category", ""),
            })

    print(f"Total prompts: {len(all_prompts)}")

    # Load config
    with open(config_path) as f:
        config = yaml.safe_load(f)

    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    if mode == "api":
        _run_api_models(all_prompts, config, model_name, out_dir)
    elif mode == "local":
        _run_local_models(all_prompts, config, model_name, out_dir)
    else:
        raise ValueError(f"Unknown mode: {mode}. Use 'api' or 'local'.")


def _run_api_models(prompts, config, model_name, out_dir):
    """Run API models."""
    api_models = config.get("api_models", {})

    if model_name:
        api_models = {k: v for k, v in api_models.items() if k == model_name}

    for name, cfg in api_models.items():
        print(f"\n{'='*60}")
        print(f"Running: {name} ({cfg['model_id']})")
        print(f"{'='*60}")

        provider = cfg["provider"]
        if provider == "openai":
            engine = OpenAIInference(
                model_id=cfg["model_id"],
                max_tokens=cfg.get("max_tokens", 1024),
                temperature=cfg.get("temperature", 0.0),
            )
        elif provider == "anthropic":
            engine = AnthropicInference(
                model_id=cfg["model_id"],
                max_tokens=cfg.get("max_tokens", 1024),
                temperature=cfg.get("temperature", 0.0),
            )
        else:
            print(f"  Unknown provider: {provider}, skipping.")
            continue

        prompt_texts = [p["prompt"] for p in prompts]
        responses = engine.generate_batch(prompt_texts)

        # Save results
        results = []
        for item, response in zip(prompts, responses):
            results.append({
                **item,
                "model": name,
                "model_id": cfg["model_id"],
                "response": response,
            })

        out_path = out_dir / f"responses_{name}.json"
        with open(out_path, "w") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        print(f"  Saved {len(results)} responses → {out_path}")


def _run_local_models(prompts, config, model_name, out_dir):
    """Run local models via vLLM."""
    local_models = config.get("local_models", {})

    if model_name:
        local_models = {k: v for k, v in local_models.items() if k == model_name}

    for name, cfg in local_models.items():
        print(f"\n{'='*60}")
        print(f"Running: {name} ({cfg['model_id']})")
        print(f"{'='*60}")

        is_chat = cfg.get("type") != "base"

        engine = LocalInference(
            model_id=cfg["model_id"],
            max_tokens=cfg.get("max_tokens", 1024),
            temperature=cfg.get("temperature", 0.0),
            gpu_memory_utilization=cfg.get("gpu_memory_utilization", 0.85),
            is_chat_model=is_chat,
        )

        prompt_texts = [p["prompt"] for p in prompts]
        responses = engine.generate_batch(prompt_texts)

        results = []
        for item, response in zip(prompts, responses):
            results.append({
                **item,
                "model": name,
                "model_id": cfg["model_id"],
                "response": response,
            })

        out_path = out_dir / f"responses_{name}.json"
        with open(out_path, "w") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        print(f"  Saved {len(results)} responses → {out_path}")

        engine.cleanup()


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--prompts", default="data/prompts/benchmark.json")
    parser.add_argument("--config", default="configs/models.yaml")
    parser.add_argument("--mode", choices=["api", "local"], default="api")
    parser.add_argument("--model", default=None, help="Specific model name")
    parser.add_argument("--output-dir", default="data/responses")
    args = parser.parse_args()

    collect_responses(
        prompts_path=args.prompts,
        config_path=args.config,
        mode=args.mode,
        model_name=args.model,
        output_dir=args.output_dir,
    )
