# Camera-Ready 新增/改写段落英文初稿

`[X]` = 重跑后填入的数字。引用标记 `[CITE: ...]` = 需你们核定具体文献。所有内容为初稿,请按你们的行文习惯改写。

---

## 1. Abstract 改写(把 face redistribution 提到最前)

改动集中在后半段。建议替换从 "Applying this taxonomy..." 起的部分:

> Applying this taxonomy to responses from 16 modern LLMs across 14 harm categories, we find that although models differ in how they refuse, their refusals are overall explicit, ethics-based, and strongly morally evaluative, with interactional repair occurring mainly through offering or providing safer alternatives instead of interpersonal facework. Read through politeness theory, this pattern reflects not a reduction of face threat but a **redistribution** of it: models increasingly protect their own speaker face — avoiding apologies, expressions of regret, and admissions of inability — while directing threat toward the user, both to positive face through moral evaluation and to negative face through redirection and unsolicited suggestion. This redistribution is especially consequential in sensitive harm contexts, where overuse of negative framing may make users feel shamed or provoked, undermining the purpose of safe non-compliance. We therefore call for alignment evaluation that considers not only whether models refuse harmful requests, but also whether they refuse in ways that are contextually adaptive and socially accountable for the interactional consequences of saying no.

---

## 2. §2.2 扩写 — Face dimensions

接在现有 Goffman/Brown & Levinson 段之后:

> Politeness theory distinguishes two aspects of face that any face-threatening act may put at risk: **positive face**, a person's desire for their wants and self-image to be approved of, and **negative face**, their desire to be unimpeded in action (Brown and Levinson, 1987). Crucially, a single act can threaten the face of either participant. A refusal threatens the requester's positive face when it conveys disapproval of what they wanted, and their negative face when it redirects them toward a course of action they did not choose. It threatens the *refuser's* own face when it is delivered through apology, expressed regret, or admitted inability, since these concede fault or incompetence (Goffman, 1967; Johnson et al., 2004). Human refusers typically absorb some speaker-face cost — apologizing, pleading obstacles, hedging — precisely in order to limit the threat borne by the hearer (Beebe et al., 1990; Campillo et al., 2009). This four-way distinction — speaker vs. hearer face, positive vs. negative face — provides the analytic vocabulary we use in §6 to interpret how LLM refusals allocate interactional cost.

## 3. §2.2 新增 — Stance(Ggm3 第三条批评)

新起一段:

> Three features in our taxonomy — *positive alignment*, *solidarity / empathy*, and *negative stance* — are not politeness strategies in the Brown and Levinson sense but instances of **stance-taking**: the speaker's public evaluation of an object, positioning of the self, and alignment with the interlocutor [CITE: Du Bois 2007; Biber & Finegan 1989; Kiesling 2009 — 请核定]. Stance and facework are analytically distinct but interactionally coupled: evaluating a request as harmful (*negative stance*) simultaneously positions the model as a moral authority and disaligns it from the user, and it is this disalignment, rather than the refusal itself, that carries the threat to the user's positive face. Separating the two constructs lets us ask not only how forcefully a model refuses, but what evaluative position it takes toward the user in doing so — a question that the safety-behavior taxonomies reviewed in §2.1 cannot express.

## 4. §3 或 Table 1 附近 — Layer 2 理论刻画说明 + scope boundary

