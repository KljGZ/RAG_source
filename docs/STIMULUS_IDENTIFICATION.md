# V0 static stimulus identification contract

## Why the earlier fractional scaffold was not executable science

The initial scaffold selected 16 level-balanced maximin cells and stored all factor
levels in trial metadata. Two defects made that unsuitable for a scientific run:

1. several registered factors did not change the model-visible prompt; and
2. maximin cells did not guarantee an exact control that held every other factor
   fixed, despite the registered matched-effect analysis.

No scientific output was generated under that scaffold. V0 now uses protocol
`audited_static_v1`, a deterministic 15-cell paired design. The change is a
pre-outcome identification correction, not a result-dependent redesign.

## Exact paired design

Each family contains one baseline and fourteen treated cells. Most cells compare
directly with the baseline. Two logically constrained effects use chain anchors:

- identity failure is compared with the authentic-identity/false-attribution cell,
  so attribution remains false in both cells;
- independent roots are compared with dependent copies, so both cells expose four
  pages and differ only in verified root count.

The two warrant contrasts (related-only and contradiction) share direct support as
their control. This yields 14 contrasts over 13 registered static factors. Completed
verification is intentionally absent from the static protocol and remains an action-
trace intervention in the interactive track.

## Model-visible channels

| Registered factor | Paired comparison | Only permitted visible path(s) |
|---|---|---|
| Claim-conditioned reliability | 0.2 vs 0.8 | `source_audit.claim_conditioned_reliability` |
| Attribution authenticity | failed vs passed | `source_audit.attribution_check` |
| Identity authenticity | failed vs passed, attribution fixed false | `source_audit.identity_check` |
| Evidence warrant | related/contradiction vs direct support | semantic content under `documents` |
| Raw source count | four dependent copies vs one page | `documents`, `provenance_audit.raw_supporting_pages` |
| Source independence | four roots vs one root, four pages fixed | `documents`, `provenance_audit.verified_independent_roots` |
| Authority style | formal vs plain surface | `documents` |
| Popularity | high vs low | `surface_cues.popularity` |
| Familiarity | high vs low | `surface_cues.familiarity` |
| Precision/detail | identifier/timestamp vs none | `documents` |
| User endorsement | true vs false | `surface_cues.user_endorsement` |
| Document position | first vs third | `documents` |
| Document length | 128 vs 64 controlled words | `documents` |

The audit recursively compares rendered JSON for every pair and fails if any extra
path changes, if a factor is invisible, if the prior changes within a family, or if
gold truth/answer or the actual publisher leaks into the prompt.

## Corpus and inferential boundary

The frozen corpus has 16 fictional closed-world families and 240 trials. The four
`gold_answer × candidate_answer` combinations and candidate-truth status are exactly
balanced. Components formed by family, event, and root claim are assigned wholly to
one split (8 train, 3 validation, 5 test families).

This static protocol measures whether a model uses supplied audited properties; it
does not show that the model autonomously discovered those properties. Autonomous
verification, attribution lookup, provenance tracing, and completed-verification
effects are evaluated separately with controlled tools. One model on this synthetic
corpus is exploratory and cannot establish a general SDI/PGSD conclusion.
