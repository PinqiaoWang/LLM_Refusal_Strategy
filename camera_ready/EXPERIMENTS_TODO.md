# Camera-Ready Experiments TODO

EMNLP 2026 · Submission 16201 · 目标:兑现三份 rebuttal 中的实验承诺 + AC 必改项

每个实验块格式:**目标 / 兑现哪条承诺 / 输入 / 要写或改的代码 / 输出 / 验收标准 / 预估**。
状态标记:`[ ]` 未开始 `[~]` 进行中 `[x]` 完成

---

## ⚠️ 先读:`camera_ready/FINDINGS_provenance.md`

**2026-08-24 重大订正**:此前的诊断是对着一份**落后 origin/main 66 个 commit** 的
本地 checkout 做的,其中 4 条结论已撤回。先 `git fetch origin` 再看。

**订正后仍需处理的**
- **F7′(最重要)**:提交版 PDF **混用了两代 judge** —— 正文 §5.5 的数字来自现行的
  GPT-5.5 标注(全部精确吻合,**不用改**),而附录 Table 11/12/13 来自已归档的旧
  GPT-5.3 标注。**附录 F–J 全部表需要用当前标注重新生成。**
- **F3**:人–人一致性(Table 9 / §4.2 κ=1.000/0.953)全仓库无原始两标注者编码,
  需作者提供 —— 唯一的外部阻塞项。
- **F5**:Table 8 有 4 处 LM 列抄写错误(已定位);Table 10 漏列 Claude Sonnet 4.6。
- **F8**:`02_collect_responses.py` 静默丢数据的编码 bug(两处),origin/main 上未修。

**已拍板**:E0 → 方案 A,**262 条**(200 + 62)。
**已撤销**:"judge 改回 GPT-5.5 non-reasoning、全部重标" —— GPT-5.5 non-reasoning
已经是现状,原 200 条不必重标,**只有新增 62 条需要标注**。

⚠️ 真正的分析流水线是 origin/main 的 `analysis/l2_variation.Rmd`(R),
不是 `scripts/06_analyze_validation_judgments.py`。重新生成附录表要用前者。

---

## E0 — 查询池盘点 `[x] 已完成`

**结果已跑出**,见 `camera_ready/pool_inventory.csv`,脚本 `camera_ready/scripts/00_pool_inventory.py`。

| Category | 现有 | SB 剩余 | LMSYS 剩余 | **上限** | 能到 20? |
|---|---|---|---|---|---|
| Child Sexual Exploitation | 25 | 0 | 3392 | 3417 | ✓ |
| **Code Interpreter Abuse** | 10 | 0 | 9 | **19** | ✗ |
| Defamation | 12 | 11 | 85 | 108 | ✓ |
| **Elections** | 10 | 0 | 6 | **16** | ✗ |
| Hate | 25 | 39 | 7735 | 7799 | ✓ |
| **Indiscriminate Weapons** | 10 | 2 | 6 | **18** | ✗ |
| Intellectual Property | 11 | 3 | 11 | 25 | ✓ |
| Non-Violent Crimes | 10 | 90 | 32 | 132 | ✓ |
| **Privacy** | 10 | 0 | 0 | **10** | ✗ **完全无法扩** |
| Sex-Related Crimes | 16 | 0 | 589 | 605 | ✓ |
| Sexual Content | 25 | 12 | 7472 | 7509 | ✓ |
| Specialized Advice | 10 | 21 | 6 | 37 | ✓ |
| Suicide & Self-Harm | 15 | 3 | 195 | 213 | ✓ |
| Violent Crimes | 11 | 40 | 223 | 274 | ✓ |

### 结论与决策点(需要你先拍板,后面所有实验依赖它)

**4 个类别达不到 20**,其中 Privacy 上限就是现在的 10 —— SORRY-Bench 该类 unsafe 已全部用完,LMSYS 的 19,829 条 unsafe 里 Llama Guard 一条 Privacy 都没再判出来。放宽到"任一 assigned category"也无济于事(Privacy 在放宽后的池子里直接消失)。

rebuttal 措辞是 *"targeting at least 20 queries per category **where the available pool permits**"*,所以这不算违约,但**必须显式报告**:Table 8 加一列 "available pool",正文一句话说明 Privacy / Elections / Indiscriminate Weapons / Code Interpreter Abuse 受源数据限制。硬凑或不提是最大的翻车点。

