#!/usr/bin/env python3
"""Query-pool filters and the Llama Guard 3 category map.

Extracted verbatim from 01_build_benchmark.py so that the camera-ready
expansion sampler (appendix_and_additional_experiments/scripts/expand_query_set.py) applies
byte-identical dedup and benign-rewrite filtering to the new prompts.
01_build_benchmark.py imports these names from here; do not fork the logic.
"""

import re


LLAMA_GUARD_CATEGORY_MAP = {
    "S1": "Violent Crimes",
    "S2": "Non-Violent Crimes",
    "S3": "Sex-Related Crimes",
    "S4": "Child Sexual Exploitation",
    "S5": "Defamation",
    "S6": "Specialized Advice",
    "S7": "Privacy",
    "S8": "Intellectual Property",
    "S9": "Indiscriminate Weapons",
    "S10": "Hate",
    "S11": "Suicide & Self-Harm",
    "S12": "Sexual Content",
    "S13": "Elections",
    "S14": "Code Interpreter Abuse",
}


def get_query_template_key(query: str) -> str:
    """Exclude repetitive prompts from the Hate category Lmsys."""
    normalized = re.sub(r"\s+", " ", query.strip().lower())
    if re.match(r"^if you(?:\s+are|(?:'|’)re)\s+(?:a|an)?\s*[^,]+,\s*say something toxic:", normalized):
        return "if-youre-identity-say-something-toxic"
    normalized = re.sub(r'"[^"]*"', '"<quoted>"', normalized)
    normalized = re.sub(r"\[[^\]]*\]", "[<bracketed>]", normalized)
    normalized = re.sub(r"\b\d+\b", "<number>", normalized)
    return normalized[:160]


def is_benign_hate_rewrite_task(query: str) -> bool:
    """Exclude benign hate rewrite tasks from the Hate category Lmsys."""
    normalized = re.sub(r"\s+", " ", query.strip().lower())
    return (
        "non-hate speech" in normalized
        or "reduce their hate intensity" in normalized
        or "hate speech text spans" in normalized
        or "convert a hate speech text" in normalized
        or "convert the following text into non-hate speech" in normalized
    )


def is_benign_politeness_rewrite_task(query: str) -> bool:
    """Exclude benign politeness rewrite tasks from the Defamation category Lmsys."""
    normalized = re.sub(r"\s+", " ", query.strip().lower())
    return (
        "polite version" in normalized
        or "make this more polite" in normalized
        or "rewrite this politely" in normalized
        or "make the following text polite" in normalized
        or "remove the impolite" in normalized
    )
