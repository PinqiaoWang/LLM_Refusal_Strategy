library(tidyverse)

# Diagnostic script for checking whether model-level attributes explain
# differences in refusal style. This is intentionally separate from the main
# Rmd so the paper figures stay stable.

ANNOTATION_DIR <- file.path("data", "annotations")
OUTPUT_DIR <- file.path("analysis", "model_attribute_diagnostics")
dir.create(OUTPUT_DIR, recursive = TRUE, showWarnings = FALSE)

out_path <- function(filename) {
  file.path(OUTPUT_DIR, filename)
}

PROMPT_SHA256 <- "238bb923037bb4126bef041f202fd6547e328aa62f4f61f06b8f63d784891fb1"

L2_FEATURES <- c(
  "explicit_nc", "implicit_nc", "apology", "hedge", "explanatory_preface",
  "positive_alignment", "solidarity", "negative_stance",
  "normative_suggestion", "statement_of_principle",
  "alternative_offer", "executed_alternative", "role_based"
)

MODEL_ORDER <- c(
  "gpt-4o", "gpt-5", "gpt-5.3", "gpt-5.3-reasoning",
  "claude-sonnet-3.7", "claude-sonnet-4.6",
  "claude-opus-4.6", "claude-opus-4.6-reasoning",
  "gemini-2.5-pro", "grok-4.20",
  "llama-3.1-8b", "llama-3.1-70b",
  "qwen3-8b", "qwen3-8b-reasoning",
  "qwen3-32b", "qwen3-32b-reasoning"
)

MODEL_FAMILY <- c(
  "gpt-4o" = "OpenAI",
  "gpt-5" = "OpenAI",
  "gpt-5.3" = "OpenAI",
  "gpt-5.3-reasoning" = "OpenAI",
  "claude-sonnet-3.7" = "Anthropic",
  "claude-sonnet-4.6" = "Anthropic",
  "claude-opus-4.6" = "Anthropic",
  "claude-opus-4.6-reasoning" = "Anthropic",
  "gemini-2.5-pro" = "Google",
  "grok-4.20" = "xAI",
  "llama-3.1-8b" = "Meta",
  "llama-3.1-70b" = "Meta",
  "qwen3-8b" = "Qwen",
  "qwen3-8b-reasoning" = "Qwen",
  "qwen3-32b" = "Qwen",
  "qwen3-32b-reasoning" = "Qwen"
)

MODEL_ACCESS <- c(
  "gpt-4o" = "closed/proprietary",
  "gpt-5" = "closed/proprietary",
  "gpt-5.3" = "closed/proprietary",
  "gpt-5.3-reasoning" = "closed/proprietary",
  "claude-sonnet-3.7" = "closed/proprietary",
  "claude-sonnet-4.6" = "closed/proprietary",
  "claude-opus-4.6" = "closed/proprietary",
  "claude-opus-4.6-reasoning" = "closed/proprietary",
  "gemini-2.5-pro" = "closed/proprietary",
  "grok-4.20" = "closed/proprietary",
  "llama-3.1-8b" = "open-weight",
  "llama-3.1-70b" = "open-weight",
  "qwen3-8b" = "open-weight",
  "qwen3-8b-reasoning" = "open-weight",
  "qwen3-32b" = "open-weight",
  "qwen3-32b-reasoning" = "open-weight"
)

EXCLUDED_MODELS <- c(
  "gpt-4-turbo",
  "llama-3-70b-instruct",
  "mistral-7b-instruct-v0.1",
  "claude-opus-3"
)

read_judged <- function(path) {
  model <- basename(path) |>
    str_remove("^responses_") |>
    str_remove("[.]judged[.]csv$")

  suppressWarnings(readr::read_csv(
    path,
    show_col_types = FALSE,
    col_types = cols(.default = col_character())
  )) |>
    mutate(model = model)
}

to_int_binary <- function(x) {
  x <- na_if(trimws(x), "")
  suppressWarnings(as.integer(x))
}

mean_abs_l2_distance <- function(a, b) {
  mean(abs(as.numeric(a[L2_FEATURES]) - as.numeric(b[L2_FEATURES])), na.rm = TRUE)
}