三个选项,选一个:
- **A(推荐)**:能到 20 的到 20,4 个受限类别取满上限(Privacy 10、Elections 16、Indiscriminate Weapons 18、Code Interpreter Abuse 19),Table 8 加 pool 列 + 正文说明。最终 ≈ 20×10 + 63 = **263 条**。
- **B**:引入第三个来源(HarmBench / AdvBench / DoNotAnswer)补齐受限类别。更完整,但要新的 license 说明、重跑 Llama Guard、并且新来源的分布特性与现有两源不同,会引入新的可比性问题。**一周内不建议**。
- **C**:统一降到能普遍达到的水平(如 16/类)。均衡但浪费了大类的可用数据,且低于 rebuttal 承诺的 20。

⚠️ **注意**:上表 LMSYS 剩余数是**去重和 benign-rewrite 过滤之前**的原始计数,实际可用会更少(尤其小类)。E1 跑完过滤才是真实数字。

### 顺带发现的问题(非实验,但要修)

`00_pool_inventory.py` 末尾的自检显示**论文 Table 8 与数据文件对不上** 4 处:

| Category | 数据文件 SB/LM | 论文 Table 8 |
|---|---|---|
| Defamation | (10, 2) | (10, 3) |
| Hate | (10, 15) | (10, 14) |
| Intellectual Property | (10, 1) | (10, 0) |
| Violent Crimes | (10, 1) | (10, 2) |

行总计仍是 132/68,所以像是制表时的抄写错误。但也可能是论文用了与 `primary_llama_guard_category_name` 不同的归类规则 —— **请确认是哪种**,camera-ready 必须修。

---

## E1 — 构建扩展查询集 `[x] 已完成`

**目标** 在 E0 决策基础上产出最终扩展 query set
**兑现** AC 必改项 "include the expanded query set";6B7i W1;n561 W1
**输入** `data/prompts/*_llama_guard_coded.json`、`data/prompts/sampled_200_final_queries.json`
**代码** 扩展 `scripts/01_build_benchmark.py`,加一个 `--expand-to N --exclude-used <final200.json>` 模式,**复用现有的 `get_query_template_key` 去重、`is_benign_hate_rewrite_task` / `is_benign_politeness_rewrite_task` 过滤和 per-category cap**,保证新旧 prompt 用完全相同的管线
**输出** `data/prompts/sampled_expanded_final_queries.json`(含原 200 条,`final_sample_id` 保持不变,新增条目续号,加 `batch: "v1"|"v2"` 字段)
**验收**
- 每类计数 = min(20, pool ceiling),受限类别记录实际 ceiling
- 新条目与原 200 条 Jaccard > 0.8 去重通过
- 输出一份 `camera_ready/table8_expanded.csv`,含 SB/LM/total/pool_ceiling 四列,可直接排版成新 Table 8

**预估** 半天

---

## E2 — 全量重新采集响应(含模型漂移控制)`[~] 采集进行中(13 个模型 x 262)` ⚠️ 关键路径

**目标** 在**同一时间窗口、同一批次**内重跑全部 16 个模型 × 全部扩展 prompt
**兑现** 隐含要求:合并数据集必须内部可比
**为什么必须全量重跑**:原 200 条是 5 月前采的,现在 8 月。OpenRouter 上 `openai/gpt-5.3-chat`、`anthropic/claude-opus-4.6`、`x-ai/grok-4.20` 的服务端版本/系统提示/安全过滤很可能已经变了。若新 prompt 用 8 月数据、旧 prompt 用 5 月数据合并,**新旧子集间的差异会混入模型版本漂移** —— 而论文核心结论恰恰是模型间与跨时间的 refusal style 差异。这个污染无法事后剥离。

**输入** `data/prompts/sampled_expanded_final_queries.json`
**代码** `scripts/02_collect_responses.py`,需要加:
- `--run-id` 参数,输出到 `data/responses/openrouter/expanded_<run_id>/`
- **每条响应记录 metadata**:`collected_at` (ISO 时间戳)、OpenRouter 返回的实际 `model` 字段、`provider`、`finish_reason`、`generation_id`。目前的输出没有这些,而 App E 的 camera-ready 需要报告模型快照信息
- 断点续跑(按 `final_sample_id` 跳过已有结果),避免中途失败重来

**输出** `data/responses/openrouter/expanded_<run_id>/responses_<model>.{json,csv}` × 16
**验收**
- 16 × ~263 ≈ **4,200 次生成**全部有结果或明确的 service-level refusal 记录
- 有一份 `camera_ready/collection_manifest.csv`:model_key / openrouter_model_id / 实际返回 model / 采集起止时间 / n_ok / n_service_refusal / n_error
- **漂移对照**:在旧 200 条子集上,把 8 月结果与 `data/responses/openrouter/sampled_200/` 的 5 月结果做 Layer 0 一致率对比 → 放进附录。这本身就是一个有意思的结果(模型 refusal 行为在三个月内是否变化)

**预估** 1 天(挂机为主,注意 rate limit 与预算)

---

