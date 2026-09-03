# V0 interactive-verification engineering amendment 003

## Triggering evidence and scope

This amendment is frozen after the V0 publication audit and before any Track E
full-run response is generated. The audit was performed at Git revision
`218aaa4d10423a9f9349c8ae5817d3e4a6d46ad2` after all three version-3
engineering preflights had completed. The
full-run controller had passed no plan and had produced no `.eval` log. Therefore
this correction cannot be informed by a formal-run outcome.

The retained version-3 preflight evidence is:

| policy | evidence SHA-256 | raw log SHA-256 | old strict completions |
| --- | --- | --- | ---: |
| `no_tools` | `4cfc079236c6c5c22e10caab8948b6bbce427f0602030bdceb704dd4c49fd872` | `ba1e9f8069f245b5fe835ade96c6aa49ac16339c9556789b06ac249ff1006282` | 0/10 |
| `tools_unprompted` | `d1b54b93a9f3fa54bce7287e40ee2e5713b3cc388903ef6a30551ece87936bbc` | `5451a71fb3cc4c687127766dddadea1596fb4ef4f059549dd05288ea03400891` | 0/10 |
| `tools_prompted` | `114898ca84249b84820c07b29da626f9c28d1f92e610010b44fb6ee2d012249a` | `2f83447b5a37230bfb01e18d7873e678b79c23b6cb7a47e444e1a3616be1fd63` | 0/10 |

The frozen version-1 trace scorer had SHA-256
`a2732707d461297d15faf3649130c5f7577034237d3df55d31ecee309ad1775a`
and emitted definition ID `trial_specific_interactive_v1`.

## Defect

For each trial, version 1 collected all identifiers returned by successful
`controlled_search` calls and evaluated the presented-record component as:

```text
(presented_document_id was returned) is page_exists
```

For `c5_missing_reference`, `page_exists` is false. Consequently, an empty trace
made both sides false and incorrectly passed
`presented_record_existence_checked`. This is a vacuous-truth implementation
error: absence of an observation was treated as an observation of absence. It
affected 2/10 rows in both zero-call policies. It did not change their old strict
completion counts because other required components were false, but it could bias
component estimates and could permit a future false strict completion.

## Authorized semantic correction

The trace definition is advanced to `trial_specific_interactive_v2`. For a
presented record that exists, the component passes only if a successful,
JSON-list-valued `controlled_search` result contains its exact `document_id`. For
a presented record that is absent, it passes only if:

1. at least one successful, JSON-list-valued `controlled_search` call has a query
   that explicitly contains the trial's presented `document_id`, case-insensitively;
2. every such target-bound result omits that exact identifier.

No search, a failed search, an invalid/non-list result, or an unrelated search
must fail the component. This amendment does not change the prompt, trial set,
model, tool implementation, gold record, treatment, outcome threshold, or any
other verification component.

## Required model-free acceptance and immutable rescore

Before a replacement full plan may become executable, deterministic tests must
cover at least: no call, unrelated empty search, successful target-bound empty
search, failed target-bound search, and the existing-record positive case. A
content-hashed acceptance artifact must bind the corrected scorer and these gates.

All three retained version-3 raw logs must then be rescored without a model call.
The rescore must verify each raw-log hash, retain both old recorded and new
recomputed component vectors, enumerate every changed field by sample ID, and
show that trigger/tool-call counts are invariant. It must fail closed on sample
loss, duplicate IDs, raw-log drift, unexpected old definition, or any change
outside fields derived from trace completion. Original `.eval` logs and version-3
acceptance artifacts remain immutable and must not be overwritten.

## Replacement, freezing, and interpretation

Replacement full plans use a new plan version, input-contract version, runtime
code manifest, output directory, controller state directory, and Git revision.
They bind this amendment, the scorer acceptance, and the policy-specific rescore
artifact. All three policies must use the same corrected scorer revision.

The ten-row logs remain engineering preflights and are not pooled into the
160-row exploratory V0 estimates. Rescoring corrects an observability predicate;
it does not retroactively turn a preflight into scientific evidence. Behavioral
values remain non-gating. V1, PAVG, API-model, real-source, and confirmatory claims
remain unauthorized.
