#!/usr/bin/env Rscript

# CPU-only deployment test: fit the preregistered model to data generated with
# known positive normative effects. This is infrastructure evidence, not a study result.

suppressPackageStartupMessages({
  library(glmmTMB)
  library(jsonlite)
})

args <- commandArgs(trailingOnly = TRUE)
if (length(args) != 1) stop("usage: synthetic_recovery.R <output.json>")

set.seed(20260831)
family_count <- 120
variants_per_family <- 16
n <- family_count * variants_per_family

data <- data.frame(
  family_id = factor(rep(sprintf("family-%03d", seq_len(family_count)), each = variants_per_family)),
  model_id = factor(rep(sprintf("model-%02d", seq_len(6)), length.out = n)),
  source_id = factor(rep(sprintf("source-%02d", seq_len(24)), length.out = n)),
  reliability = runif(n, 0.1, 0.9),
  attribution_authentic = rbinom(n, 1, 0.5),
  warrant_score = sample(c(-1, 0, 0.15, 0.55, 1), n, replace = TRUE),
  authority_style = rbinom(n, 1, 0.5),
  popularity = rbinom(n, 1, 0.5),
  source_independence = rbinom(n, 1, 0.5),
  verification_completed = rbinom(n, 1, 0.5)
)

family_effect <- rnorm(family_count, 0, 0.35)
linear <- -1.0 +
  1.2 * data$reliability +
  0.8 * data$attribution_authentic +
  0.9 * data$warrant_score +
  0.15 * data$authority_style +
  0.1 * data$popularity +
  0.45 * data$source_independence +
  0.55 * data$verification_completed +
  family_effect[as.integer(data$family_id)]
data$claim_adopted <- rbinom(n, 1, plogis(linear))

formula <- claim_adopted ~ reliability + attribution_authentic + warrant_score +
  authority_style + popularity + source_independence + verification_completed +
  attribution_authentic:authority_style + reliability:popularity +
  source_independence:verification_completed +
  (1 | family_id) + (1 | model_id) + (1 | source_id)

model <- glmmTMB(formula, data = data, family = binomial(link = "logit"))
fixed <- fixef(model)$cond
required_positive <- c(
  "reliability", "attribution_authentic", "warrant_score",
  "source_independence", "verification_completed"
)
observed <- unname(fixed[required_positive])
names(observed) <- required_positive
converged <- isTRUE(model$sdr$pdHess)
direction_recovered <- all(observed > 0)

result <- list(
  schema_version = "1.0.0",
  purpose = "CPU-only synthetic GLMM deployment recovery; not empirical evidence",
  seed = 20260831,
  rows = n,
  families = family_count,
  converged_positive_definite_hessian = converged,
  required_positive_effects = as.list(observed),
  effect_directions_recovered = direction_recovered,
  passed = converged && direction_recovered
)
write_json(result, args[[1]], pretty = TRUE, auto_unbox = TRUE, digits = NA)
if (!result$passed) quit(status = 1)