## E3 — 主 judge 标注 `[x] 完成:806 条新标注,judge 拒答 1 条(0.13%)`

**目标** GPT-5.5 non-reasoning 标注 E2 的全部响应
**输入** E2 输出
**代码** `scripts/05_run_full_validation_judge.py`(已有,输入需 `query` / `response` 字段);判定提示词固定用 `data/judge_prompt_current.txt`,**不要在这轮改 prompt**
**输出** `data/annotations/expanded_<run_id>/responses_<model>.judged.{json,csv}`
**验收**
- 记录 judge 的 model string + 调用日期 + prompt 文件 SHA256(论文 App D 已有 SHA256 前缀 `238bb923037b...`,确认是否仍一致;若 prompt 改过必须更新)
- judge 拒答率 < 1%(论文原为 0.5%),记录具体条数
- 先在 20 条上 smoke test 再全量

**预估** 半天

---

## E4 — 跨家族 judge 稳健性检验 `[~] gold-100 验证已完成;全量重标待 E3`

**目标** 用非 OpenAI 家族的 judge 复核,回应"judge 可能与被评模型共享对齐偏好"
**兑现** 6B7i W2(rebuttal 明确承诺 "cross-family robustness check using an Anthropic model under the same codebook and protocol")
**做法** 两步:
1. **gold set 验证**:Claude Opus 4.6(non-reasoning)在 `data/gold_100.json` 上跑,复用 `scripts/04_compare_judge_models_on_gold.py`,报 Layer 0/1/2 的 accuracy + κ,与 GPT-5.5 并列
2. **全量重标**:同一 judge 标注 E2 全部响应,报 judge–judge 一致率,并**逐条核对论文的 headline 结论在第二 judge 下是否复现**

**输出** `camera_ready/judge_crossfamily_gold100.csv`、`camera_ready/judge_agreement_matrix.csv`、`data/annotations/expanded_<run_id>_claudejudge/`
**验收**
- 第二 judge 对 gold 的 κ 与 GPT-5.5 同量级
- 有一张"headline 结论 × 两个 judge"的复现对照表
- **如果有结论不复现,如实报告** —— 这比藏起来强得多,也正是 reviewer 想看的诚实性

**预估** 半天~1 天

---

## E5 — 补齐 judge 模型比较表 `[x] 已完成` 🎁 几乎免费

**目标** 论文 App D.1 说比较过 GPT-4o / GPT-5.3(std+reas)/ GPT-5.5(std+reas)/ o4-mini / ensemble,但"full comparative results were not reported";rebuttal 承诺补上
**好消息**:这些结果**仓库里已经有了**,不用重跑:
```
data/judge_gpt4o_standard.json
data/judge_gpt55_standard.json
data/judge_gpt55_reasoning.json
data/judge_o4mini_reasoning.json
data/judge_ensemble_v2.json
data/judge_compare_gpt53_currentprompt_gold100.json
data/judge_compare_gpt55_currentprompt_gold100.json
```
**代码** 跑 `scripts/04_compare_judge_models_on_gold.py` 汇总成一张表即可
**输出** `camera_ready/appendixD_judge_comparison.csv` → 新 Table(App D)
**验收** 每个候选 judge 一行,列 = Layer 0 acc/κ、Layer 1 acc/κ、Layer 2 平均 κ、成本或延迟代理指标;并有一句话解释为何选 GPT-5.5 non-reasoning
⚠️ 注意 prompt 版本:仓库里有 `judge_calibrated_prompt_v3.txt` / `v5.txt` / `judge_prompt_current.txt`,**确认这些比较结果是否都在同一 prompt 版本下产生**,否则比较不公平,需注明

**预估** 1–2 小时

---

## E6 — Bootstrap 置信区间与显著性检验 `[x] 脚本完成并已在旧数据上验证`

**目标** 给所有报告的比例配 CI,给所有强调的对比配检验
**兑现** 6B7i W1 / n561 W1 的"统计稳定性"
**做法**
- **以 prompt 为重抽样单元**做 cluster bootstrap(10,000 次),因为同一 prompt 在 16 个模型间不独立
- 覆盖:Layer 0 各类率、Layer 1 四类分布、Layer 2 全部 13 个 feature,× 每个模型 × 每个 harm cluster
- 成对对比(GPT-4o→GPT-5.3 的 negative stance 等)做两比例检验 + Holm 校正
**代码** 新建 `camera_ready/scripts/06_bootstrap_ci.py`
**输出** `camera_ready/bootstrap_ci.csv`、`camera_ready/pairwise_tests.csv`;Figure 2 加误差条或在附录给 CI 表
**验收** 论文正文强调的每个数字都能在 csv 里查到对应 CI

**预估** 半天

---

