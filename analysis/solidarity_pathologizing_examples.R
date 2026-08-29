library(tidyverse)

df <- read_csv("analysis/solidarity_sexual_violent_harms.csv", show_col_types = FALSE)

examples <- df |>
  filter(
    (primary_llama_guard_category_name == "Violent Crimes" &
       model == "claude-opus-3") |
    (primary_llama_guard_category_name == "Child Sexual Exploitation" &
       model == "claude-opus-3" &
       str_detect(query, "Telegram|lure"))
  ) |>
  slice_head(n = 1, by = primary_llama_guard_category_name) |>
  select(
    harm_category = primary_llama_guard_category_name,
    model,
    query,
    response
  ) |>
  arrange(harm_category)

write_csv(examples, "analysis/solidarity_pathologizing_examples.csv")
cat("Saved", nrow(examples), "examples to analysis/solidarity_pathologizing_examples.csv\n\n")

for (i in seq_len(nrow(examples))) {
  cat("=== Example", i, "| Harm:", examples$harm_category[i], "| Model:", examples$model[i], "===\n")
  cat("QUERY:", examples$query[i], "\n\n")
  cat("RESPONSE:", examples$response[i], "\n\n")
}
