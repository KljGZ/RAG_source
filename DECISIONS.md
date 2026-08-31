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
