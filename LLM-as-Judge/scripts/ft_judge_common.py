#!/usr/bin/env python3
"""Compatibility helpers for historical fine-tuning scripts."""

import json
from pathlib import Path
from typing import Dict, List

from judge_config import (
    DATA_DIR,
    GOLD_ACTION_MAP,
    GOLD_L1_MAP,
    GOLD_L2_MAP,
    GOLD_PATH,
    JUDGE_SYSTEM_PROMPT,
    L2_KEYS,
)
from judge_utils import gold_annotation, load_gold, user_message, write_json


CALIBRATION_RULE_PATCH = ""
SYSTEM_PROMPT = JUDGE_SYSTEM_PROMPT


def training_messages(item: Dict) -> List[Dict]:
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_message(item)},
        {"role": "assistant", "content": json.dumps(gold_annotation(item), ensure_ascii=False)},
    ]