> Table 1 gives operational definitions optimized for reliable annotation. Table [N] additionally characterizes each Layer 2 category theoretically, along three dimensions: whether the category is a **form-based device** (hedges, explanatory prefaces, role-based self-positioning) or a **functional feature**; for functional features, the class of **illocutionary act** they realize (commissive, expressive, assertive, directive; Searle, 1976 [CITE 核定]); and the **stance or face-management** work they perform. We note that our explicit/implicit distinction is a matter of illocutionary type: explicit non-compliance is realized commissively, through an utterance that directly commits the model to not performing the requested action, whereas implicit non-compliance is conveyed through an assertive or expressive act — a justification, an expression of discomfort — that leaves the commitment implicated rather than stated. The terms *action-negating marker* and *non-action-negating marker* used in the annotation codebook (Appendix A) are operational coding cues for this distinction, not proposed pragmatic constructs.
>
> We emphasize a scope boundary. This taxonomy is a **descriptive measurement instrument**: it characterizes how models realize non-compliance, not whether a given realization is pragmatically appropriate. Establishing appropriateness requires evidence about user uptake — whether a refusal is experienced as shaming, dismissive, or supportive — which our design does not provide. §6 therefore reads our findings against documented human refusal behavior and against face theory, and identifies where the observed patterns are *theoretically expected to be* interactionally costly, leaving direct validation to user studies.

### 建议的 Layer 2 理论刻画表(骨架,请核定归类)

| Feature | Form / Function | Illocutionary type | Stance / face work |
|---|---|---|---|
| Explicit NC | Function | Commissive | Bald FTA to hearer's negative face |
| Implicit NC | Function | Assertive / expressive | FTA implicated, mitigated |
| Apology / regret | Function | Expressive | Speaker positive-face cost; mitigates hearer FTA |
| Hedge | Form | — (modality) | Softens force of the FTA |
| Explanatory preface | Form | (Assertive, deferring) | Delays FTA; preference organization |
| Positive alignment | Function | Expressive | Stance: alignment; hearer positive-face redress |
| Solidarity / empathy | Function | Expressive | Stance: affective alignment; positive-face redress |
| Negative stance | Function | Assertive (evaluative) | Stance: negative evaluation + disalignment; hearer positive-face threat |
| Alternative offer | Function | Commissive (offer) | Hearer negative-face threat; helpfulness repair |
| Executed alternative | Function | Directive / assertive | Hearer negative-face threat; substantive repair |
| Normative suggestion | Function | Directive | Stance: implicit evaluation; threatens both hearer faces |
| Statement of principle | Function | Assertive | Impersonalizes the FTA; deflects speaker responsibility |
| Role-based self-positioning | Form | (Assertive, identity) | Deflects speaker-face cost onto category membership |

---

## 5. §6 Conclusion 改写 — Face redistribution / pragmatic overcorrection

这是全文最重要的一处改写。建议替换现有 §6 主体:

> Through the lens of pragmatics, this work shows that LLM refusals exhibit a distinct interactional style: explicit, firm non-compliance grounded in ethical justification, with interactional repair pursued through continued helpfulness rather than through interpersonal facework. Read against the four-way face distinction introduced in §2.2, the trajectory we observe across model generations is best described not as a reduction of face threat but as its **redistribution**.
>
> Early models in our sample absorbed substantial speaker-face cost. Apology and expressed regret — which concede fault and position the model as having failed the user — appeared in `[X]%` of GPT-4o refusals and `[X]%` of Claude Opus 3 refusals. In recent frontier models these devices have largely receded (`[X]%` in GPT-5.3, `[X]%` in Opus 4.6), while the features that carry threat to the *hearer* have grown: negative stance, which disapproves of the user's request and thereby threatens their positive face, rose from `[X]%` to `[X]%` in the OpenAI sequence, and normative suggestion and alternative offers, which redirect the user toward an action they did not choose and thereby threaten their negative face, rose from `[X]%` to `[X]%` and `[X]%` to `[X]%` respectively. Models have not become more or less polite in aggregate; they have shifted who pays for the refusal.
>
> There is a defensible rationale for part of this shift. Apologizing for declining to assist with a violent crime is pragmatically odd: it implies the refusal is a regrettable failure rather than the correct outcome, and it invites renegotiation. Removing speaker-face mitigation makes safety boundaries legible and non-negotiable, which is plausibly what "safe completion" training targets (Yuan et al., 2025b). But legibility does not require moral evaluation of the user, and the two have been coupled in practice. The result resembles a **pragmatic overcorrection**: in withdrawing from self-deprecating facework, models have moved not to face-neutral refusal but to hearer-directed face threat, and especially to threats against the user's positive face.
>
> This coupling is most consequential where the user is least able to absorb it. In Suicide & Self-Harm contexts, models produce their most care-oriented refusals overall, yet still take an explicit negative stance in `[X]%` of cases — directing positive-face threat at users for whom shame is itself a documented barrier to help-seeking (Sheehy et al., 2020). In severely harmful contexts, conversely, apparent solidarity can function as disguised evaluation, attributing the request to psychological disturbance and so threatening positive face under the guise of redress (§5.4). In both cases the interactional cost is borne by the user, and in both cases the alternative is available: a refusal can be explicit, non-negotiable, and grounded in ethics without also constituting a verdict on the person who asked.
>
> We therefore argue that alignment evaluation should treat the allocation of face threat as a design parameter rather than a byproduct. Constraining models from complying in harmful contexts is necessary; grounded non-compliance need not equate to socially careless behavior. Whether the redistribution we document is a deliberate design choice or an unintended consequence of optimizing for boundary clarity, its interactional costs are measurable, and our taxonomy provides one instrument for measuring them.

