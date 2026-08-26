# Camera-Ready 清单(EMNLP 2026,约一周)

## 0. 核心判断

进 main conference 靠的是 AC 那句 **"provided the authors make the changes promised in their rebuttal"** —— 你们在三份回复里的承诺现在是**具有约束力的**,commitment reader 会逐条核对。所以 camera-ready 不是"改改文字",而是**兑现承诺清单**。

三份 rebuttal 中的承诺共 **18 条**,加上 AC 单独列的 5 条必改项(全部已包含在 18 条内)。下面按优先级排。

**版面**:ACL/EMNLP 长文 camera-ready 通常给到 9 页正文(比投稿多 1 页),附录不限。⚠️ 请到会议官网确认 2026 年具体规定。你们要塞进去的东西(stance 文献、face 四维分析、Layer 2 理论列、扩样说明)远超 1 页,**必须靠删 §5.5 重复文字和把数字搬进附录来腾**。这是本次最大的写作约束。

---

## P0 — 不做会被判未兑现承诺

### 1. 扩展 query set 到 ≥20/类 + 重跑 16 模型 【工作量最大,先启动】
AC 明确列为必改项("include the expanded query set"),两份 rebuttal 都写了。

**现状(Table 8)**:已 ≥20 的只有 3 类 —— CSE 25、Hate 24、Sexual Content 25。需要补的 11 类:

| 类别 | 现有 | 需补 | SORRY-Bench 剩余可用性 |
|---|---|---|---|
| Code Interpreter Abuse | 10 (SB 8 + LM 2) | +10 | SB 该类只有 8 条 unsafe,**全靠 LMSYS** |
| Privacy | 10 (SB 8 + LM 2) | +10 | 同上,SB 已耗尽 |
| Elections | 10 (SB 10 + LM 0) | +10 | LMSYS 中该类极稀少,**很可能凑不到 20** |
| Indiscriminate Weapons | 10 | +10 | LMSYS 稀少,可能凑不到 |
| Intellectual Property | 10 | +10 | 需查 SB 剩余池 |
| Non-Violent Crimes | 10 | +10 | 池子应该充足 |
| Specialized Advice | 10 | +10 | 需查 |
| Defamation | 13 | +7 | 需查 |
| Violent Crimes | 12 | +8 | 池子应该充足 |
| Suicide & Self-Harm | 15 | +5 | 池子应该充足 |
| Sex-Related Crimes | 16 | +4 | 池子应该充足 |

**做法**:
- 先跑一遍**池子盘点**(SB 剩余 221 条 unsafe base prompts 按 Llama Guard 类别的分布 + LMSYS 19,829 条的类别分布),再定最终每类目标数。**半天就能出结果,先做这个再决定规模**。
- 凑不到 20 的类别**如实报告池子上限**,在 Table 8 加一列"available pool size"。你们 rebuttal 的措辞是 "where the available pool permits",已经留了余地,但必须显式说明是哪几类、为什么。硬凑或含糊带过是最大的翻车点。
- 预估新增 ~100–120 条 prompt × 16 模型 ≈ 1,600–1,900 次生成 + 同量 judge 调用。OpenRouter 成本很低,一天内可完成。

### ⚠️ 1b. 模型版本漂移 —— 这条最容易被忽略,但会直接毁掉数据可比性
原始 200 条是 2026 年 5 月前采集的。现在是 8 月,OpenRouter 上 GPT-5.3 / Opus 4.6 / Grok 4.20 的服务端权重、system prompt、safety filter **很可能已更新**。如果新 prompts 在 8 月采集、旧的用 5 月数据,合并成一个 400 条的数据集,**新旧子集之间的差异会混入模型版本差异**,而你们的核心结论恰恰是关于模型间/时间上的 refusal style 差异 —— 这个污染是致命的。

**建议(按稳妥度排序)**:
1. **全部重跑**(旧 200 + 新 ~120,同一批次、同一时间窗口)。约 5,000 次生成 + 5,000 次 judge,成本仍可控,一到两天。这是唯一干净的方案,**强烈推荐**。
2. 若时间不够:至少在旧 200 条中抽 50 条复跑,报告与 5 月结果的一致率,作为漂移检查放进附录。
3. 无论选哪种,在 App E 记录**每个模型的 OpenRouter model string + 采集日期**,camera-ready 必须有这个。judge 模型(GPT-5.5)同理 —— App D 已有 SHA256 prefix,继续保持并加上重跑日期。

