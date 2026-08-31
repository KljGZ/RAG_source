# Decision log

## 2026-08-31 — Compute environment

- Use a user-owned Miniforge installation and a Conda environment named
  `provtrust` with Python 3.11.
- Keep GPU, browser, and formal R statistics dependencies as explicit layers.
- Treat the remote host as a single-machine executor because no scheduler or
  container runtime is installed.
- Keep controlled web services private and access them through SSH forwarding.
- Use the USTC conda-forge mirror and a bootstrap-scoped IPv4 resolver shim on
  this node; its sustained IPv6 HTTPS route stalls while IPv4 is healthy.
- Defer PyTorch/CUDA installation until a dedicated RTX PRO 6000 Blackwell
  compatibility probe. The API-oriented V0 base environment does not need it.
- Preserve the exact Linux solve and transfer package payloads from an
  internet-connected workstation when the compute node's outbound HTTPS is
  unavailable. Every payload must pass declared byte-size and SHA-256 checks on
  both sides.
- Install `clubSandwich` 0.7.0 from a hash-locked canonical CRAN source archive
  because the locked conda-forge index has no `r-clubsandwich` package. Keep all
  other formal statistics dependencies in the Conda transaction.
- Lock the BrowserGym 0.14.3 layer to Playwright 1.44, lxml 5.x, and
  Trafilatura 2.0.0. BrowserGym's declared upper bound on lxml and exact
  Playwright requirement conflict with the newest standalone versions, so these
  four packages are treated as one compatibility set.
- Install that BrowserGym compatibility set from Linux Python wheels. The
  Playwright 1.44 Conda build forces a Node/shared-library solve that downgrades
  Arrow 25 to 21 and conflicts with `r-arrow`; the Python wheel contains its own
  driver and leaves the Conda Arrow ABI unchanged.

## 2026-08-31 — Controlled webpages

- Do not provision a separate public server for V0/V1.
- Bind controlled source, search, and Inspect services to remote loopback and
  reach them through SSH forwarding.
- Consider a separate CPU VM only for persistent multi-user access or an
  explicitly approved external-validity stage.

## 2026-08-31 — Repository strategy

- Use `KljGZ/RAG_source` as the canonical GitHub repository.
- Version at auditable stage boundaries rather than after individual runs.
- Never commit passwords, API keys, model caches, generated poison documents,
  or unrestricted raw run outputs.
