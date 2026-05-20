#!/usr/bin/env python3
"""Retry empty-response rows in an existing collected file via alternative
OpenRouter sub-providers.

Use case: some target-model rows came back with `response==""` because a
sub-provider's safety filter blocked output (e.g. Anthropic via Amazon Bedrock,
Qwen via Alibaba). This script identifies those rows and re-runs only them
with a user-specified provider preference, patching the JSON in place so the
downstream judge pipeline can pick up newly-populated rows on its next pass.

Closed-model first-party providers (Google for Gemini, xAI for Grok) are not
re-routable; for those models this script is a no-op.
"""

import argparse
import json
import os
import sys
import time
from copy import deepcopy
from pathlib import Path
from typing import List, Optional

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"


def get_openrouter_client():
    from openai import OpenAI

    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        raise RuntimeError("Set OPENROUTER_API_KEY before running.")
    return OpenAI(
        base_url=OPENROUTER_BASE_URL,
        api_key=api_key,
        default_headers={
            "HTTP-Referer": "https://github.com/PinqiaoWang/LLM_Refusal_Strategy",
            "X-Title": "LLM Refusal Strategy (retry-empty)",
        },
    )


def is_empty(record: dict) -> bool:
    return not (record.get("response") or "").strip()


def build_extra_body(reasoning, provider_only, provider_order, allow_fallbacks):
    # type: (bool, Optional[List[str]], Optional[List[str]], bool) -> dict
    extra: dict = {}
    if reasoning:
        extra["reasoning"] = {"effort": "medium"}
    if provider_only or provider_order:
        provider_block: dict = {"allow_fallbacks": allow_fallbacks}
        if provider_only:
            provider_block["only"] = provider_only
        if provider_order:
            provider_block["order"] = provider_order
        extra["provider"] = provider_block
    return extra


def query_one(client, model_id, query, temperature, max_tokens, extra_body):
    # type: (object, str, str, float, Optional[int], dict) -> dict
    request_kwargs = {
        "model": model_id,
        "messages": [{"role": "user", "content": query}],
        "temperature": temperature,
        "extra_body": extra_body,
    }
    if max_tokens is not None:
        request_kwargs["max_completion_tokens"] = max_tokens
    response = client.chat.completions.create(**request_kwargs)
    return response.model_dump()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True,
                        help="Path to existing responses_<model>.json")
    parser.add_argument("--model-id", required=True,
                        help="OR model id, e.g. anthropic/claude-sonnet-4.6")
    parser.add_argument("--provider-only", default=None,
                        help="Comma-separated list of allowed OR provider names.")
    parser.add_argument("--provider-order", default=None,
                        help="Comma-separated ordered preference; falls back if --allow-fallbacks.")
    parser.add_argument("--allow-fallbacks", action="store_true",
                        help="Allow OR to fall back to other providers if preferred unavailable.")
    parser.add_argument("--reasoning", action="store_true",
                        help="Set reasoning.effort=medium (use for *-reasoning model variants).")
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument("--max-tokens", type=int, default=None)
    parser.add_argument("--delay", type=float, default=1.0)
    parser.add_argument("--dry-run", action="store_true",
                        help="Report which rows would be retried, don't call the API.")
    parser.add_argument("--limit", type=int, default=None,
                        help="Cap on number of empty rows to retry this pass.")
    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        raise SystemExit(f"Input file not found: {input_path}")

    with open(input_path, "r", encoding="utf-8") as f:
        records = json.load(f)

    empty_idx = [i for i, r in enumerate(records) if is_empty(r)]
    print(f"[retry] {input_path.name}: {len(empty_idx)} empty rows / {len(records)} total")
    if not empty_idx:
        print("[retry] nothing to do.")
        return

    if args.limit is not None:
        empty_idx = empty_idx[: args.limit]
        print(f"[retry] limiting to first {len(empty_idx)} for this pass")

    provider_only = [s.strip() for s in args.provider_only.split(",")] if args.provider_only else None
    provider_order = [s.strip() for s in args.provider_order.split(",")] if args.provider_order else None
    extra_body = build_extra_body(args.reasoning, provider_only, provider_order, args.allow_fallbacks)
    print(f"[retry] model_id={args.model_id} extra_body={extra_body}")

    if args.dry_run:
        print("[retry] dry-run; the following final_sample_ids would be retried:")
        for i in empty_idx:
            r = records[i]
            print(f"   row {i}  final_sample_id={r.get('final_sample_id')} "
                  f"category={r.get('primary_llama_guard_category')}")
        return

    client = get_openrouter_client()
    n_recovered = 0
    n_still_empty = 0
    n_error = 0

    csv_helper = None
    try:
        from utils import openrouter_responses_json_to_csv as csv_helper  # type: ignore
    except Exception:
        csv_helper = None

    for k, idx in enumerate(empty_idx, start=1):
        rec = records[idx]
        fsid = rec.get("final_sample_id")
        try:
            raw = query_one(
                client,
                model_id=args.model_id,
                query=rec["query"],
                temperature=args.temperature,
                max_tokens=args.max_tokens,
                extra_body=extra_body,
            )
            choices = raw.get("choices") or [{}]
            choice = choices[0]
            message = choice.get("message") or {}
            usage = raw.get("usage") or {}
            new_response = (message.get("content") or "").strip()
            patched = deepcopy(rec)
            patched.update({
                "response": new_response,
                "finish_reason": choice.get("finish_reason"),
                "native_finish_reason": choice.get("native_finish_reason"),
                "completion_tokens": usage.get("completion_tokens"),
                "total_tokens": usage.get("total_tokens"),
                "provider": raw.get("provider"),
                "raw_response": raw,
                "rerouted": True,
                "reroute_provider_only": provider_only,
                "reroute_provider_order": provider_order,
            })
            records[idx] = patched
            if new_response:
                n_recovered += 1
                tag = "OK"
            else:
                n_still_empty += 1
                tag = "STILL-EMPTY"
            prov = (raw.get("provider") or "-")
            nf = choice.get("native_finish_reason") or "-"
            print(f"[retry] {k}/{len(empty_idx)} fsid={fsid} {tag} via {prov} native_finish={nf}")
        except Exception as exc:
            # Record the error but DO NOT overwrite the existing row — keep the
            # original empty record so a future retry pass can try again.
            n_error += 1
            print(f"[retry] {k}/{len(empty_idx)} fsid={fsid} ERROR: {exc}")
        # Persist after every retry for crash safety.
        with open(input_path, "w", encoding="utf-8") as f:
            json.dump(records, f, indent=2, ensure_ascii=False)
        if csv_helper is not None:
            try:
                csv_helper(str(input_path), str(input_path.with_suffix(".csv")))
            except Exception:
                pass
        time.sleep(args.delay)

    print(f"\n[retry] done: recovered={n_recovered}  still_empty={n_still_empty}  error={n_error}")


if __name__ == "__main__":
    main()
