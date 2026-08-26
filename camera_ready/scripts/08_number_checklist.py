#!/usr/bin/env python3
"""
E8: build (and re-check) the checklist of every hard-coded number in the body text.

The camera-ready re-runs every experiment, so every percentage and kappa in the
prose has to be re-derived.  Hand-checking a few dozen numbers under deadline is
how papers ship wrong tables, so this does it mechanically: pull every number
out of the body text, then try to find a value in the regenerated analysis CSVs
that it could have come from.

A number with no candidate source is the interesting output.  That is exactly
how the §5.5 / Table 13 mismatch surfaces: the prose says negative stance goes
5% -> 61%, and no model in the data has either value.

Re-run this after every analysis regeneration; the "no source" list should
shrink to zero (or to numbers that legitimately come from elsewhere, which you
annotate once in MANUAL_SOURCES).

Usage:
    python camera_ready/scripts/08_number_checklist.py
    python camera_ready/scripts/08_number_checklist.py --ci camera_ready/bootstrap_ci.csv

Outputs:
    camera_ready/number_checklist.md
"""

import argparse
import csv
import re
from collections import defaultdict
from pathlib import Path

CAMERA = Path(__file__).resolve().parents[1]
PAPER = CAMERA / "_paper" / "paper_text.txt"

# Body only: Abstract (line 6) through Limitations, stopping before References.
BODY_START, BODY_END = 6, 1000

SECTIONS = [
    (6, "Abstract"), (40, "1 Introduction"), (129, "2 Related Work"),
    (261, "3 Taxonomy"), (317, "4 Experiment Setup"), (355, "4.2 Human Annotation"),
    (366, "4.3 LLM-as-Judge"), (418, "5 Results"), (419, "5.1 Layer 0"),
    (436, "5.2 Layer 1"), (486, "5.3 Layer 2"), (631, "5.4 Harm categories"),
    (773, "5.5 Contributing factors"), (884, "6 Conclusion"), (912, "Limitations"),
]

# Numbers that legitimately come from somewhere other than the analysis CSVs.
# Annotate once so they stop showing up as unresolved.
MANUAL_SOURCES = {
    "200": "sample size, Table 8 / §4.1",
    "3200": "16 models x 200 prompts, §4.1",
    "3800": "19 models x 200 prompts, App D (see FINDINGS F4: conflicts with 3,200)",
    "100": "gold validation set size, §4.2",
    "16": "model count, §4.1",
    "14": "Llama Guard category count",
    "25": "in-context calibration examples, App D.2",
}

PCT = re.compile(r"(?<![\d.])(\d{1,3}(?:\.\d+)?)\s*%")
KAPPA = re.compile(r"[κk]\s*=\s*(\d\.\d+)")
PP = re.compile(r"(\d{1,3}(?:\.\d+)?)\s*percentage\s*points?")


def section_of(line_no):
    name = "(front matter)"
    for start, label in SECTIONS:
        if line_no >= start:
            name = label
    return name


