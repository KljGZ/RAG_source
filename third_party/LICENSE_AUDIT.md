# Third-party license audit

Audit date: 2026-08-31. Repository heads are pinned in
`THIRD_PARTY_MANIFEST.yaml`; a moving default branch is never a reproducible
dependency.

| Resource | Detected license | Distribution decision |
|---|---|---|
| Inspect AI | MIT | install as a dependency |
| Learn2Discern | none detected | adapter only; do not copy or redistribute |
| GroupQA | none detected | design reference/local clone only |
| AuthorityBench | none detected | design reference/local clone only |
| RAGChecker | Apache-2.0 | optional package/adapter |
| ALCE | MIT | optional adapter |
| SourceCheckup | none detected | design reference/local clone only |
| BrowserGym | Apache-2.0 text | optional package/adapter |
| MIRAGE | none detected | local isolated adapter; no redistribution |

“None detected” is not a declaration that a work is free to use. It means the
repository API and root listing contained no explicit license at audit time. Data
terms, paper supplements, model terms, and website terms must be audited separately
before acquisition or publication.

No third-party source code is vendored in this repository.
