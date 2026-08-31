# Threat model

## Assets and failures

The protected assets are factual answer integrity, calibrated uncertainty, genuine
attribution, traceable evidence, and accurate representation of source independence.
Failures include reliance on a spoofed publisher, false attribution to a genuine
publisher, evidence overreach, duplicated-source consensus laundering, fabricated
verification claims, and semantic RAG poisoning.

## Adversary capabilities

The isolated stress track may vary document wording, authority style, precise but
false identifiers, placement, repetition, provenance claims, semantic anchors, and
retrieval relevance. It may place authorized synthetic documents into the controlled
candidate pool. It may not modify public search results, third-party systems,
canonical external records, or unapproved corpora.

## Boundary

- All fabricated or poisoned content is stored in offline snapshots or served only
  on remote loopback.
- `robots.txt`, `X-Robots-Tag`, no-store headers, SSH forwarding, and URL audits are
  defense in depth; loopback binding is the primary boundary.
- The project does not perform SEO poisoning, public corpus injection, credential
  harvesting, impersonation through public domains, or unauthorized testing.
- MIRAGE adapters only read a safety manifest with `isolated`,
  `public_indexing_disabled`, and `authorized_corpus` all true.

## Non-goals

This benchmark is not a general malware framework, public misinformation generator,
or proof of model consciousness. It does not claim that one text-only detector can
establish factual truth without external evidence.