max_l2_feature_diff <- function(a, b) {
  diffs <- abs(as.numeric(a[L2_FEATURES]) - as.numeric(b[L2_FEATURES]))
  tibble(
    max_feature = L2_FEATURES[which.max(diffs)],
    max_feature_diff = max(diffs, na.rm = TRUE)
  )
}

pair_diff <- function(pairs, label, model_rates) {
  map_dfr(seq_len(nrow(pairs)), function(i) {
    a <- pairs$a[i]
    b <- pairs$b[i]
    ra <- model_rates |> filter(model == a) |> slice(1)
    rb <- model_rates |> filter(model == b) |> slice(1)
    max_diff <- max_l2_feature_diff(ra, rb)

    tibble(
      comparison = label,
      a = a,
      b = b,
      n_nc_a = ra$n_nc,
      n_nc_b = rb$n_nc,
      nc_rate_a = ra$nc_rate,
      nc_rate_b = rb$nc_rate,
      nc_rate_diff = ra$nc_rate - rb$nc_rate,
      mean_abs_l2_diff = mean_abs_l2_distance(ra, rb)
    ) |>
      bind_cols(max_diff)
  })
}

permutation_p_mean_diff <- function(values_a, values_b, n_perm = 10000, seed = 20260525) {
  set.seed(seed)
  observed <- mean(values_a, na.rm = TRUE) - mean(values_b, na.rm = TRUE)
  pooled <- c(values_a, values_b)
  n_a <- length(values_a)

  null <- replicate(n_perm, {
    shuffled <- sample(pooled)
    mean(shuffled[seq_len(n_a)], na.rm = TRUE) -
      mean(shuffled[-seq_len(n_a)], na.rm = TRUE)
  })

  tibble(
    observed_diff = observed,
    p_two_sided = mean(abs(null) >= abs(observed))
  )
}

raw <- list.files(
  ANNOTATION_DIR,
  pattern = "^responses_.*[.]judged[.]csv$",
  full.names = TRUE
) |>
  map_dfr(read_judged) |>
  filter(!model %in% EXCLUDED_MODELS)

if (!"judge_skipped" %in% names(raw)) raw$judge_skipped <- NA_character_
if (!"skip_reason" %in% names(raw)) raw$skip_reason <- NA_character_

df <- raw |>
  mutate(
    across(all_of(L2_FEATURES), to_int_binary),
    parse_error = if_else(parse_error %in% c("True", "TRUE", "1"), TRUE, FALSE, missing = FALSE),
    judge_skipped = if_else(judge_skipped %in% c("True", "TRUE", "1"), TRUE, FALSE, missing = FALSE),
    family = MODEL_FAMILY[model],
    access = MODEL_ACCESS[model]
  ) |>
  filter(
    is.na(judge_prompt_sha256) |
      judge_prompt_sha256 == "" |
      judge_prompt_sha256 == PROMPT_SHA256
  )

df_clean <- df |>
  filter(!parse_error, !judge_skipped, !is.na(layer0))

df_nc <- df_clean |>
  filter(layer0 == "Non-compliance")

model_l2 <- df_nc |>
  group_by(model, family, access) |>
  summarise(
    n_nc = n(),
    across(all_of(L2_FEATURES), \(x) mean(x, na.rm = TRUE)),
    .groups = "drop"
  )

model_l0 <- df_clean |>
  group_by(model, family, access) |>
  summarise(
    n = n(),
    nc_rate = mean(layer0 == "Non-compliance"),
    .groups = "drop"
  )

model_rates <- model_l2 |>
  left_join(model_l0, by = c("model", "family", "access")) |>
  mutate(model = factor(model, levels = MODEL_ORDER)) |>
  arrange(model)

write_csv(model_rates, out_path("model_level_l2_rates_for_attributes.csv"))

size_pairs <- tribble(
  ~a, ~b,
  "llama-3.1-8b", "llama-3.1-70b",
  "qwen3-8b", "qwen3-32b",
  "qwen3-8b-reasoning", "qwen3-32b-reasoning"
)

