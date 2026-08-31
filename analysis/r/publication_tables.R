#!/usr/bin/env Rscript

suppressPackageStartupMessages({
  library(arrow)
  library(jsonlite)
})

args <- commandArgs(trailingOnly = TRUE)
if (length(args) != 2) stop("usage: publication_tables.R <effects.parquet> <output.csv>")
effects <- read_parquet(args[[1]], as_data_frame = TRUE)
required <- c("estimand", "estimate", "conf_low", "conf_high", "n_families")
missing <- setdiff(required, names(effects))
if (length(missing) > 0) stop(paste("missing columns:", paste(missing, collapse = ", ")))
write.csv(effects[required], args[[2]], row.names = FALSE, na = "NA")
