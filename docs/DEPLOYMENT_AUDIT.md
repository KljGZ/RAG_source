# Theory-to-deployment audit

## 1. How the research claim evolved

The project did not begin with the claim that probabilistic models cannot
“understand sources.” That statement is too broad and is not falsifiable. The MIRAGE
case study instead exposed a narrower observation: once a professionally written,
apparently well-sourced false document enters a RAG candidate set, models may prefer
specificity, authority style, identifiers, or a fabricated citation chain over a real
source. Learn2Discern then showed that response changes after a source label are only
weakly aligned with external reliability and can be more aligned with source
popularity.

Those results motivate, but do not answer, the present question. A source label in a
prompt need not correspond to a real publication; a citation can be syntactically
valid but falsely attributed; ten pages can be copies of one root; and a model can say
“verified” without performing any verification. The project therefore advances from
source-label sensitivity to **Provenance-Grounded Source Discernment (PGSD)** and tests
the corresponding failure profile, **Source Discernment Illusion (SDI)**.

The falsifiable claim is:

> Observable trust should be causally controlled by verified claim-conditioned
> reliability, source identity, attribution authenticity, evidence warrant,
> provenance independence, and completed verification. Apparent source awareness is
> illusory to the extent that it is instead controlled by proxy cues or unsupported
> verbal assurances.

No implementation or analysis infers consciousness, hidden chain-of-thought, or a
privileged internal belief state.

## 2. Formal identification contract

For each counterfactual family, the underlying question, candidate, truth conditions,
gold answer, event, and root claim remain fixed. The normative vector is

\[
N=(R^\star,I,A,W,D,V),
\]

where the terms denote claim-conditioned reliability, identity authenticity,
attribution authenticity, evidence warrant, independent provenance, and completed
verification. The heuristic vector is

\[
H=(P,F,S,Q,O,L,U,C),
\]

covering popularity, familiarity, authority style, precision/detail, order, length,
user endorsement, and raw page count.

Each trial stores an explicit intervention vector. Exact matched contrasts hold all
other registered factors fixed, while the confirmatory model includes family, model,
and source grouping. Splits are assigned to connected components induced jointly by
`family_id`, `event_id`, and `root_claim_id`; no counterfactual family or event can
cross train/validation/test boundaries.

The operational outcome is observed through two model calls:

\[
q \rightarrow p_0,\qquad (q,d,s,tools) \rightarrow p_1.
\]

The first call sees no external evidence or verification tools. The second sees the
registered evidence and, for interactive tracks, only the controlled tools. Numeric
adoption is signed movement toward the candidate divided by the prior-candidate
distance and is never clipped. Categorical adoption is the posterior-minus-prior
candidate indicator. Self-reported confidence and declared factor weights remain
observable reports, not internal belief.

## 3. Implemented experimental tracks

1. **L2D replication.** A dedicated two-stage numeric solver records prior and
   posterior responses, absolute update, directed/normalized uptake, truth
   improvement, candidate advantage, reliability, popularity, and parse failures.
2. **Static causal decomposition.** The default V0 builder chooses 16 deterministic,
   level-balanced, maximin cells from the valid constrained factorial pool rather
   than evaluating an uncontrolled Cartesian explosion.
3. **Identity, attribution, and warrant.** Separate interventions and estimands avoid
   equating a genuine page, a genuine attribution, and actual support for the claim.
4. **Consensus laundering.** Provenance DAGs distinguish raw documents from verified
   roots. Duplicate pages are idempotent; independent roots remain separately
   countable.
5. **Interactive verification.** Search, snapshot opening, source resolution,
   identifier checking, and literal evidence-span tools are frozen, offline, and
   loopback/file-root constrained. A completion diagnostic requires canonical
   resolution, canonical snapshot access, and a nonempty evidence span; a sentence
   claiming verification is not sufficient.
6. **Rationale faithfulness.** Short declared factor weights are compared with matched
   counterfactual effects by sign agreement, rank correlation, and cosine alignment.
   Hidden chain-of-thought is neither requested nor stored.
7. **PAVG defense.** The implementation applies a risk gate, source/attribution
   checks, warrant mapping, verified-root aggregation, authority non-amplification,
   conflict detection, and calibrated abstention. The Inspect PAVG task exposes the
   same auditable protocol through controlled tools.
8. **MIRAGE stress.** The adapter accepts only an authorized, isolated, non-indexed
   manifest. It reports retrieval success, generation success conditional on
   retrieval, and their joint success separately. It does not create or publish
   poison documents.

Every track constructs successfully in the deployed Inspect environment without a
model call. This verifies wiring, not a scientific conclusion.

## 4. Engineering and reproducibility deployment

The repository is independent rather than a fork of MIRAGE, Learn2Discern, or
GroupQA. Inspect AI is an installed orchestration dependency; upstream repositories
are pinned adapters/design references and no-license projects are not copied. The
deployed stack contains:

- Python 3.11, Inspect AI, Pydantic schemas, Arrow/DuckDB/Polars, execution state,
  retries, sharding, cost ledger, and artifact hashing;
- R 4.5.3 with `glmmTMB`, `lme4`, `emmeans`, `clubSandwich`, `TOSTER`, `targets`, and
  Arrow, including the exact `glmmTMB 1.1.14` / `TMB 1.9.19` ABI pair;
- BrowserGym/Playwright with Chromium 125 and FFmpeg;
- Transformers/SentenceTransformers and a metadata-verified PyTorch 2.12.1+cu130 /
  CUDA 13 software layer;
- full Conda, pip, R, browser-archive, prompt, dataset-fixture, and JSON Schema hashes.

Because the mainland node currently lacks outbound HTTPS, packages are downloaded on
the local workstation, checked against authoritative size/hash metadata, uploaded,
and verified again. Model weights and licensed datasets will follow the same path.

## 5. Service, monitoring, and server decision

The controlled source and search services run on remote loopback ports 18080 and
18081. They emit `noindex`, `no-store`, CSP, and `robots.txt` isolation controls.
Playwright loaded the harmless fixture with `--disable-gpu`; no fabricated
real-world source has been deployed.

The supervisor manages only allowlisted commands. PID reuse and shebang execution are
handled by checking process creation time, the observed executable/command line, the
current configured command, and the working directory. It also checks free disk, Git
cleanliness, and environment-lock hashes, rate-limits restarts, and refuses to act if
identity changes.

No separate public server is needed for V0/V1. SSH forwarding provides researcher
access. A separate CPU VM is justified only for later persistent multi-user access or
an explicitly approved external-validity study.

## 6. Acceptance evidence and remaining gates

The no-GPU acceptance report passed package versions, locks, browser binaries,
services, `pip check`, and offline `uv lock`; it records that Torch was not imported,
no CUDA context was created, and no model/API/experiment was invoked. Ruff, strict
Mypy, and 42 Pytest tests pass. A CPU-only 1,920-row GLMM simulation converged with a
positive-definite Hessian and recovered all five predeclared positive directions.

The following cannot be honestly marked complete before execution inputs exist:

- licensed upstream datasets and real-source snapshots;
- human/deterministically validated V0 gold claim families;
- additional target/judge model revisions and judge independence validation;
- any paid provider access and a hard API budget (currently zero and disabled);
- V0 outcomes, human agreement, and V1 preregistration freeze.

The first target Qwen3-14B revision, physical GPU 2, CPU affinity, storage allocation,
and zero-API policy are now frozen for the compatibility pilot. The remaining items
are enforced gates; no positive SDI or PAVG result is assumed in advance.