**下游影响**:全文所有数字、Figure 1/2/3/4、Table 8/14 及附录 F–J 全部要重算。**务必把分析脚本参数化、一键重生成所有图表**,不要手改正文数字 —— 一周内手改必出错。正文里硬编码的数字有几十处(90%/10%、70%、23%、6%、1%、43%、23% vs 8%、5%→61%、5%→50%、4%→85%、7%→39%、14%→61%、2.4pp、8.7pp、2.0pp、18%→9%、75%→83%、48%→61%、86%、44%、1%→25%、0%→12%、3%、22pp、11pp……),建议做一个 checklist 逐个对照。

### 2. Ggm3 的三条理论修改 【决定论文最终质量,也是 excitement=5 的来源】
这是 AC 转述的"理论 grounding 松散"批评,也是你们给 Ggm3 承诺最详细的部分。三件事:

- **§2.2 扩写**:引入 speaker face / hearer face × positive face / negative face 四维,并**首次正式引入 stance 文献**(Du Bois 2007 stance triangle 的 evaluation/positioning/alignment 三元;Biber & Finegan 1989;Kiesling 2009 关于 interactional stancetaking)。把 positive alignment / solidarity-empathy / negative stance 明确定位为 stance-taking 而非 politeness 策略。⚠️ 具体引哪几篇请你们自行核定,我不确定你们领域的标准引用。
- **Layer 2 重组**:Table 1 加一列 "theoretical characterization",区分 form-based devices(hedge、explanatory preface、role-based self-positioning)与 functional features,后者再按 illocutionary act type(commissive / expressive / assertive / directive)、stance、face-threat direction 归类。**建议做成一张新表(Table 2)放正文**,原 Table 1 保留操作性定义。
- **§6 改写**:采用 Ggm3 的 "face redistribution / pragmatic overcorrection" 论述 —— 前沿模型不是减少了 face threat,而是把它从 speaker face 转移到 hearer face。这是全文最强的一句 takeaway,应该进 abstract。**建议同时改 abstract**(见 drafts 文件)。

### 3. 删 §5.5(L489–537)重复段落
Ggm3 和 AC 都点名。这段两个自然段大量重复数字。**把逐模型数字全部搬到附录表,正文只留趋势描述** —— 这一刀能腾出约半页,正好资助 §2.2 和 §6 的扩写。

### 4. 释放数据与代码 【零成本,但 6B7i 和 Ggm3 都给了 Datasets=1 / Software=1】
三份 rebuttal 都承诺了。camera-ready 必须有一个**可点击的 URL**(GitHub + 数据托管),不能只写 "will be released"。内容:全部判定标注(建议连 19 模型的都放)、codebook、judge prompt 全文、采样/判定/可视化/分析脚本。注意 LMSYS-Chat-1M 的再分发条款 —— 若不允许直接放 prompt 原文,就放**索引 ID + 复现脚本**。

### 5. 模型命名统一(Qwen3-8B / Qwen3-32B 连字符格式,全文)
n561 提的,一分钟的事,别忘。

---

## P1 — rebuttal 中承诺过,工作量小但必须做

