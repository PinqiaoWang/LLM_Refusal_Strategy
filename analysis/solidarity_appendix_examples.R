library(tidyverse)

df <- read_csv("analysis/solidarity_sexual_violent_harms.csv", show_col_types = FALSE)

ex1 <- df |>
  filter(primary_llama_guard_category_name == "Violent Crimes",
         model == "claude-sonnet-3.7") |>
  filter(str_detect(query, "paralyze someone with a knife")) |>
  slice(1)

ex2 <- df |>
  filter(primary_llama_guard_category_name == "Child Sexual Exploitation",
         model == "claude-opus-4.6") |>
  filter(str_detect(query, "Telegram")) |>
  slice(1)

examples <- bind_rows(ex1, ex2) |>
  transmute(
    harm_category = primary_llama_guard_category_name,
    model,
    query,
    response = str_trim(response)
  )

write_csv(examples, "analysis/solidarity_appendix_examples.csv")

cat("=== LaTeX table rows ===\n\n")
for (i in seq_len(nrow(examples))) {
  cat("Row", i, "| Model:", examples$model[i], "| Harm:", examples$harm_category[i], "\n")
  cat("Query:   ", examples$query[i], "\n")
  cat("Response:", examples$response[i], "\n\n")
}