reasoning_pairs <- tribble(
  ~a, ~b,
  "claude-opus-4.6", "claude-opus-4.6-reasoning",
  "gpt-5.3", "gpt-5.3-reasoning",
  "qwen3-8b", "qwen3-8b-reasoning",
  "qwen3-32b", "qwen3-32b-reasoning"
)

temporal_pairs <- tribble(
  ~a, ~b,
  "gpt-4o", "gpt-5",
  "gpt-5", "gpt-5.3",
  "gpt-4o", "gpt-5.3",
  "claude-sonnet-3.7", "claude-sonnet-4.6",
  "claude-sonnet-4.6", "claude-opus-4.6",
  "claude-sonnet-3.7", "claude-opus-4.6"
)

closed_family_pairs <- expand_grid(
  a = c("gpt-5.3", "claude-opus-4.6", "gemini-2.5-pro", "grok-4.20"),
  b = c("gpt-5.3", "claude-opus-4.6", "gemini-2.5-pro", "grok-4.20")
) |>
  filter(a < b)

attribute_pairs <- bind_rows(
  pair_diff(size_pairs, "size", model_rates),
  pair_diff(reasoning_pairs, "reasoning", model_rates),
  pair_diff(temporal_pairs, "temporal", model_rates),
  pair_diff(closed_family_pairs, "closed_family", model_rates)
)

write_csv(attribute_pairs, out_path("model_attribute_pair_differences.csv"))

attribute_effect_direction <- attribute_pairs |>
  filter(comparison %in% c("size", "reasoning")) |>
  rowwise() |>
  mutate(
    feature_a = model_rates[[max_feature]][match(a, model_rates$model)],
    feature_b = model_rates[[max_feature]][match(b, model_rates$model)],
    nc_change_pp = 100 * (nc_rate_b - nc_rate_a),
    mean_abs_l2_diff_pp = 100 * mean_abs_l2_diff,
    largest_l2_shift_pp = 100 * (feature_b - feature_a),
    direction_reference = case_when(
      comparison == "size" ~ "second model minus first model (larger - smaller)",
      comparison == "reasoning" ~ "second model minus first model (reasoning - standard)",
      TRUE ~ "second model minus first model"
    ),
    direction_summary = case_when(
      comparison == "size" & abs(nc_change_pp) > 10 & mean_abs_l2_diff_pp < 3 ~
        "Large NC-rate change, small average L2-form change.",
      comparison == "size" & max_feature == "apology" ~
        "Larger Qwen model uses much more apology; size pattern is family-specific.",
      comparison == "reasoning" & mean_abs_l2_diff_pp < 2 ~
        "Reasoning mode has limited observed effect on refusal form.",
      comparison == "reasoning" & a == "qwen3-32b" ~
        "Reasoning increases normative suggestion most clearly for Qwen3-32B.",
      TRUE ~ "Observed effect is descriptive and pair-specific."
    )
  ) |>
  ungroup() |>
  transmute(
    comparison,
    pair_id = paste(a, "vs", b),
    direction_reference,
    nc_rate_a,
    nc_rate_b,
    nc_change_pp,
    mean_abs_l2_diff_pp,
    largest_l2_shift_feature = max_feature,
    largest_l2_shift_pp,
    feature_rate_a = feature_a,
    feature_rate_b = feature_b,
    direction_summary
  )

write_csv(attribute_effect_direction, out_path("attribute_effect_size_direction_table.csv"))

attribute_summary <- attribute_pairs |>
  group_by(comparison) |>
  summarise(
    n_pairs = n(),
    mean_pair_l2_diff = mean(mean_abs_l2_diff),
    median_pair_l2_diff = median(mean_abs_l2_diff),
    max_pair_l2_diff = max(mean_abs_l2_diff),
    mean_abs_nc_diff = mean(abs(nc_rate_diff)),
    .groups = "drop"
  )

write_csv(attribute_summary, out_path("model_attribute_pair_summary.csv"))

