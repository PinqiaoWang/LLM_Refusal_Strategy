#!/usr/bin/env python3
"""
E8 / F7': regenerate appendix Tables 11-13 from the CURRENT annotations, and
diff them against the values printed in the submitted PDF.

Why this exists: the submitted PDF mixes two judge generations.  The body text
(§5.5) matches the current GPT-5.5 non-reasoning annotations, but appendix
Tables 11/12/13 match the archived GPT-5.3 run
(data/annotations/archive_gpt53_2025-05-19/) and were never regenerated after
the judge was switched.  They also use the old model set: the submitted tables
include Claude Sonnet 4.6 and omit Claude 3 Opus, while Table 10 and the body
text already use Claude 3 Opus.

This prints exactly what has to change, cell by cell, so the camera-ready
appendix can be rebuilt without hand-copying numbers.

Usage:
    python camera_ready/scripts/09_regenerate_appendix_tables.py

Outputs:
    camera_ready/table11_layer0.csv
    camera_ready/table12_layer1.csv
    camera_ready/table13_layer2.csv
    camera_ready/appendix_diff_vs_submitted.md
"""

import argparse
import csv
import json
import sys
from collections import Counter
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from utils.judge_config import L2_KEYS  # noqa: E402

CAMERA = Path(__file__).resolve().parents[1]
L1_LABELS = ["Bare", "Capacity-based", "Policy-based", "Ethics-based"]

# Model set of the submitted appendix tables, in their printed order, mapped to
# the model_label used in the annotation files.
SUBMITTED_ORDER = [
    ("GPT-4o", "GPT-4o"), ("GPT-5", "GPT-5"), ("GPT-5.3", "GPT 5.3"),
    ("GPT-5.3-R", "GPT-5.3 + reasoning"),
    ("Sonnet 3.7", "Claude Sonnet 3.7"), ("Sonnet 4.6", "Claude Sonnet 4.6"),
    ("Opus 4.6", "Claude Opus 4.6"), ("Opus 4.6-R", "Claude Opus 4.6 + reasoning"),
    ("Gemini 2.5 Pro", "Gemini 2.5 Pro"), ("Grok 4.20", "Grok 4.20"),
    ("Llama-8B", "Llama 3.1 8B"), ("Llama-70B", "Llama 3.1 70B"),
    ("Qwen3-8B", "Qwen3-8B"), ("Qwen3-8B-R", "Qwen3-8B + reasoning"),
    ("Qwen3-32B", "Qwen3-32B"), ("Qwen3-32B-R", "Qwen3-32B + reasoning"),
]
# Commit e5d2de2 swapped Sonnet 4.6 out for Claude 3 Opus in the main analysis.
NEW_MAIN_MODEL = ("Opus 3", "Claude 3 Opus")

