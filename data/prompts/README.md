# Prompt-set provenance

- `sampled_200_final_queries.json` is the final 2025 main-experiment query set
  (Set B). It is the exact 200-query set used by all 16 models in the primary
  analysis, including Claude Sonnet 4.6. The prompt-matched Claude Opus 3
  supplementary rerun also uses this set.
- `sampled_200_main_collection_reconstructed.json` reconstructs Set B from the
  main response records and adds source-pool metadata. Its query, source, and
  candidate-ID sequence matches `sampled_200_final_queries.json` exactly.
- `outdated_queries.json` is the superseded 200-query set (Set A). It was used
  by the original Claude Opus 3, GPT-4 Turbo, Llama 3 70B Instruct, and Mistral
  7B Instruct v0.1 supplementary collections. It also served as the 200-query
  seed for the August robustness collection.
- `sampled_expanded_final_queries.json` is the August 262-query robustness set:
  all 200 Set A queries plus 62 additions. Relative to the final 2025 Set B,
  it contains 138 shared queries and 124 different queries; Set B contains 62
  queries absent from the August set.

The response files are the authoritative record of which query set each model
actually received. These labels describe that observed provenance and prevent
the two historical 200-query files from being confused again.
