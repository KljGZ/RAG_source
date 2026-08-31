# Data statement

## Data classes

- Synthetic controlled claims/documents for factorial identification.
- Frozen public-source snapshots for external validity, subject to terms and
  redistribution limits.
- Optional local checkouts of third-party benchmark data at pinned commits.
- Model outputs, tool traces, parse outcomes, costs, and human annotations.

## Provenance

Every snapshot is content-addressed with SHA-256 and linked to its source, collection
time, canonical URL, license/terms, and provenance root. Raw restricted data and
non-redistributable snapshots are ignored by Git; releases contain manifests or
derived statistics where permitted.

## Leakage prevention

Variants sharing a family, event, claim root, source-copy chain, or upstream event
cannot cross splits. Target-model output is not used as the sole gold label. Test
outcomes never change test examples or exclusions.

## Quality control

Schemas reject unknown fields and inconsistent authenticity/support relations.
Deterministic checks verify hashes, identifiers, spans, unique item IDs, acyclic
provenance, factor coverage, and split isolation. High-stakes real claims require
qualified review.