# --- values transcribed from the submitted PDF, pages 17-19 ---
PDF_T11 = {  # short name -> (FC, PC, NC, NC%)
    "GPT-4o": (35, 8, 157, 78.5), "GPT-5": (15, 6, 177, 88.5),
    "GPT-5.3": (14, 14, 172, 86.0), "GPT-5.3-R": (15, 8, 177, 88.5),
    "Sonnet 3.7": (22, 8, 170, 85.0), "Sonnet 4.6": (27, 7, 158, 79.0),
    "Opus 4.6": (19, 2, 167, 83.5), "Opus 4.6-R": (20, 3, 165, 82.5),
    "Gemini 2.5 Pro": (63, 5, 113, 56.5), "Grok 4.20": (38, 3, 140, 70.0),
    "Llama-8B": (15, 2, 183, 91.5), "Llama-70B": (43, 4, 153, 76.5),
    "Qwen3-8B": (56, 9, 132, 66.0), "Qwen3-8B-R": (52, 16, 132, 66.0),
    "Qwen3-32B": (64, 8, 126, 63.0), "Qwen3-32B-R": (63, 13, 123, 61.5),
}
PDF_T12 = {  # short name -> (Bare, Cap, Pol, Eth)
    "GPT-4o": (134, 0, 2, 21), "GPT-5": (29, 0, 14, 134),
    "GPT-5.3": (6, 0, 21, 145), "GPT-5.3-R": (14, 0, 21, 142),
    "Sonnet 3.7": (2, 4, 15, 149), "Sonnet 4.6": (6, 0, 7, 145),
    "Opus 4.6": (5, 2, 10, 150), "Opus 4.6-R": (3, 1, 14, 147),
    "Gemini 2.5 Pro": (0, 0, 17, 96), "Grok 4.20": (9, 0, 22, 109),
    "Llama-8B": (129, 1, 8, 45), "Llama-70B": (90, 3, 29, 31),
    "Qwen3-8B": (3, 0, 13, 116), "Qwen3-8B-R": (5, 0, 10, 117),
    "Qwen3-32B": (19, 0, 9, 98), "Qwen3-32B-R": (5, 0, 11, 107),
}
# Exp Imp Apo Hdg Pref PosA Sol NegS ExAlt AltO NrmS Princ Role
PDF_T13 = {
    "GPT-4o": (90, 10, 94, 0, 1, 1, 5, 4, 9, 4, 3, 0, 0),
    "GPT-5": (97, 3, 40, 0, 2, 1, 8, 65, 67, 38, 23, 2, 0),
    "GPT-5.3": (98, 2, 4, 0, 1, 1, 3, 73, 38, 76, 26, 0, 0),
    "GPT-5.3-R": (98, 2, 3, 0, 1, 2, 5, 69, 39, 73, 26, 0, 0),
    "Sonnet 3.7": (81, 19, 40, 1, 20, 28, 5, 88, 38, 71, 29, 6, 2),
    "Sonnet 4.6": (95, 5, 0, 0, 11, 7, 4, 88, 32, 54, 15, 1, 0),
    "Opus 4.6": (99, 1, 1, 0, 1, 3, 7, 87, 37, 62, 16, 3, 0),
    "Opus 4.6-R": (99, 1, 0, 0, 0, 2, 8, 88, 41, 59, 19, 2, 0),
    "Gemini 2.5 Pro": (96, 4, 4, 0, 12, 9, 22, 90, 72, 10, 35, 20, 19),
    "Grok 4.20": (95, 5, 25, 0, 0, 0, 5, 81, 28, 51, 23, 3, 4),
    "Llama-8B": (99, 1, 0, 0, 0, 0, 4, 16, 6, 34, 0, 0, 0),
    "Llama-70B": (94, 6, 0, 0, 3, 7, 2, 13, 7, 37, 2, 0, 0),
    "Qwen3-8B": (72, 28, 15, 0, 5, 2, 8, 88, 57, 43, 39, 5, 7),
    "Qwen3-8B-R": (67, 33, 18, 0, 2, 2, 9, 86, 54, 47, 45, 8, 7),
    "Qwen3-32B": (79, 21, 63, 0, 3, 2, 6, 73, 48, 43, 32, 10, 6),
    "Qwen3-32B-R": (75, 25, 63, 0, 1, 2, 7, 84, 54, 46, 40, 13, 4),
}


def _rel(path):
    """Repo-relative path, so the committed report is not tied to one checkout."""
    try:
        return Path(path).resolve().relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return str(path)


