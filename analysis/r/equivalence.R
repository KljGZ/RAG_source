#!/usr/bin/env Rscript

suppressPackageStartupMessages({
  library(TOSTER)
  library(jsonlite)
})

args <- commandArgs(trailingOnly = TRUE)
if (length(args) != 5) {
  stop("usage: equivalence.R <estimate> <se> <df> <equivalence_bound> <output.json>")
}

estimate <- as.numeric(args[[1]])
se <- as.numeric(args[[2]])
degrees <- as.numeric(args[[3]])
bound <- as.numeric(args[[4]])

result <- TOSTmeta(
  ES = estimate,
  se = se,
  low_eqbound_d = -bound,
  high_eqbound_d = bound,
  alpha = 0.05
)
write_json(result, args[[5]], pretty = TRUE, auto_unbox = TRUE, digits = NA)
