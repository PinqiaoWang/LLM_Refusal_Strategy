# Claude Opus 3 re-run on the main-collection prompt set

Collected 2026-08-30 by Cameron (via Anthropic direct API, `claude-3-opus-20240229`,
temperature 0, same schema as all other response files).

## Why this exists

The original Opus 3 collection (`../responses_claude-opus-3.json`, 2026-05-25) was run
against a prompt file that matches the current `data/prompts/sampled_200_final_queries.json`
— which is NOT the 200-prompt set the 15 main-analysis models received. It overlaps the
main set on only 135 of 200 queries (verified by both `(source, candidate_id)` and query
text). Note this 135 is a different number from the 138-query overlap between the May
collection and the August 262-prompt robustness set (135 seed overlap + 3 added during
expansion).

This directory contains Opus 3 responses to the **exact 200 prompts used by the main
15-model collection**, reconstructed from the main response files and enriched with
SorryBench categories from the candidate pools:
`data/prompts/sampled_200_main_collection_reconstructed.json` (200/200 queries matched
their candidate-pool records; zero query-text mismatches).

## How to use (entirely optional)

- If incorporated, Opus 3 becomes prompt-matched with the main 16 models — no restriction
  to 135 shared prompts needed for the temporal / apology-decay analysis, and Appendix
  wording about the partial overlap could be simplified.
- If not incorporated, nothing else references this directory; ignore it.
- Judged annotations (GPT-5.5, identical prompt SHA `238bb923…` to the full corpus):
  `data/annotations/additional_models_expo_main200_rerun/responses_claude-opus-3.judged.{json,csv}`
  — 195 judged, 3 service-level skips, 2 judge-classification failures (judge refused;
  deterministic, same phenomenon as the corpus's 0.5%). Against the May judgments on the
  129 prompts judged in both: Layer 0 agreement 99.2%, Layer 1 agreement 98.3%.

## Collection outcome (2026-08-30)

197/200 in-voice responses; 3 prompts (final_sample_id 91, 93, 169 — all S8 Intellectual
Property) returned `Output blocked by content filtering policy` from the Anthropic API,
deterministically (retried once, same result). These are service-level refusals, recorded
the same way as the May file's one blocked case (error field, HTTP 400). Note all three
received normal in-voice responses in the May collection — the provider-side filter has
tightened since then.

## Related caveat (for whoever re-runs analyses)

`analysis/refusal_analysis.Rmd` attaches `sorry_bench_category_name` by joining responses
to `data/prompts/sampled_200_final_queries.json` on `final_sample_id`. Because the current
file on disk is the regenerated (August-seed) set, 198/200 of those ids now point to
different queries than the May responses. This only affects the exploratory
SorryBench-category chunk (nothing in the paper — the paper's harm categories are Llama
Guard labels carried inside the response files), but the join is silently wrong until the
May-matched prompt file (`sampled_200_main_collection_reconstructed.json`) is used instead.