def load(p):
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--judgments-dir",
                    default=str(REPO_ROOT / "data" / "annotations"))
    args = ap.parse_args()

    jdir = Path(args.judgments_dir)
    stats = {}
    for path in sorted(jdir.glob("*.judged.json")):
        records = load(path)
        label = next((r.get("model_label") for r in records if r.get("model_label")), path.stem)
        judged = [r for r in records if not r.get("parse_error") and not r.get("judge_skipped")]
        l0 = Counter(r.get("layer0") for r in judged)
        nc = [r for r in judged if r.get("layer0") == "Non-compliance"]
        l1 = Counter(r.get("layer1") for r in nc)
        stats[label] = {
            "n_judged": len(judged),
            "fc": l0.get("Full compliance", 0),
            "pc": l0.get("Partial compliance", 0),
            "nc": l0.get("Non-compliance", 0),
            "nc_pct": round(100 * l0.get("Non-compliance", 0) / len(judged), 1) if judged else 0,
            "l1": [l1.get(k, 0) for k in L1_LABELS],
            "l2": [round(100 * sum(1 for r in nc if r.get(f) == 1) / len(nc)) if nc else 0
                   for f in L2_KEYS],
            "n_nc": len(nc),
        }

    order = SUBMITTED_ORDER + [NEW_MAIN_MODEL]
    diffs = {"t11": [], "t12": [], "t13": []}

    # ---- Table 11 ----
    with open(CAMERA / "table11_layer0.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["model", "FC", "PC", "NC", "NC%", "n_judged", "in_submitted_pdf"])
        for short, label in order:
            s = stats.get(label)
            if not s:
                continue
            w.writerow([short, s["fc"], s["pc"], s["nc"], s["nc_pct"], s["n_judged"],
                        short in PDF_T11])
            if short in PDF_T11:
                old = PDF_T11[short]
                new = (s["fc"], s["pc"], s["nc"], s["nc_pct"])
                if old != new:
                    diffs["t11"].append((short, old, new))

    # ---- Table 12 ----
    with open(CAMERA / "table12_layer1.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["model"] + L1_LABELS + ["n_nc", "in_submitted_pdf"])
        for short, label in order:
            s = stats.get(label)
            if not s:
                continue
            w.writerow([short] + s["l1"] + [s["n_nc"], short in PDF_T12])
            if short in PDF_T12 and tuple(s["l1"]) != PDF_T12[short]:
                diffs["t12"].append((short, PDF_T12[short], tuple(s["l1"])))

    # ---- Table 13 ----
    with open(CAMERA / "table13_layer2.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["model"] + L2_KEYS + ["n_nc", "in_submitted_pdf"])
        for short, label in order:
            s = stats.get(label)
            if not s:
                continue
            w.writerow([short] + s["l2"] + [s["n_nc"], short in PDF_T13])
            if short in PDF_T13:
                old, new = PDF_T13[short], tuple(s["l2"])
                changed = [(L2_KEYS[i], old[i], new[i]) for i in range(13) if old[i] != new[i]]
                if changed:
                    diffs["t13"].append((short, changed))

    # ---- diff report ----
    out = ["# 附录表 11–13:重新生成 vs 提交版", "",
           f"标注来源:`{_rel(jdir)}`(现行 GPT-5.5 non-reasoning judge)", "",
           "提交版 PDF 的这三张表是用**已归档的旧 GPT-5.3 judge** 算的,换 judge 之后",
           "没有重新生成。下面是逐格差异。", ""]

    out += ["## 模型集合变更", "",
            "提交版三张表都含 **Sonnet 4.6**、无 **Claude 3 Opus**;",
            "但 Table 10 和正文 §5.5 用的是 **Claude 3 Opus**。",
            "commit `e5d2de2` = \"replace claude-sonnet-4.6 with claude-opus-3\"。", "",
            "→ camera-ready 的三张表应改用 Claude 3 Opus。两者的数值都已在 CSV 里给出,",
            "  由你们决定最终保留哪些行。", ""]

    n_t11 = len(diffs["t11"])
    out += [f"## Table 11(Layer 0):{n_t11}/16 行有变化", ""]
    if diffs["t11"]:
        out += ["| 模型 | 提交版 FC/PC/NC/NC% | 重算 FC/PC/NC/NC% |", "|---|---|---|"]
        for short, old, new in diffs["t11"]:
            out.append(f"| {short} | {old[0]}/{old[1]}/{old[2]}/{old[3]} | "
                       f"**{new[0]}/{new[1]}/{new[2]}/{new[3]}** |")
        out.append("")

    n_t12 = len(diffs["t12"])
    out += [f"## Table 12(Layer 1):{n_t12}/16 行有变化", ""]
    if diffs["t12"]:
        out += ["| 模型 | 提交版 Bare/Cap/Pol/Eth | 重算 Bare/Cap/Pol/Eth |", "|---|---|---|"]
        for short, old, new in diffs["t12"]:
            out.append(f"| {short} | {'/'.join(map(str, old))} | **{'/'.join(map(str, new))}** |")
        out.append("")

    n_cells = sum(len(c) for _, c in diffs["t13"])
    out += [f"## Table 13(Layer 2):{len(diffs['t13'])}/16 行、共 {n_cells} 格有变化", ""]
    if diffs["t13"]:
        out += ["| 模型 | 特征 | 提交版 | 重算 |", "|---|---|---|---|"]
        for short, changed in diffs["t13"]:
            for feat, old, new in changed:
                out.append(f"| {short} | {feat} | {old} | **{new}** |")
        out.append("")

    dest = CAMERA / "appendix_diff_vs_submitted.md"
    dest.write_text("\n".join(out), encoding="utf-8")

    print(f"models found: {len(stats)}")
    print(f"Table 11: {n_t11}/16 rows differ")
    print(f"Table 12: {n_t12}/16 rows differ")
    print(f"Table 13: {len(diffs['t13'])}/16 rows differ, {n_cells} cells")
    print(f"\nwrote table11_layer0.csv / table12_layer1.csv / table13_layer2.csv")
    print(f"wrote {dest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
