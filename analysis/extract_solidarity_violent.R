library(tidyverse)

ANNOTATION_DIR <- file.path("data", "annotations")
PROMPT_SHA256  <- "238bb923037bb4126bef041f202fd6547e328aa62f4f61f06b8f63d784891fb1"
EXCLUDED_MODELS <- c(
  "gpt-4-turbo", "llama-3-70b-instruct",
  "mistral-7b-instruct-v0.1", "claude-sonnet-4.6"
)
SEXUAL_VIOLENT_HARMS <- c(
  "Child Sexual Exploitation", "Sex-Related Crimes", "Sexual Content",
  "Violent Crimes", "Indiscriminate Weapons"
)

read_judged <- function(path) {
  model <- basename(path) |>
    str_remove("^responses_") |>
    str_remove("[.]judged[.]csv$")
  suppressWarnings(
    readr::read_csv(path, show_col_types = FALSE,
                    col_types = cols(.default = col_character()))
  ) |> mutate(model = model)
}

df <- list.files(ANNOTATION_DIR,
                 pattern = "^responses_.*[.]judged[.]csv$",
                 full.names = TRUE) |>
  map_dfr(read_judged) |>
  filter(!model %in% EXCLUDED_MODELS) |>
  filter(is.na(judge_prompt_sha256) |
           judge_prompt_sha256 == "" |
           judge_prompt_sha256 == PROMPT_SHA256) |>
  filter(layer0 == "Non-compliance") |>
  mutate(solidarity = as.integer(solidarity)) |>
  filter(solidarity == 1) |>
  filter(primary_llama_guard_category_name %in% SEXUAL_VIOLENT_HARMS)

cat("Total solidarity responses in sexual & violent harms cluster:", nrow(df), "\n\n")
cat("By harm category:\n")
print(table(df$primary_llama_guard_category_name))
cat("\nBy model:\n")
print(table(df$model))

df |>
  select(
    final_sample_id, model, primary_llama_guard_category_name,
    query, response, layer0, layer1,
    solidarity, negative_stance, apology,
    positive_alignment, normative_suggestion,
    alternative_offer, executed_alternative
  ) |>
  arrange(primary_llama_guard_category_name, model) |>
  write_csv("analysis/solidarity_sexual_violent_harms.csv")

cat("\nSaved to analysis/solidarity_sexual_violent_harms.csv\n")
