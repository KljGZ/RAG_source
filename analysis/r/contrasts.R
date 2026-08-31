#!/usr/bin/env Rscript

suppressPackageStartupMessages({
  library(emmeans)
  library(jsonlite)
})

args <- commandArgs(trailingOnly = TRUE)
if (length(args) != 2) stop("usage: contrasts.R <model.rds> <output.json>")
model <- readRDS(args[[1]])

attribution <- contrast(
  emmeans(model, ~ attribution_authentic, type = "response"),
  method = "revpairwise",
  adjust = "holm"
)
warrant <- emtrends(model, ~ 1, var = "warrant_score")

result <- list(
  attribution = as.data.frame(confint(attribution)),
  warrant_trend = as.data.frame(confint(warrant)),
  multiplicity = "Holm"
)
write_json(result, args[[2]], pretty = TRUE, auto_unbox = TRUE, digits = NA)