## E7 — 每个 model×category cell 的 NC 底数 `[x] 脚本完成并已在旧数据上验证`

**目标** rebuttal 承诺:"report the number of non-compliant responses underlying each model-by-category estimate",并标注小样本 cell 为 exploratory
**代码** 扩展 `scripts/06_analyze_validation_judgments.py`
**输出** Table 14 增加底数(如 `72% (n=18)`);低于阈值(建议 n<10)的 cell 加标记
**验收** Table 8 与 Table 14 有交叉引用;正文说明小 cell 为探索性
**预估** 2 小时

---

## E8 — 全部图表与正文数字重生成 `[~] 数字部分完成;图表待装 R`  ⚠️ 最容易出错

**目标** 用扩展数据重算一切
**做法**
- 把 `scripts/06_analyze_validation_judgments.py` 和 `src/analysis.py` 参数化到能一条命令重生成 Figure 1/2/3/4 与附录 F–J 全部表
- **建一份 `camera_ready/number_checklist.md`**:把正文里所有硬编码数字逐个列出(90%/10%、70%、23%、6%、1%、21%/17%/4%、8%↔38%、95%/92%/47%、92%/68%/77%、43%、23% vs 8%、5%→61%、5%→50%、4%→85%、7%→39%、14%→61%、2.4pp、8.7pp、2.0pp、18%→9%、75%→83%、48%→61%、86%、44%、1%→25%、0%→12%、3%→1%、22pp、11pp、9.5%/9.5%/3.0% ……),每个标注来源 csv 与新值
- **不要手改正文数字** —— 一周内手改必错

**验收** checklist 全部打勾;PDF 里搜不到任何未更新的旧数字
**预估** 1 天

---

## E9 — 数据与代码发布 `[ ]`

**目标** 6B7i 和 Ggm3 都给了 Datasets=1 / Software=1;三份 rebuttal 都承诺发布
**做法**
- camera-ready 里必须有**可点击 URL**,不能只写 "will be released"
- 内容:全部判定标注(建议把 19 个模型的都放)、codebook、judge prompt 全文、采样/采集/判定/分析脚本、`collection_manifest.csv`
- ⚠️ **LMSYS-Chat-1M 再分发条款** —— 若不允许直接放 prompt 原文,就放 **conversation ID + 复现脚本**;SORRY-Bench 是 MIT,可以直接放
- 清理:`configs/models.yaml` 现在还是早期方案(gpt-4o / claude-3-haiku / gemma-2-9b,与实际 16 模型完全不符),README 里 "Target venue: EMNLP 2025" 和目录结构也过时了,发布前要更新
- `.gitignore` 检查有没有 API key 泄漏;`__pycache__` 清掉

**验收** 从零 clone + 按 README 能跑通至少 judge 与 analysis 两段
**预估** 半天

---

## 执行顺序与依赖

```
E0 [x] ──> 决策(A/B/C) ──> E1 ──> E2 ──> E3 ──┬──> E6 ──┐
                                               ├──> E7 ──┼──> E8 ──> 定稿
                                    E4 ────────┘         │
                            E5(独立,随时可做)──────────┘
                            E9(独立,最后打包)
```

关键路径是 **E1 → E2 → E3 → E8**。E2 是唯一的长时挂机任务,**尽早启动**。
E5 几乎免费,建议第一天就顺手做掉,先给自己一个 checkpoint。

## 建议排期(约一周)

| 天 | 数据线 | 备注 |
|---|---|---|
| D1 | 拍板 E0 决策 → E1 建集;顺手做 E5 | 同时把 Table 8 的 4 处不一致查清 |
| D2 | **启动 E2 全量采集**(挂机) | 期间做 E6 脚本、E7 |
| D3 | E2 收尾 → E3 主 judge 全量 | |
| D4 | E4 跨家族 judge | |
| D5 | E6 / E7 出数 → E8 重生成全部图表 | |
| D6 | E8 数字核对 + E9 打包 | |
| D7 | 缓冲 | |

## 非实验的待办

写作侧的清单(Ggm3 三条理论修改、§5.5 删重复、命名统一、Table 2/Table 9 数值重复的硬伤等)在会话外的两份文档里:`camera_ready_checklist.md` 与 `camera_ready_drafts.md`。

**特别提醒**:论文 Table 2(judge-vs-gold)与 Table 9(标称 human IAA before adjudication)数值完全相同,且 Table 9 与 §4.2 正文的 κ=1.000 / 0.953 直接矛盾。这是目前论文里最可能被读者抓到的硬伤,**优先级等同实验**。原始的人–人标注结果在 `data/gold_100.xlsx` / `data/Gold Rule.xlsx` 里,请重新算一遍真实的 inter-annotator κ。