6. **跨家族 judge robustness check**(承诺给 6B7i)。用 Anthropic 模型 + 同一 codebook,先在 100 条 gold set 上报 κ,再全量重标,报 judge–judge 一致率与结论复现情况。放附录 D。
7. **补齐 App D 的 judge 比较完整结果表** —— 你们承认"full comparative results were not reported",现在必须给出 GPT-4o / GPT-5.3(std+reas)/ GPT-5.5(std+reas)/ o4-mini / ensemble 在 gold set 上的完整对比,并说明为何 GPT-5.5 non-reasoning 在性能与成本间最优。
8. **交叉引用 Table 8 与 Table 14,并报告每个 model×category cell 的 NC 底数**,明确标注小样本 cell 为 exploratory。
9. **"human refusals" 措辞全文收紧** —— 改为明确指向文献(Beebe et al. 1990;Campillo et al. 2009;Johnson et al. 2004),避免读成实测对照。Abstract、§5.3 开头、§6 都有这类表述。
10. **§4.1 正文加入 SORRY-Bench / LMSYS 互补理由**(受控覆盖 vs 自然分布),不要只留在 App K。
11. **Table 1 脚注修**:指向 Table 6/7 与 Appendix A;声明 "action-negating marker" 是**操作性编码术语**而非提出的语用学构念;explicit/implicit 用 commissive vs. assertive/expressive 重述。
12. **Scope boundary 声明** —— 明确本文提供描述性测量框架,不主张判定 appropriateness;规范性判据需 user study。放 §1 贡献列表后或 §3 开头一句,同时更新 Limitations。

---

## P2 — 提交前必须自查的既有错误

13. ⚠️ **Table 2 与 Table 9 数值完全相同**(95.0/.857、93.5/.860、negative stance 90.9/.791、executed alternative 83.1/.605……)。Table 2 是 judge-vs-gold,Table 9 标题却是"human inter-annotator agreement, before adjudication"。几乎肯定是排版时误复制。**必修**。
14. ⚠️ **与 13 相关**:§4.2 正文写人–人一致性 Layer 0/1 κ=1.000、Layer 2 平均 κ=0.953,与 Table 9 的数字直接矛盾。需要确认哪个是真实的人–人一致性,并统一。**这两条是目前论文里最可能被 commitment reader 或读者抓到的硬伤**,优先级实际上等同 P0。
15. Table 8 caption 写 "LM = LMSYS/WildChat",但全文(§4.1、Ethics、App K)只提 LMSYS-Chat-1M,WildChat 从未出现也未引用。若确实用了 WildChat,需补引用与 license 说明;若没用,删掉。
16. 数量口径统一:正文 3,200 pairs(16 模型)vs App D 的 3,800 pairs(19 模型)。不是错误,但要在 App E 说清楚,避免读者困惑。
17. **Limitations 更新** —— 扩样后,"200 prompts 太小"这条要重写为新的样本量与残余局限;把 judge 跨家族检查后的残余风险、appropriateness 判据缺失、无 user perception 数据保留。
18. **Ethics / licensing 更新** —— 新增 prompts 的来源与许可,以及数据释放的 content warning。

---

## 一周时间表(建议两条线并行)

| 天 | 数据线(建议 1 人) | 写作线(建议 1–2 人) |
|---|---|---|
| D1 | 池子盘点(SB 剩余 + LMSYS 按类分布),定最终每类目标数;把分析脚本参数化 | 修 P2 的 13/14/15/16(先把硬伤清掉);删 §5.5 重复段 |
| D2 | 采样新 prompts;启动**全部 400 条 × 16 模型全量重跑** | 写 §2.2 stance + face 扩写;起草新 Table 2(理论刻画) |
| D3 | 生成完成 → judge 标注全量;并行跑 Anthropic 跨家族 judge 的 gold-set 验证 | 写 §6 face-redistribution;改 abstract |
| D4 | 跨家族 judge 全量;补 App D judge 比较表;所有图表重生成 | 改 §5.3/§5.4 使其接回 face 理论;写 scope boundary 与 Limitations |
| D5 | Table 8 加 pool size 列;Table 14 加 NC 底数;附录 F–J 重算 | **全文数字逐个对照新结果**(用 checklist);措辞收紧("human refusals"、命名统一) |
| D6 | 整理 GitHub 仓库 + 数据托管,拿到可引用 URL,写 README | 全文通读 + 版面压到页数上限;检查所有 rebuttal 承诺是否逐条落地 |
| D7 | 缓冲 / 提交 | 缓冲 / 提交 |

---

## 提交前最后一步:承诺核对表

打开三份 rebuttal,逐句划出"we will ..." 的句子,对照 camera-ready 打勾。建议在附录开头或 README 里加一小段 **"Changes from the submitted version"**(即使会议不强制)—— commitment reader 会很领情,也能防止自己漏项。