access_summary <- model_rates |>
  group_by(access) |>
  summarise(
    models = paste(as.character(model), collapse = ", "),
    n_models = n(),
    mean_nc_rate = mean(nc_rate),
    across(all_of(L2_FEATURES), mean),
    .groups = "drop"
  )

write_csv(access_summary, out_path("open_closed_l2_summary.csv"))

access_feature_tests <- map_dfr(c("nc_rate", L2_FEATURES), function(feature) {
  closed_values <- model_rates |>
    filter(access == "closed/proprietary") |>
    pull(feature)
  open_values <- model_rates |>
    filter(access == "open-weight") |>
    pull(feature)

  permutation_p_mean_diff(closed_values, open_values) |>
    mutate(feature = feature, .before = 1)
})

write_csv(access_feature_tests, out_path("open_closed_permutation_tests.csv"))

reasoning_pair_tests <- reasoning_pairs |>
  mutate(pair = paste(a, b, sep = " vs ")) |>
  left_join(model_rates |> select(model, nc_rate, all_of(L2_FEATURES)), by = c("a" = "model")) |>
  left_join(model_rates |> select(model, nc_rate, all_of(L2_FEATURES)), by = c("b" = "model"), suffix = c("_base", "_reasoning")) |>
  mutate(
    mean_abs_l2_diff = map2_dbl(a, b, \(base_model, reasoning_model) {
      base_rates <- model_rates |> filter(model == base_model) |> slice(1)
      reasoning_rates <- model_rates |> filter(model == reasoning_model) |> slice(1)
      mean_abs_l2_distance(base_rates, reasoning_rates)
    }),
    nc_rate_diff = nc_rate_base - nc_rate_reasoning
  ) |>
  select(pair, mean_abs_l2_diff, nc_rate_diff)

write_csv(reasoning_pair_tests, out_path("reasoning_pair_tests.csv"))

APPENDIX_L2_FEATURES <- c(
  "implicit_nc", "apology", "solidarity", "negative_stance",
  "normative_suggestion", "alternative_offer", "executed_alternative"
)

l0_detail <- df_clean |>
  group_by(model) |>
  summarise(
    n_total = n(),
    full_compliance = mean(layer0 == "Full compliance"),
    non_compliance = mean(layer0 == "Non-compliance"),
    partial_compliance = mean(layer0 == "Partial compliance"),
    .groups = "drop"
  )

l1_detail <- df_nc |>
  group_by(model) |>
  summarise(
    n_nc = n(),
    bare = mean(layer1 == "Bare", na.rm = TRUE),
    ethics_based = mean(layer1 == "Ethics-based", na.rm = TRUE),
    policy_based = mean(layer1 == "Policy-based", na.rm = TRUE),
    capacity_based = mean(layer1 == "Capacity-based", na.rm = TRUE),
    .groups = "drop"
  )

appendix_model_table <- model_rates |>
  select(model, family, access, all_of(APPENDIX_L2_FEATURES)) |>
  left_join(l0_detail, by = "model") |>
  left_join(l1_detail, by = "model") |>
  mutate(model = as.character(model)) |>
  select(
    model, family, access,
    n_total, n_nc,
    full_compliance, non_compliance, partial_compliance,
    bare, ethics_based, policy_based, capacity_based,
    all_of(APPENDIX_L2_FEATURES)
  )

write_csv(appendix_model_table, out_path("model_attribute_appendix_model_table.csv"))

pair_rows <- function(pairs, comparison, a_mode = "A", b_mode = "B") {
  pairs |>
    mutate(pair_id = paste(a, b, sep = " vs ")) |>
    pivot_longer(c(a, b), names_to = "side", values_to = "model") |>
    mutate(
      comparison = comparison,
      mode = if_else(side == "a", a_mode, b_mode),
      .before = pair_id
    ) |>
    select(comparison, pair_id, mode, model) |>
    left_join(appendix_model_table, by = "model")
}

attribute_appendix_rows <- bind_rows(
  pair_rows(size_pairs, "size", "Smaller", "Larger"),
  pair_rows(reasoning_pairs, "reasoning", "Standard", "Reasoning"),
  pair_rows(temporal_pairs, "temporal", "Earlier", "Later"),
  pair_rows(closed_family_pairs, "closed_family", "Model A", "Model B")
)

