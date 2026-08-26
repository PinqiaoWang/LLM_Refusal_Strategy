# 附录表 11–13:重新生成 vs 提交版

标注来源:`data/annotations`(现行 GPT-5.5 non-reasoning judge)

提交版 PDF 的这三张表是用**已归档的旧 GPT-5.3 judge** 算的,换 judge 之后
没有重新生成。下面是逐格差异。

## 模型集合变更

提交版三张表都含 **Sonnet 4.6**、无 **Claude 3 Opus**;
但 Table 10 和正文 §5.5 用的是 **Claude 3 Opus**。
commit `e5d2de2` = "replace claude-sonnet-4.6 with claude-opus-3"。

→ camera-ready 的三张表应改用 Claude 3 Opus。两者的数值都已在 CSV 里给出,
  由你们决定最终保留哪些行。

## Table 11(Layer 0):16/16 行有变化

| 模型 | 提交版 FC/PC/NC/NC% | 重算 FC/PC/NC/NC% |
|---|---|---|
| GPT-4o | 35/8/157/78.5 | **36/7/157/78.5** |
| GPT-5 | 15/6/177/88.5 | **14/8/176/88.9** |
| GPT-5.3 | 14/14/172/86.0 | **15/9/175/87.9** |
| GPT-5.3-R | 15/8/177/88.5 | **14/7/177/89.4** |
| Sonnet 3.7 | 22/8/170/85.0 | **20/9/169/85.4** |
| Sonnet 4.6 | 27/7/158/79.0 | **29/5/159/82.4** |
| Opus 4.6 | 19/2/167/83.5 | **20/3/171/88.1** |
| Opus 4.6-R | 20/3/165/82.5 | **21/3/170/87.6** |
| Gemini 2.5 Pro | 63/5/113/56.5 | **62/7/110/61.5** |
| Grok 4.20 | 38/3/140/70.0 | **37/3/141/77.9** |
| Llama-8B | 15/2/183/91.5 | **13/3/183/92.0** |
| Llama-70B | 43/4/153/76.5 | **40/5/154/77.4** |
| Qwen3-8B | 56/9/132/66.0 | **49/14/136/68.3** |
| Qwen3-8B-R | 52/16/132/66.0 | **47/17/134/67.7** |
| Qwen3-32B | 64/8/126/63.0 | **62/9/126/64.0** |
| Qwen3-32B-R | 63/13/123/61.5 | **65/11/123/61.8** |

## Table 12(Layer 1):16/16 行有变化

| 模型 | 提交版 Bare/Cap/Pol/Eth | 重算 Bare/Cap/Pol/Eth |
|---|---|---|
| GPT-4o | 134/0/2/21 | **145/0/0/12** |
| GPT-5 | 29/0/14/134 | **40/1/6/129** |
| GPT-5.3 | 6/0/21/145 | **16/1/6/152** |
| GPT-5.3-R | 14/0/21/142 | **26/1/8/142** |
| Sonnet 3.7 | 2/4/15/149 | **2/7/10/150** |
| Sonnet 4.6 | 6/0/7/145 | **12/1/4/142** |
| Opus 4.6 | 5/2/10/150 | **7/1/6/157** |
| Opus 4.6-R | 3/1/14/147 | **3/3/9/155** |
| Gemini 2.5 Pro | 0/0/17/96 | **5/0/23/82** |
| Grok 4.20 | 9/0/22/109 | **14/0/19/108** |
| Llama-8B | 129/1/8/45 | **140/0/5/38** |
| Llama-70B | 90/3/29/31 | **105/2/19/28** |
| Qwen3-8B | 3/0/13/116 | **9/1/8/118** |
| Qwen3-8B-R | 5/0/10/117 | **9/0/8/117** |
| Qwen3-32B | 19/0/9/98 | **23/1/7/95** |
| Qwen3-32B-R | 5/0/11/107 | **11/0/10/102** |

## Table 13(Layer 2):16/16 行、共 147 格有变化

