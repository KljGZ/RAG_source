# Model evaluation card

Each evaluated system records provider, exact model/revision, observation date,
temperature, token limit, prompts and hashes, tool policy, retry/parse history,
concurrency, and environment lock. Provider aliases are insufficient because hosted
models can change.

Target and primary judge must differ. Primary conclusions cannot depend on one LLM
judge: deterministic labels, structured parsing, expert/human samples, agreement
metrics, and sensitivity analysis are required. Parse failures, refusals, timeouts,
rate limits, and exhausted retries remain in denominators under the frozen policy.

The benchmark never requests or stores hidden chain-of-thought. `declared_factors`
is a compact observable report whose faithfulness is tested behaviorally.

V0 is exploratory. Before V1, hypotheses, primary endpoints, factor coding, exclusion
rules, mixed models, equivalence margins, multiplicity procedure, prompts, and model
versions are frozen and tagged.