attribute_appendix_l0_l1 <- attribute_appendix_rows |>
  select(
    comparison, pair_id, mode, model, family, access,
    n_total, n_nc,
    full_compliance, non_compliance, partial_compliance,
    bare, ethics_based, policy_based, capacity_based
  )

attribute_appendix_l2 <- attribute_appendix_rows |>
  select(
    comparison, pair_id, mode, model, family, access,
    n_nc, all_of(APPENDIX_L2_FEATURES)
  )

write_csv(attribute_appendix_l0_l1, out_path("model_attribute_appendix_l0_l1.csv"))
write_csv(attribute_appendix_l2, out_path("model_attribute_appendix_l2.csv"))

walk(unique(attribute_appendix_rows$comparison), function(comparison_name) {
  write_csv(
    attribute_appendix_l0_l1 |> filter(comparison == comparison_name),
    out_path(paste0(comparison_name, "_appendix_l0_l1.csv"))
  )
  write_csv(
    attribute_appendix_l2 |> filter(comparison == comparison_name),
    out_path(paste0(comparison_name, "_appendix_l2.csv"))
  )
})

AFFILIATIVE_FEATURES <- c(
  "apology", "positive_alignment", "solidarity", "explanatory_preface", "hedge"
)

temporal_affiliative_features <- attribute_appendix_rows |>
  filter(comparison == "temporal") |>
  select(comparison, pair_id, mode, model, family, n_nc) |>
  left_join(
    model_rates |> select(model, all_of(AFFILIATIVE_FEATURES)),
    by = "model"
  )

write_csv(temporal_affiliative_features, out_path("temporal_affiliative_features.csv"))

mcnemar_from_binary <- function(x, y) {
  keep <- !is.na(x) & !is.na(y)
  x <- as.integer(x[keep])
  y <- as.integer(y[keep])

  if (length(x) == 0) {
    return(tibble(n_paired = 0L, both_0 = NA_integer_, a1_b0 = NA_integer_,
                  a0_b1 = NA_integer_, both_1 = NA_integer_, p_value = NA_real_))
  }

  both_0 <- sum(x == 0 & y == 0)
  a1_b0 <- sum(x == 1 & y == 0)
  a0_b1 <- sum(x == 0 & y == 1)
  both_1 <- sum(x == 1 & y == 1)
  tab <- matrix(c(both_0, a1_b0, a0_b1, both_1), nrow = 2, byrow = TRUE)

  p_value <- if ((a1_b0 + a0_b1) == 0) {
    NA_real_
  } else {
    suppressWarnings(mcnemar.test(tab, correct = FALSE)$p.value)
  }

  tibble(
    n_paired = length(x),
    both_0 = both_0,
    a1_b0 = a1_b0,
    a0_b1 = a0_b1,
    both_1 = both_1,
    p_value = p_value
  )
}

l0_pair_mcnemar <- bind_rows(
  size_pairs |> mutate(comparison = "size"),
  reasoning_pairs |> mutate(comparison = "reasoning"),
  temporal_pairs |> mutate(comparison = "temporal"),
  closed_family_pairs |> mutate(comparison = "closed_family")
) |>
  mutate(pair_id = paste(a, b, sep = " vs ")) |>
  pmap_dfr(function(a, b, comparison, pair_id) {
    wide <- df_clean |>
      filter(model %in% c(a, b)) |>
      transmute(final_sample_id = as.character(final_sample_id),
                model,
                nc = as.integer(layer0 == "Non-compliance")) |>
      pivot_wider(names_from = model, values_from = nc)

    mcnemar_from_binary(wide[[a]], wide[[b]]) |>
      mutate(comparison = comparison, pair_id = pair_id, a = a, b = b, .before = 1)
  })

write_csv(l0_pair_mcnemar, out_path("model_pair_l0_mcnemar_tests.csv"))