| 模型 | 特征 | 提交版 | 重算 |
|---|---|---|---|
| GPT-4o | positive_alignment | 1 | **0** |
| GPT-4o | solidarity | 5 | **7** |
| GPT-4o | executed_alternative | 9 | **7** |
| GPT-4o | normative_suggestion | 3 | **4** |
| GPT-4o | statement_of_principle | 0 | **1** |
| GPT-5 | explicit_nc | 97 | **98** |
| GPT-5 | implicit_nc | 3 | **2** |
| GPT-5 | explanatory_preface | 2 | **0** |
| GPT-5 | solidarity | 8 | **14** |
| GPT-5 | negative_stance | 65 | **55** |
| GPT-5 | executed_alternative | 67 | **66** |
| GPT-5 | alternative_offer | 38 | **52** |
| GPT-5 | normative_suggestion | 23 | **40** |
| GPT-5 | role_based | 0 | **1** |
| GPT-5.3 | explanatory_preface | 1 | **0** |
| GPT-5.3 | positive_alignment | 1 | **2** |
| GPT-5.3 | solidarity | 3 | **7** |
| GPT-5.3 | negative_stance | 73 | **61** |
| GPT-5.3 | executed_alternative | 38 | **39** |
| GPT-5.3 | alternative_offer | 76 | **85** |
| GPT-5.3 | normative_suggestion | 26 | **50** |
| GPT-5.3 | statement_of_principle | 0 | **1** |
| GPT-5.3-R | explicit_nc | 98 | **99** |
| GPT-5.3-R | implicit_nc | 2 | **1** |
| GPT-5.3-R | positive_alignment | 2 | **1** |
| GPT-5.3-R | solidarity | 5 | **8** |
| GPT-5.3-R | negative_stance | 69 | **59** |
| GPT-5.3-R | alternative_offer | 73 | **85** |
| GPT-5.3-R | normative_suggestion | 26 | **46** |
| GPT-5.3-R | statement_of_principle | 0 | **1** |
| Sonnet 3.7 | explicit_nc | 81 | **80** |
| Sonnet 3.7 | implicit_nc | 19 | **20** |
| Sonnet 3.7 | hedge | 1 | **0** |
| Sonnet 3.7 | explanatory_preface | 20 | **12** |
| Sonnet 3.7 | positive_alignment | 28 | **25** |
| Sonnet 3.7 | solidarity | 5 | **15** |
| Sonnet 3.7 | executed_alternative | 38 | **42** |
| Sonnet 3.7 | alternative_offer | 71 | **76** |
| Sonnet 3.7 | normative_suggestion | 29 | **54** |
| Sonnet 3.7 | statement_of_principle | 6 | **4** |
| Sonnet 3.7 | role_based | 2 | **8** |
| Sonnet 4.6 | explicit_nc | 95 | **96** |
| Sonnet 4.6 | implicit_nc | 5 | **4** |
| Sonnet 4.6 | explanatory_preface | 11 | **7** |
| Sonnet 4.6 | positive_alignment | 7 | **5** |
| Sonnet 4.6 | solidarity | 4 | **14** |
| Sonnet 4.6 | negative_stance | 88 | **78** |
| Sonnet 4.6 | executed_alternative | 32 | **35** |
| Sonnet 4.6 | alternative_offer | 54 | **56** |
| Sonnet 4.6 | normative_suggestion | 15 | **25** |
| Sonnet 4.6 | role_based | 0 | **1** |
| Opus 4.6 | solidarity | 7 | **21** |
| Opus 4.6 | negative_stance | 87 | **82** |
| Opus 4.6 | executed_alternative | 37 | **44** |
| Opus 4.6 | alternative_offer | 62 | **71** |
| Opus 4.6 | normative_suggestion | 16 | **29** |
| Opus 4.6 | statement_of_principle | 3 | **1** |
| Opus 4.6 | role_based | 0 | **1** |
| Opus 4.6-R | explicit_nc | 99 | **100** |
| Opus 4.6-R | implicit_nc | 1 | **0** |
| Opus 4.6-R | solidarity | 8 | **25** |
| Opus 4.6-R | negative_stance | 88 | **84** |
| Opus 4.6-R | executed_alternative | 41 | **45** |
| Opus 4.6-R | alternative_offer | 59 | **69** |
| Opus 4.6-R | normative_suggestion | 19 | **34** |
| Opus 4.6-R | statement_of_principle | 2 | **1** |
| Opus 4.6-R | role_based | 0 | **1** |
| Gemini 2.5 Pro | explicit_nc | 96 | **95** |
| Gemini 2.5 Pro | implicit_nc | 4 | **5** |
| Gemini 2.5 Pro | explanatory_preface | 12 | **13** |
| Gemini 2.5 Pro | positive_alignment | 9 | **8** |
| Gemini 2.5 Pro | solidarity | 22 | **35** |
| Gemini 2.5 Pro | negative_stance | 90 | **91** |
| Gemini 2.5 Pro | executed_alternative | 72 | **67** |
| Gemini 2.5 Pro | alternative_offer | 10 | **13** |
| Gemini 2.5 Pro | normative_suggestion | 35 | **44** |
| Gemini 2.5 Pro | statement_of_principle | 20 | **12** |
| Gemini 2.5 Pro | role_based | 19 | **68** |
| Grok 4.20 | explicit_nc | 95 | **94** |
| Grok 4.20 | implicit_nc | 5 | **6** |
| Grok 4.20 | solidarity | 5 | **11** |
| Grok 4.20 | negative_stance | 81 | **78** |
| Grok 4.20 | executed_alternative | 28 | **33** |
| Grok 4.20 | alternative_offer | 51 | **56** |
| Grok 4.20 | normative_suggestion | 23 | **38** |
| Grok 4.20 | statement_of_principle | 3 | **1** |
| Grok 4.20 | role_based | 4 | **3** |
| Llama-8B | explicit_nc | 99 | **98** |
| Llama-8B | implicit_nc | 1 | **2** |
| Llama-8B | solidarity | 4 | **5** |
| Llama-8B | negative_stance | 16 | **11** |
| Llama-8B | executed_alternative | 6 | **7** |
| Llama-8B | alternative_offer | 34 | **33** |
| Llama-70B | explicit_nc | 94 | **93** |
| Llama-70B | implicit_nc | 6 | **7** |
| Llama-70B | positive_alignment | 7 | **5** |
| Llama-70B | solidarity | 2 | **4** |
| Llama-70B | negative_stance | 13 | **10** |
| Llama-70B | executed_alternative | 7 | **5** |
| Llama-70B | alternative_offer | 37 | **40** |
| Qwen3-8B | explicit_nc | 72 | **69** |
| Qwen3-8B | implicit_nc | 28 | **31** |
| Qwen3-8B | apology | 15 | **14** |
| Qwen3-8B | explanatory_preface | 5 | **7** |
| Qwen3-8B | positive_alignment | 2 | **1** |
| Qwen3-8B | solidarity | 8 | **15** |
| Qwen3-8B | negative_stance | 88 | **84** |
| Qwen3-8B | executed_alternative | 57 | **59** |
| Qwen3-8B | alternative_offer | 43 | **57** |
| Qwen3-8B | normative_suggestion | 39 | **57** |
| Qwen3-8B | statement_of_principle | 5 | **17** |
| Qwen3-8B | role_based | 7 | **10** |
| Qwen3-8B-R | explicit_nc | 67 | **66** |
| Qwen3-8B-R | implicit_nc | 33 | **34** |
| Qwen3-8B-R | apology | 18 | **17** |
| Qwen3-8B-R | explanatory_preface | 2 | **6** |
| Qwen3-8B-R | positive_alignment | 2 | **1** |
| Qwen3-8B-R | solidarity | 9 | **16** |
| Qwen3-8B-R | negative_stance | 86 | **84** |
| Qwen3-8B-R | executed_alternative | 54 | **57** |
| Qwen3-8B-R | alternative_offer | 47 | **51** |
| Qwen3-8B-R | normative_suggestion | 45 | **60** |
| Qwen3-8B-R | statement_of_principle | 8 | **18** |
| Qwen3-8B-R | role_based | 7 | **10** |
| Qwen3-32B | explicit_nc | 79 | **78** |
| Qwen3-32B | implicit_nc | 21 | **22** |
| Qwen3-32B | apology | 63 | **61** |
| Qwen3-32B | explanatory_preface | 3 | **5** |
| Qwen3-32B | positive_alignment | 2 | **1** |
| Qwen3-32B | solidarity | 6 | **20** |
| Qwen3-32B | negative_stance | 73 | **72** |
| Qwen3-32B | executed_alternative | 48 | **45** |
| Qwen3-32B | alternative_offer | 43 | **52** |
| Qwen3-32B | normative_suggestion | 32 | **48** |
| Qwen3-32B | statement_of_principle | 10 | **19** |
| Qwen3-32B | role_based | 6 | **10** |
| Qwen3-32B-R | explicit_nc | 75 | **74** |
| Qwen3-32B-R | implicit_nc | 25 | **26** |
| Qwen3-32B-R | apology | 63 | **62** |
| Qwen3-32B-R | positive_alignment | 2 | **0** |
| Qwen3-32B-R | solidarity | 7 | **19** |
| Qwen3-32B-R | negative_stance | 84 | **81** |
| Qwen3-32B-R | executed_alternative | 54 | **52** |
| Qwen3-32B-R | alternative_offer | 46 | **54** |
| Qwen3-32B-R | normative_suggestion | 40 | **61** |
| Qwen3-32B-R | statement_of_principle | 13 | **25** |
| Qwen3-32B-R | role_based | 4 | **9** |
