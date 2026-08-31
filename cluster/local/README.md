# Single-node execution

The target node has no scheduler. Every project process is registered by exact
argument vector and PID creation time. The supervisor never discovers, kills, or
restarts arbitrary Python/GPU processes, so other users' jobs remain out of scope.

GPU workers remain disabled until an explicit resource allocation is recorded in a
run manifest.
