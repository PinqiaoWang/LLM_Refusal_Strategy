# 扩样对论文数字的影响(200 -> 262)

同样的模型、同样的 judge,唯一变化是新增的 62 条 prompt。

- 比较了 260 个 model×statistic 比率
- 中位数 |Δ| = **0.97pp**,平均 1.26pp
- |Δ| ≥ 5pp 的有 1 个(0%),≥10pp 的有0 个,最大 5.9pp

## §5.5 的趋势claim在扩样后是否成立

| 特征 | 轨迹 | 200 条 | 262 条 | 方向 |
|---|---|---|---|---|
| negative_stance | GPT-4o → GPT-5 | 4%→55% | 4%→58% | ✅ 一致 |
| normative_suggestion | GPT-4o → GPT-5 | 4%→40% | 3%→44% | ✅ 一致 |
| alternative_offer | GPT-4o → GPT-5 | 4%→52% | 5%→55% | ✅ 一致 |
| executed_alternative | GPT-4o → GPT-5 | 7%→66% | 9%→67% | ✅ 一致 |
| apology | GPT-4o → GPT-5 | 94%→40% | 92%→40% | ✅ 一致 |
| positive_alignment | Claude Sonnet 4.6 → Claude Opus 4.6 | 5%→3% | 6%→6% | ⚠️ 趋势变平(未反转) |
| explanatory_preface | Claude Sonnet 4.6 → Claude Opus 4.6 | 7%→1% | 6%→1% | ✅ 一致 |
| apology | Claude Sonnet 4.6 → Claude Opus 4.6 | 0%→1% | 0%→1% | ⚠️ 趋势变平(未反转) |
| negative_stance | Claude Sonnet 4.6 → Claude Opus 4.6 | 78%→82% | 77%→80% | ✅ 一致 |

**7 条方向不变,2 条需要复核(反转或变平)。**
> 方向判定用 ±1pp 的死区:小于 1pp 的变化算"持平",不算上升或下降。

## 变化最大的 10 个

| 模型 | 统计量 | 200 | 262 | Δ |
|---|---|---|---|---|
| Gemini 2.5 Pro | Ethics-based | 75% | 69% | -5.9pp |
| Grok 4.20 | normative_suggestion | 38% | 42% | +4.6pp |
| Qwen3-8B + reasoning | solidarity | 16% | 20% | +4.2pp |
| GPT-5 | solidarity | 14% | 18% | +3.8pp |
| GPT-5 | normative_suggestion | 40% | 44% | +3.8pp |
| Qwen3-32B + reasoning | statement_of_principle | 25% | 21% | -3.7pp |
| GPT-5 | alternative_offer | 52% | 55% | +3.7pp |
| Claude Opus 4.6 | normative_suggestion | 29% | 32% | +3.5pp |
| Qwen3-8B | solidarity | 15% | 19% | +3.4pp |
| Gemini 2.5 Pro | Capacity-based | 0% | 3% | +3.3pp |

---

## §5.5 的三个派生量(平均 Layer 2 特征差异)

这三个是正文里仅有的、无法按数值直接匹配到分析 CSV 的数字。手工重算后:

| 论文表述 | 论文值 | 200 条重算 | 262 条 |
|---|---|---|---|
| Llama 8B vs 70B 平均 L2 特征差异 | 2.4pp | **2.4** ✅ | 2.1 |
| Qwen3 8B vs 32B 平均 L2 特征差异 | 8.7pp | **8.7** ✅ | 8.4 |
| 4 个 standard/reasoning 对的平均 L2 差异 | 2.0pp | **2.0** ✅ | 1.9 |

三个都在原 200 条上**精确复现**,扩样后变化不到 0.3pp。定义 = 13 个 Layer 2 特征
上两模型比率之差的绝对值的平均。

**至此正文数字核对表全部闭合**:321 个百分比全部能在重算数据里找到来源,
3 个 pp 派生量已手工验证。

---

## 结论:扩样可以放心做,正文改动很小

- 260 个 model×statistic 比率,中位数变化 **0.97pp**,最大 5.9pp,无一超过 10pp
- §5.5 的趋势 claim:7 条方向不变,2 条变平(均为 ≤5% 的小效应),**0 条反转**
- 三个派生量变化 < 0.3pp

也就是说:**兑现"扩样到 262 条"这个承诺,不需要重写任何论点,只需要更新数值。**
真正需要重新生成的是附录表(见 `appendix_diff_vs_submitted.md`),那是换 judge
造成的,与扩样无关。