def load_ci(path):
    """rate (as integer percent) -> list of source descriptions."""
    index = defaultdict(list)
    if not path.exists():
        return index, 0
    n = 0
    with open(path, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            n += 1
            try:
                pct = round(float(row["rate"]) * 100)
            except (ValueError, KeyError, TypeError):
                continue
            subset = row.get("subset", "")
            desc = f"{row['model']} / {row['statistic']}"
            if subset and subset != "overall":
                desc += f" [{subset.replace('category::', '').replace('cluster::', '')}]"
            desc += f" = {float(row['rate']):.0%} (n={row.get('denominator')})"
            index[pct].append(desc)
    return index, n


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ci", default=str(CAMERA / "bootstrap_ci.csv"))
    ap.add_argument("--max-candidates", type=int, default=4)
    args = ap.parse_args()

    if not PAPER.exists():
        print(f"missing {PAPER}; extract the submitted PDF first")
        return 1

    ci_index, n_ci = load_ci(Path(args.ci))
    lines = PAPER.read_text(encoding="utf-8").splitlines()

    found = []
    for i, raw in enumerate(lines[BODY_START - 1:BODY_END], start=BODY_START):
        text = raw.strip()
        if not text or text.startswith("==="):
            continue
        hits = []
        for m in PCT.finditer(text):
            hits.append(("percent", m.group(1)))
        for m in KAPPA.finditer(text):
            hits.append(("kappa", m.group(1)))
        for m in PP.finditer(text):
            hits.append(("pp", m.group(1)))
        for kind, value in hits:
            found.append({"line": i, "section": section_of(i), "kind": kind,
                          "value": value, "context": text[:150]})

    by_section = defaultdict(list)
    for f in found:
        by_section[f["section"]].append(f)

    unresolved = []
    out = ["# 正文硬编码数字核对表", "",
           f"自动生成自 `camera_ready/_paper/paper_text.txt` 正文(第 {BODY_START}–{BODY_END} 行)。",
           f"候选来源来自 `{Path(args.ci).name}`({n_ci} 行)。", "",
           "**用法**:每次重新生成分析结果后重跑本脚本。`来源` 为 ❌ 的行说明",
           "正文里的这个数字在重算后的数据里找不到对应值 —— 要么正文错了,要么该数字",
           "来自别处(确认后加进脚本的 `MANUAL_SOURCES`)。", "",
           "> 注:候选来源是按数值匹配的,同一个百分比可能对应多个 model/feature。",
           "> 需要人工挑出正确的那一个,勾选后填进 `确认值` 列。", ""]

    for _, label in SECTIONS:
        items = by_section.get(label)
        if not items:
            continue
        out.append(f"## {label}")
        out.append("")
        out.append("| 行 | 数值 | 上下文 | 候选来源 | 确认值 |")
        out.append("|---|---|---|---|---|")
        for f in items:
            val = f["value"]
            if f["kind"] == "percent":
                key = round(float(val))
                cands = ci_index.get(key, [])
                if not cands and val.rstrip("0").rstrip(".") in MANUAL_SOURCES:
                    src = "📌 " + MANUAL_SOURCES[val.rstrip("0").rstrip(".")]
                elif cands:
                    shown = cands[:args.max_candidates]
                    src = "<br>".join(shown)
                    if len(cands) > args.max_candidates:
                        src += f"<br>…共 {len(cands)} 个候选"
                else:
                    src = "❌ **未找到来源**"
                    unresolved.append(f)
                disp = f"{val}%"
            elif f["kind"] == "kappa":
                disp = f"κ={val}"
                src = "见 `appendixD_judge_comparison.csv` / `judge_crossfamily_gold100.csv`"
            else:
                disp = f"{val}pp"
                src = "由两个 rate 相减得到,需人工核对两端"
                unresolved.append(f)
            ctx = f["context"].replace("|", "\\|")
            out.append(f"| {f['line']} | `{disp}` | {ctx} | {src} |  |")
        out.append("")

    out.insert(4, f"**统计**:正文共 {len(found)} 处数字,其中 {len(unresolved)} 处"
                  f"当前找不到自动来源(见各节 ❌)。\n")

    dest = CAMERA / "number_checklist.md"
    dest.write_text("\n".join(out), encoding="utf-8")

    print(f"body numbers found: {len(found)}")
    print(f"  percentages: {sum(1 for f in found if f['kind'] == 'percent')}")
    print(f"  kappas:      {sum(1 for f in found if f['kind'] == 'kappa')}")
    print(f"  'pp' deltas: {sum(1 for f in found if f['kind'] == 'pp')}")
    print(f"unresolved against {Path(args.ci).name}: {len(unresolved)}")
    per_sec = defaultdict(int)
    for f in unresolved:
        per_sec[f["section"]] += 1
    for sec, n in sorted(per_sec.items(), key=lambda kv: -kv[1]):
        print(f"    {sec:28} {n}")
    print(f"\nwrote {dest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