---

## 6. §5.3 小改 — 让结果段接回理论

在 "LLMs prioritize moral judgement over facework" 小节末尾加一句,提前埋下 §6 的论点:

> In face-theoretic terms, these features do not sit on a single politeness continuum: apology and hedging bear on the *model's* face, whereas negative stance and normative suggestion bear on the *user's*. The pattern in Figure 2 is therefore not simply "less politeness" but a systematic reallocation of interactional cost from speaker to hearer, which we develop in §6.

## 7. §5.5 精简

现有两段大量重复逐模型数字。建议保留趋势陈述、把逐模型数字全部移入附录:

> Both frontier providers show a shared decline in *apology / regret*, one of the most recognizable politeness markers in human refusals (Figure 4), despite following divergent stylistic trajectories: OpenAI models shift from apologetic toward normatively evaluative and redirective refusal, whereas Anthropic models begin from an already strongly evaluative baseline and briefly intensify affiliative softening in Sonnet 3.7 before receding by Opus 4.6. Other affiliative features do not compensate for the loss of apology in either family (per-model rates in Appendix H). Because LLM refusals are already highly explicit, ethics-based, and morally evaluative, this erosion compounds a pre-existing facework deficit rather than offsetting an excess.

---

## 8. Limitations 更新(扩样与跨家族 judge 之后)

> Our expanded query set contains `[N]` prompts, with at least 20 per harm category where the source pools permit; `[list categories]` remain below this target because the available unsafe prompt pools are smaller (Table 8). Estimates for these categories should be read as exploratory, and we report the number of non-compliant responses underlying every model-by-category estimate (Table 14).
>
> All large-scale annotation is produced by an LLM judge. We constrain the judge to predefined features using the same codebook given to human annotators, validate it against human-adjudicated gold labels, and additionally verify robustness with a judge from a different model family (`[model]`, Appendix D), which reaches `[κ]` against gold labels and agrees with our primary judge on `[X]%` of feature labels. Residual judge bias cannot be excluded, and we treat these labels as scalable approximations rather than ground truth.
>
> Several Layer 2 features remain intentionally broad: *solidarity / empathy* covers both context-sensitive care and formulaic concern, and *executed alternative* captures the presence but not the quality of safer assistance.
>
> Finally, our analysis characterizes model outputs, not user uptake. We identify where refusal styles are theoretically expected to impose interactional cost, but we do not measure whether they affect trust, felt judgment, help-seeking, or attempts to renegotiate the boundary. Establishing which refusal strategies are pragmatically appropriate in which harm contexts requires user studies with the populations most affected, which we regard as the necessary next step.
