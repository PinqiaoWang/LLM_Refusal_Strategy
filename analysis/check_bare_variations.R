library(tidyverse)

ANNOTATION_DIR <- file.path("data", "annotations")
PROMPT_SHA256  <- "238bb923037bb4126bef041f202fd6547e328aa62f4f61f06b8f63d784891fb1"
EXCLUDED_MODELS <- c(
  "gpt-4-turbo", "llama-3-70b-instruct",
  "mistral-7b-instruct-v0.1", "claude-sonnet-4.6"
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
  filter(layer0 == "Non-compliance", layer1 == "Bare")

for (m in c("gpt-4o", "llama-3.1-8b", "llama-3.1-70b")) {
  cat("\n===", m, "=== unique bare responses (by frequency)\n")
  df |>
    filter(model == m) |>
    count(response, sort = TRUE) |>
    mutate(response = str_trunc(response, 160)) |>
    print(n = 30)
}