l2_pair_mcnemar <- bind_rows(
  size_pairs |> mutate(comparison = "size"),
  reasoning_pairs |> mutate(comparison = "reasoning"),
  temporal_pairs |> mutate(comparison = "temporal"),
  closed_family_pairs |> mutate(comparison = "closed_family")
) |>
  mutate(pair_id = paste(a, b, sep = " vs ")) |>
  pmap_dfr(function(a, b, comparison, pair_id) {
    map_dfr(L2_FEATURES, function(feature) {
      wide <- df_nc |>
        filter(model %in% c(a, b)) |>
        transmute(final_sample_id = as.character(final_sample_id),
                  model,
                  value = .data[[feature]]) |>
        pivot_wider(names_from = model, values_from = value)

      mcnemar_from_binary(wide[[a]], wide[[b]]) |>
        mutate(comparison = comparison, pair_id = pair_id, a = a, b = b,
               feature = feature, .before = 1)
    })
  })

write_csv(l2_pair_mcnemar, out_path("model_pair_l2_mcnemar_tests.csv"))

prompt_alignment_check <- bind_rows(
  size_pairs |> mutate(comparison = "size"),
  reasoning_pairs |> mutate(comparison = "reasoning"),
  temporal_pairs |> mutate(comparison = "temporal"),
  closed_family_pairs |> mutate(comparison = "closed_family")
) |>
  mutate(pair_id = paste(a, b, sep = " vs ")) |>
  pmap_dfr(function(a, b, comparison, pair_id) {
    da <- df_clean |>
      filter(model == a) |>
      transmute(final_sample_id = as.character(final_sample_id),
                query_a = query)
    db <- df_clean |>
      filter(model == b) |>
      transmute(final_sample_id = as.character(final_sample_id),
                query_b = query)
    joined <- inner_join(da, db, by = "final_sample_id")

    tibble(
      comparison = comparison,
      pair_id = pair_id,
      n_a = nrow(da),
      n_b = nrow(db),
      n_joined = nrow(joined),
      same_query = sum(joined$query_a == joined$query_b, na.rm = TRUE),
      different_query = sum(joined$query_a != joined$query_b, na.rm = TRUE),
      unique_ids_a = n_distinct(da$final_sample_id),
      unique_ids_b = n_distinct(db$final_sample_id)
    )
  })

write_csv(prompt_alignment_check, out_path("model_pair_prompt_alignment_check.csv"))

cat("\nWrote:\n")
cat("- ", out_path("model_level_l2_rates_for_attributes.csv"), "\n", sep = "")
cat("- ", out_path("model_attribute_pair_differences.csv"), "\n", sep = "")
cat("- ", out_path("model_attribute_pair_summary.csv"), "\n", sep = "")
cat("- ", out_path("attribute_effect_size_direction_table.csv"), "\n", sep = "")
cat("- ", out_path("model_attribute_appendix_model_table.csv"), "\n", sep = "")
cat("- ", out_path("model_attribute_appendix_l0_l1.csv"), "\n", sep = "")
cat("- ", out_path("model_attribute_appendix_l2.csv"), "\n", sep = "")
cat("- ", out_path("{size,reasoning,temporal,closed_family}_appendix_l0_l1.csv"), "\n", sep = "")
cat("- ", out_path("{size,reasoning,temporal,closed_family}_appendix_l2.csv"), "\n", sep = "")
cat("- ", out_path("temporal_affiliative_features.csv"), "\n", sep = "")
cat("- ", out_path("open_closed_l2_summary.csv"), "\n", sep = "")
cat("- ", out_path("open_closed_permutation_tests.csv"), "\n", sep = "")
cat("- ", out_path("reasoning_pair_tests.csv"), "\n", sep = "")
cat("- ", out_path("model_pair_l0_mcnemar_tests.csv"), "\n", sep = "")
cat("- ", out_path("model_pair_l2_mcnemar_tests.csv"), "\n", sep = "")
cat("- ", out_path("model_pair_prompt_alignment_check.csv"), "\n", sep = "")

cat("\nPair summary:\n")
print(attribute_summary, n = Inf)

cat("\nOpen/closed permutation tests:\n")
print(access_feature_tests |> arrange(p_two_sided), n = Inf)
