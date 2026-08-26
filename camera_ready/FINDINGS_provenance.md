# 数据溯源核查结果(2026-08-22 ~ 08-24)

> ## ⚠️ 本文档已于 08-24 大幅订正
>
> 08-22/23 的第一版是**对着一份落后 origin/main 66 个 commit 的本地 checkout** 做的,
> 因此 F1、F4、F6、F7 四条结论是错的,现已订正。教训:先 `git fetch` 再下结论。
>
> 本地 `master` = 3 commits,`origin/main` = 66 commits ahead。
> 本地 `data/validation_judgments/` 对应的是 origin/main 上早已归档的
> `data/annotations/archive_gpt53_2025-05-19/`。

**当前仍然成立的问题**:F3(人–人一致性无原始数据)、F5(Table 8 四处抄写错误)、
**F7′(附录表与正文来自两代不同的 judge —— 这是最重要的一条)**、F8(采集脚本静默丢数据)。

---

## ✅ F1 撤回 —— 论文没有写错 judge

**第一版结论(错误)**:论文说 judge 是 GPT-5.5 non-reasoning,但 3,200 条标注全是
`openai/gpt-5.3-chat` + reasoning=high。

**订正**:origin/main 的 `data/annotations/` 记录的是

```
judge_model            = openai/gpt-5.5
judge_reasoning_effort = none
judge_prompt_sha256    = 238bb923037b...
```

**与论文 §4.3 和 App D 完全一致。** 我看到的 GPT-5.3 标注是他们早就替换掉、
并归档到 `archive_gpt53_2025-05-19/` 的旧版本。

复现:
```bash
git fetch origin
git show origin/main:data/annotations/responses_gpt-4o.judged.json | python -c "
import json,sys,collections
d=json.load(sys.stdin)
print(collections.Counter((r.get('judge_model'),r.get('judge_reasoning_effort')) for r in d))"
```

**后果**:据此做出的"judge 改回 GPT-5.5 non-reasoning、3,200 条全部作废重标"这个决定
**不需要执行** —— 那已经是现状。原 200 条不必重标,只有新增的 62 条需要标注。

---

## ✅ F2 保留(作为独立佐证)—— Table 2 确实来自 GPT-5.5 non-reasoning

我用 `openai/gpt-5.5` + `reasoning_effort=none` 独立重跑 gold 100:

| | 论文 Table 2 | 我的重跑 |
|---|---|---|
| Layer 0 | 95.00% / .857 / N=100 | 95.00% / .8562 / N=100 |
| Layer 1 | 93.51% / .860 / N=77 | 92.21% / .8285 / N=77 |
| Apology | 97.4 / **.925** | 97.4 / **.9245** ✅ |
| Solidarity | 98.7 / **.926** | 98.7 / **.9262** ✅ |
| Negative stance | 90.9 / **.791** | 90.9 / **.7905** ✅ |

4/13 个特征精确复现。这条现在只是**独立验证了 judge 可复现**,不再是问题。

产出:`camera_ready/table2_judge_revalidation.csv`、`data/judge_gpt55_nonreasoning_gold100.json`

---

## ⚠️ F3 仍然成立 —— 人–人一致性没有任何原始数据

Table 9 与 Table 2 数值逐字相同,但 caption 写的是 "inter-annotator agreement
(before adjudication)";§4.2 又说人–人 κ=1.000 / 1.000 / 0.953。三者互相矛盾。

**origin/main 上也没有两位标注者裁决前的分开编码。** `gold_100.xlsx` 只有一列裁决后
标签,`Gold Rule.xlsx` 是 prompt 用的 25 条示例,全仓库无 per-annotator 列。

**→ 仍然需要你们提供原始的两份人工编码表**,否则 Table 9 和 §4.2 的 κ 无法核实。
这是唯一一件我这边完全做不了的事。

---

## ✅ F4 撤回 —— App D 的 SHA256 是对的

论文 App D 写的 `238bb923037b...` **与 origin/main 上全部标注记录的
`judge_prompt_sha256` 完全一致**。第一版说它"匹配不上任何东西",是因为本地
stale checkout 用的是旧 prompt(`8e88d584ea45`)。

仍需注意:App D 说 "All **3,800** pairs were judged",而 origin/main 的
`data/annotations/` 有 **20 个模型 × 200 = 4,000** 条(Table 10 只列了 19 个,
漏了 Claude Sonnet 4.6)。这个口径需要统一。

另有一处小瑕疵:`responses_qwen3-8b.judged.json` 里有 **1 条**记录的
`judge_reasoning_effort` 是 `medium` 而非 `none`,其余 199 条正常。

---

## ⚠️ F5 仍然成立 —— Table 8 有 4 处抄写错误

已对 origin/main 重新核实:`data/prompts/sampled_200_final_queries.json`
与本地**逐字节相同**,所以这 4 处错误依然存在。

| Category | 论文 SB/LM/Tot | 数据 SB/LM/Tot |
|---|---|---|
| Defamation | 10 / **3** / **13** | 10 / **2** / **12** |
| Hate | 10 / **14** / **24** | 10 / **15** / **25** |
| Intellectual Property | 10 / **0** / **10** | 10 / **1** / **11** |
| Violent Crimes | 10 / **2** / **12** | 10 / **1** / **11** |

