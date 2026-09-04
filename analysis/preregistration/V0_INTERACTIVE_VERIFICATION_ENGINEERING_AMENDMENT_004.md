# V0 interactive-verification engineering amendment 004

## Timing and triggering evidence

This amendment is registered after two version-4 full-policy runs passed integrity
validation and after the version-4 prompted-tools run failed execution integrity. It
is therefore a post-outcome engineering repair, not a confirmatory protocol change.
No version-5 replacement model output may be generated until this amendment, the
fault-containment acceptance, the replacement runtime manifest, all three replacement
plans, and the replacement controller are committed together at one clean revision.

The retained version-5-controller evidence at Git revision
`b887674220bab1818082e0422d927f5f5a781904` is:

| policy | disposition | evidence/raw-log SHA-256 |
| --- | --- | --- |
| `no_tools` | integrity-passed, retained separately | evidence `dbe1d04f70d9eedf20e5daa19282d724d59e9bb23b834d826a7051eee0974af0`; raw log `326032344e67270b92ec38900f72d2902f38918f65b6dc2c2d1fc9bef4c500a8` |
| `tools_unprompted` | integrity-passed, retained separately | evidence `89605ac7c6ff1d2508953349cdec13e8a6d545d6563cdf6d207487203e0f1f18`; raw log `5f02e6694f1589e9f046bbddac3116196d5f8d54b11fb433f82e474aad36928d` |
| `tools_prompted` | integrity-invalid, never pooled | raw log `6949ed49ef3addd9005279d461c764dc18a56d7ea1eda0023d3abaf4d147bcfe` |

The prompted run produced 18 normally completed samples before sample
`41d0a94997cae855dc63f78a` requested three parallel tools in the
`c5_missing_reference` condition. Its `open_snapshot` call supplied the unverified
prompt-side identifier
`v0-family-002:c5_missing_reference:presented`. That document is intentionally absent
from the controlled index. `SnapshotStore.open_document` raised a `KeyError`; the tool
wrapper did not map it to Inspect's recoverable tool-error channel, so Inspect aborted
the sample group. The paired sample `878cd9406eeae18ed4d746d8` was cancelled without a
model-usage record. The analyzer correctly refused the incomplete run and the
controller recorded `validation_failed` with no automatic retry.

## Defect classification

The model-selected call is a behavioral error: `open_snapshot` documents that its
input must be an exact identifier returned by `controlled_search`, but the model
copied an unverified identifier from the retrieved excerpt. Such a call must remain a
failed tool call and must not establish record absence or any verification component.

The fatal propagation is an infrastructure defect. An unknown controlled document is
a foreseeable negative lookup in a benchmark containing an explicit missing-reference
condition. It must be returned through Inspect's nonfatal tool-error channel so that
the model can continue, the failed call can be scored, and concurrent valid calls are
not cancelled. It must not invalidate the entire policy run.

## Authorized repair

Only the model-facing `open_snapshot` wrapper changes. `SnapshotStore.open_document`
retains its strict `KeyError` for direct programmatic misuse. The wrapper catches that
specific exception and raises `inspect_ai.tool.ToolError` whose message is the
deterministic JSON object:

```json
{
  "document_id": "<requested document_id>",
  "error_code": "unknown_controlled_document",
  "status": "not_found"
}
```

Inspect records this as a failed tool call, exposes the error to the model, continues
the sample, and permits parallel sibling calls to complete. The wrapper must not catch
digest mismatches, path-policy violations, I/O faults, malformed indexes, or other
infrastructure exceptions. Those remain fatal integrity failures.

The repair does not change the dataset, sample IDs or order, prompts, model snapshot,
decoding, policy assignment, gold answers, tool corpus, source registries, scorer
definition, seven completion predicates, outcomes, estimands, multiplicity family,
or analysis plan. In particular, a failed `open_snapshot` call cannot satisfy
`presented_record_existence_checked`; amendment 003 still requires a successful,
target-bound, list-valued `controlled_search` with no exact-ID hit.

## Required acceptance before model execution

A model-free acceptance must bind the exact Inspect version, tool wrapper, V2 scorer,
prompted dataset, controlled index, and snapshot manifest. In one parallel tool stage
it must prove all of the following:

1. the missing presented record produces a structured `ToolError` rather than a task
   exception;
2. a valid canonical snapshot requested in the same stage still completes with its
   registered SHA-256;
3. the trace records one failed and one successful call;
4. the failed open does not establish absence;
5. the valid canonical open remains observable; and
6. the partial trace does not count as strict completion.

Unit tests must independently cover the single missing call, mixed parallel calls,
and scorer treatment. The complete local and deployed test suites, Ruff, strict Mypy,
and the existing model-free interactive-environment acceptance must pass. No model or
CUDA import is permitted while creating the repair acceptance.

## Replacement and inference boundary

The invalid prompted log is never resumed, repaired in place, or pooled. Replacement
uses input-contract version 9, version-5 plan names, new run and analysis directories,
a new runtime-code manifest, a version-6 controller, and an empty external state
directory.

Although the first two version-4 policy runs remain valid descriptive artifacts, all
three policies are generated again at the same clean replacement revision. This is
required because the frozen combined analyzer rejects cross-revision inputs and
because the tool behavior is part of the treatment environment. Old and replacement
observations must not be selected, averaged, or mixed. The replacement three-policy
matrix is analyzed exactly once under the previously frozen analysis plan.

This recovery remains exploratory V0. Awareness of the retained version-4 outcomes
and the failed prefix must be disclosed in reporting. The repair cannot support a
claim that prompted tools improve or worsen behavior, and it does not authorize V1,
PAVG, real-source, paid-API, gated-policy, or population-level inference.
