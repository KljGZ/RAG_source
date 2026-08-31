#!/usr/bin/env Rscript

suppressPackageStartupMessages({
  library(arrow)
  library(glmmTMB)
  library(jsonlite)
})

args <- commandArgs(trailingOnly = TRUE)
if (length(args) != 2) {
  stop("usage: primary_glmm.R <analysis.parquet> <output.rds>")
}

data <- read_parquet(args[[1]], as_data_frame = TRUE)
required <- c(
  "claim_adopted", "reliability", "attribution_authentic", "warrant_score",
  "authority_style", "popularity", "source_independence", "verification_completed",
  "family_id", "model_id", "source_id"
)
missing <- setdiff(required, names(data))
if (length(missing) > 0) {
  stop(paste("missing columns:", paste(missing, collapse = ", ")))
}

formula <- claim_adopted ~ reliability + attribution_authentic + warrant_score +
  authority_style + popularity + source_independence + verification_completed +
  attribution_authentic:authority_style + reliability:popularity +
  source_independence:verification_completed +
  (1 | family_id) + (1 | model_id) + (1 | source_id)

model <- glmmTMB(formula, data = data, family = binomial(link = "logit"))
saveRDS(model, args[[2]])