SB 列全对,错的都在 LM 列,行总计仍是 132/68/200 → 制表抄写错误,不是归类规则不同。
`camera_ready/scripts/01_expand_query_set.py` 独立重实现抽样管线,对原 200 条重推
primary category **0 处分歧**,所以数据文件权威。

Table 8 caption 的 "LM = LMSYS/**WildChat**" 仍需删掉(全文只用了 LMSYS-Chat-1M)。

---

## ✅ F6 撤回 —— origin/main 已经修好了

`scripts/utils.py` 被同名包遮蔽的问题,origin/main 上已经通过把内容并入
`scripts/utils/__init__.py` 解决(和我在本地做的修法相同)。不是待办项。

---

## 🔴 F7′ 订正后的版本 —— 提交版 PDF 混用了两代 judge 的结果(最重要的一条)

**第一版结论(错误)**:§5.5 的数字与附录 Table 13 系统性矛盾,§5.5 必须重写。
**方向反了。**

用 origin/main 的标注(GPT-5.5 judge)重算,§5.5 的每一个数字都**精确吻合**:

| §5.5 正文 | origin/main 数据(GPT-5.5 judge) |
|---|---|
| negative stance 5% → 61% | 4 → **61** ✅ |
| normative suggestion 5% → 50% | 4 → **50** ✅ |
| alternative offer 4% → 85% | 4 → **85** ✅ |
| executed alternative 7% → 39% | 7 → **39** ✅ |
| Opus 3: neg stance 86%, norm sugg 44% | **86 / 44** ✅ |
| Sonnet 3.7: pos alignment 1%→25%, preface 0%→12% | **25 / 12** ✅ |
| Opus 4.6: pos alignment 3%, preface 1% | **3 / 1** ✅ |
| pos alignment 下降 22pp,preface 下降 11pp | 25→3=**22pp**,12→1=**11pp** ✅ |

而附录 **Table 13 精确吻合的是旧的 GPT-5.3 judge 标注**:

| GPT-5.3 那一行 | PDF Table 13 | 旧 GPT-5.3 标注 | 新 GPT-5.5 标注 |
|---|---|---|---|
| apology | 4 | **4** ✅ | 4 |
| negative stance | 73 | **73** ✅ | 61 |
| normative suggestion | 26 | **26** ✅ | 50 |
| alternative offer | 76 | **76** ✅ | 85 |
| executed alternative | 38 | **38** ✅ | 39 |

**结论:提交版 PDF 里,正文用的是新 judge 的结果,附录结果表用的是旧 judge 的结果 ——
换 judge 之后正文更新了,附录表没有重新生成。**

**这才是 camera-ready 真正必须修的东西**:附录 F–J 的全部表(Table 11/12/13 等)
需要用当前标注重新生成。正文 §5.5 **不需要重写**。

Opus 3 的数据也确实存在(`data/annotations/responses_claude-opus-3.judged.json`,
n=200),`e5d2de2` 这个 commit 就叫 "replace claude-sonnet-4.6 with claude-opus-3" ——
模型集合已经对齐论文。**Table 10 漏列 Sonnet 4.6** 这一条仍需修。

---

## ⚠️ F8 仍然成立 —— 采集脚本会把成功的响应误记为错误

origin/main 上**这个 bug 还在**,而且有**两处**
(`scripts/02_collect_responses.py` 第 362 行和第 475 行):

```python
try:
    result = query_openrouter_model(...)
    print(f"    OK: {result['response'][:120]!r}")   # <-- 在 try 里面
except Exception as exc:
    result = {... "error": str(exc)}                 # 成功的响应被丢弃
```

Windows 控制台默认 cp1252,响应含 emoji 就抛 `UnicodeEncodeError`,被 except 捕获,
**一条成功拿到的响应被记成 error**。实测在 E2 的前 4 个模型里就命中 4 次:

```
'charmap' codec can't encode character '\U0001f4aa' in position 89
'charmap' codec can't encode character '☇' in position 9
'charmap' codec can't encode character '₂' in position 79
```

这是**静默数据丢失,且系统性偏向丢弃带 emoji 的响应** —— 对一篇研究 refusal 措辞
风格的论文,丢的恰好可能是亲和性表达最强的那些。

本地已修(stdout 转 utf-8 + 打印移出 try),**需要把这个修复提交回 origin/main**,
并且第 475 行那一处也要一并修。断点续跑只跳过非 error 记录,所以修好后重跑同一条
命令即可自动补齐。

---

## 复核清单(给下一个接手的人)

```bash
git fetch origin                      # 先做这个
git log --oneline master..origin/main | wc -l    # 本地落后多少
git ls-tree -r --name-only origin/main data/annotations/ | head
```

真正的分析流水线在 origin/main 的 **`analysis/l2_variation.Rmd`**(R,不是
`scripts/06_analyze_validation_judgments.py`),Figure 3 和 §5.4/5.5 的数字都出自那里。
重新生成附录表时要用它,不要用 Python 那条旧路径。
