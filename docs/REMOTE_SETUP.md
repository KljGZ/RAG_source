# Remote setup

Machine-specific files use the `.local.*` naming convention and are excluded
from Git. Passwords and API tokens must never be written to these files.
The local profile uses an existing dedicated SSH key and has been verified with
`BatchMode=yes`; the supplied account password is not persisted.

Connect using the project-local SSH configuration:

```powershell
ssh -F configs/ssh/remote.local.conf provtrust-gpu
```

For controlled web experiments, keep services bound to remote loopback. The
`provtrust-gpu-tunnel` alias supplies all three forwards:

```powershell
ssh -F configs/ssh/remote.local.conf provtrust-gpu-tunnel
```

The default path mapping is:

| Purpose | Local | Remote |
|---|---|---|
| Repository | current workspace | `/home/REMOTE_USER/projects/RAG_source` |
| Data | untracked local cache | `/home/REMOTE_USER/provtrust_data` |
| Model cache | untracked local cache | `/home/REMOTE_USER/provtrust_cache` |
| Run outputs | downloaded on demand | `/home/REMOTE_USER/provtrust_runs` |

Remote outbound HTTPS is currently treated as unavailable. Download Hugging Face and
other external artifacts on an accessible machine, verify their declared size and
SHA-256, upload them, re-verify them remotely, and set
`HF_HUB_OFFLINE=1` plus an explicit local model path during the experiment.

The bootstrap script reads `configs/conda/mainland.yml` through `CONDARC`.
The checked-in profile uses the USTC conda-forge mirror because it provided the
best measured throughput from the target node. Override it without editing the
tracked file by setting `PROVTRUST_CONDARC` to another YAML configuration.

An IPv4-only resolver shim was sufficient during the initial bootstrap, but later
outbound HTTPS was unavailable altogether. The shim remains process-scoped and does
not modify host networking; it is not a substitute for the verified offline transfer
workflow.

## Web-service decision

V0 and V1 do not require a separate public server. The compute host can run the
controlled static/FastAPI source service, local search service, and Inspect log
viewer on loopback ports 18080, 18081, and 17500. Researchers reach them only
through the SSH forwards above. This keeps fabricated sources isolated and
prevents indexing. A separate CPU VM is justified only if a later stage needs a
persistent multi-user service or an explicitly approved external-validity study.
