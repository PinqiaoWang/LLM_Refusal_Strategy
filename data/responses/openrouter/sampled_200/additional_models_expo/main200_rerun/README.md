# Claude Opus 3 re-run on the main-collection prompt set

Collected 2026-08-30 by Cameron (via Anthropic direct API, `claude-3-opus-20240229`,
temperature 0, same schema as all other response files).

## Why this exists

The original Opus 3 collection (`../responses_claude-opus-3.json`, 2026-05-25) was run
against the superseded Set A, now stored as `data/prompts/outdated_queries.json`, rather
than the final 200-prompt Set B received by the main-analysis models. Set A overlaps Set B
on only 135 of 200 queries (verified by both `(source, candidate_id)` and query text).
Note this 135 is different from the 138-query overlap between final Set B and the August
262-prompt robustness set because the August set contains all of Set A plus 62 additions.

This directory contains Opus 3 responses to the **exact 200 prompts used by the main
collection**, reconstructed from the main response files and enriched with SorryBench
categories from the candidate pools:
`data/prompts/sampled_200_main_collection_reconstructed.json` (200/200 queries matched
their candidate-pool records; zero query-text mismatches).

## How to use (entirely optional)

- The prompt-matched rerun is used for the supplementary temporal / apology-decay
  analysis; no restriction to the old 135-query overlap is required.
- Opus 3 remains outside the designated 16-model primary panel.
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

## Prompt-file note

`data/prompts/sampled_200_final_queries.json` is now the canonical final Set B used by
the main analysis. `sampled_200_main_collection_reconstructed.json` contains the same
ordered query/source/candidate-ID sequence with reconstructed source-pool metadata.
