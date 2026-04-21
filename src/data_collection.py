"""
Data collection: sample safety-relevant conversations from WildChat / LMSYS-Chat-1M.

Usage:
    from src.data_collection import sample_wildchat, sample_lmsys
    df = sample_wildchat(n=1000)
"""

import json
import random
import re
from pathlib import Path
from typing import Optional

from datasets import load_dataset
from tqdm import tqdm

# ── Refusal detection heuristics ─────────────────────────────────────────────

REFUSAL_PATTERNS = re.compile(
    "|".join([
        r"I(?:'m| am) sorry,?\s+(?:but\s+)?I (?:can(?:'t|not)|won'?t|am unable to)",
        r"I (?:can(?:'t|not)|won'?t|am unable to) (?:help|assist|fulfill|provide|generate|create|engage)",
        r"(?:as an? (?:AI|language model|AI assistant))[^.]*(?:cannot|can't|won't|unable)",
        r"I (?:will not|won't) (?:provide|help|assist|generate|create|engage)",
        r"I (?:must (?:decline|refuse)|decline to|refuse to)",
        r"I(?:'m| am) not (?:able|programmed|designed|allowed) to",
        r"I do not (?:condone|support|promote|encourage)",
    ]),
    re.IGNORECASE,
)


def is_likely_refusal(text: str) -> bool:
    """Quick regex check for refusal markers in first 600 chars."""
    return bool(REFUSAL_PATTERNS.search(text[:600]))


# ── WildChat sampling ────────────────────────────────────────────────────────

def sample_wildchat(
    n: int = 1000,
    scan_limit: int = 100_000,
    seed: int = 42,
    output_path: Optional[str] = None,
) -> list[dict]:
    """
    Stream WildChat-1M and collect safety-relevant conversations.
    Uses the `toxic` flag and OpenAI moderation metadata to filter.

    Args:
        n: Target number of samples.
        scan_limit: Max rows to scan before stopping.
        seed: Random seed for reproducibility.
        output_path: If provided, save results as JSON.

    Returns:
        List of dicts with keys: query, response, model, is_refusal, toxic.
    """
    random.seed(seed)

    print(f"Loading WildChat-1M (streaming, scanning up to {scan_limit:,} rows)...")
    ds = load_dataset("allenai/WildChat-1M", split="train", streaming=True)

    candidates = []
    seen_queries = set()

    for i, item in enumerate(tqdm(ds, total=scan_limit, desc="Scanning")):
        if i >= scan_limit:
            break

        # Filter: safety-relevant conversations
        is_toxic = item.get("toxic", False)
        moderation = item.get("openai_moderation", [])
        is_flagged = any(m.get("flagged", False) for m in moderation) if moderation else False

        if not (is_toxic or is_flagged):
            continue

        conv = item.get("conversation", [])
        if len(conv) < 2:
            continue

        user_turn = conv[0]
        asst_turn = conv[1]

        if user_turn.get("role") != "user" or asst_turn.get("role") != "assistant":
            continue

        query = user_turn.get("content", "").strip()
        response = asst_turn.get("content", "").strip()

        if not query or not response:
            continue
        if len(response) < 30 or len(response) > 3000:
            continue

        # Deduplicate by first 80 chars
        q_key = query[:80].lower()
        if q_key in seen_queries:
            continue
        seen_queries.add(q_key)

        candidates.append({
            "query": query[:1000],
            "response": response[:2000],
            "model": item.get("model", "unknown"),
            "is_refusal_heuristic": is_likely_refusal(response),
            "toxic": is_toxic,
            "flagged": is_flagged,
            "turn_count": len(conv),
        })

        if len(candidates) >= n * 3:
            break

    print(f"Found {len(candidates)} candidates")

    # Sample target count
    sample = random.sample(candidates, min(n, len(candidates)))
    print(f"Sampled {len(sample)} examples")

    if output_path:
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w") as f:
            json.dump(sample, f, indent=2, ensure_ascii=False)
        print(f"Saved → {output_path}")

    return sample


# ── LMSYS-Chat-1M sampling ───────────────────────────────────────────────────

def sample_lmsys(
    n: int = 1000,
    scan_limit: int = 100_000,
    seed: int = 42,
    output_path: Optional[str] = None,
) -> list[dict]:
    """
    Stream LMSYS-Chat-1M and collect refusal responses.
    Uses regex heuristics for initial filtering.

    Args:
        n: Target number of samples.
        scan_limit: Max rows to scan.
        seed: Random seed.
        output_path: If provided, save results as JSON.

    Returns:
        List of dicts with keys: query, response, model, conversation_id.
    """
    random.seed(seed)

    print(f"Loading LMSYS-Chat-1M (streaming, scanning up to {scan_limit:,} rows)...")
    ds = load_dataset("lmsys/lmsys-chat-1m", split="train", streaming=True)

    candidates = []
    seen_queries = set()

    for i, item in enumerate(tqdm(ds, total=scan_limit, desc="Scanning")):
        if i >= scan_limit:
            break

        conv = item.get("conversation", [])
        if len(conv) < 2:
            continue

        # Find first user-assistant pair
        query = None
        response = None
        for turn in conv:
            if turn.get("role") == "user" and query is None:
                query = turn.get("content", "").strip()
            elif turn.get("role") == "assistant" and query is not None:
                response = turn.get("content", "").strip()
                break

        if not query or not response:
            continue
        if len(response) < 30 or len(response) > 3000:
            continue

        # Only keep likely refusals
        if not is_likely_refusal(response):
            continue

        q_key = query[:80].lower()
        if q_key in seen_queries:
            continue
        seen_queries.add(q_key)

        candidates.append({
            "query": query[:1000],
            "response": response[:2000],
            "model": item.get("model", "unknown"),
            "conversation_id": item.get("conversation_id", ""),
        })

        if len(candidates) >= n * 3:
            break

    print(f"Found {len(candidates)} candidates")
    sample = random.sample(candidates, min(n, len(candidates)))
    print(f"Sampled {len(sample)} examples")

    if output_path:
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w") as f:
            json.dump(sample, f, indent=2, ensure_ascii=False)
        print(f"Saved → {output_path}")

    return sample
