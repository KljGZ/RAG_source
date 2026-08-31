# Formal research specification

## Scope and falsifiability

ProvenanceTrustBench does not infer whether a model is conscious or possesses a
privileged form of “understanding.” It tests a narrower, falsifiable capability:

> Is observable trust behavior causally controlled by verified source identity,
> attribution, claim-conditioned reliability, evidence permission, provenance
> independence, and completed verification—or mainly by proxy cues?

Accordingly:

\[
\text{source sensitivity}\ne\text{source preference}\ne
\text{source discernment}\ne\text{source verification}.
\]

The target capability is **Provenance-Grounded Source Discernment (PGSD)**. The
failure mode is **Source Discernment Illusion (SDI)**: behavior appears source-aware
or verified to an observer while causal interventions show weak control by verified
source properties/actions, excessive control by proxy cues, or unsupported
verification assurances.

## Formal objects

Let \(w\) be the relevant world state at time \(t\), \(c\) an atomic claim, \(q\) a
query, \(d\) a document, \(s_a\) its actual publisher, and \(s_d\) its displayed or
attributed publisher. A trial belongs to a counterfactual family \(f\); all variants
in \(f\) share the same underlying claim, question, truth conditions, and controlled
content except for declared interventions.

The six normative variables are:

1. **Claim-conditioned reliability**

   \[
   R^\star(s,c,t)=P(c\text{ is correct}\mid s,\operatorname{domain}(c),t,\operatorname{role}(s,c)).
   \]

   Global source reputation is not a substitute for \(R^\star\). A regulator may be
   authoritative for its own ruling and irrelevant to an unrelated scientific claim.

2. **Identity authenticity**

   \[
   I(d,s)=\mathbf 1[d\text{ was actually published by }s].
   \]

3. **Attribution authenticity**

   \[
   A(d,c,s)=\mathbf 1[\text{the canonical record of }s\text{ actually asserts }c].
   \]

   A genuine secondary page can falsely attribute a claim to a genuine authority;
   therefore identity and attribution are separate variables.

4. **Evidence warrant/permission**

   \[
   W(d,c)\in\{-1,0,0.15,0.55,1\},
   \]

   corresponding to contradiction, unsupported, related-only, partial support, and
   direct support. The ordinal relation—not these development weights—is primary.

5. **Source independence**

   Documents map to provenance roots \(g(d)\). The effective evidence count is the
   number of independent verified roots, not the number of pages:

   \[
   N_{\mathrm{eff}}(c)=|\{g(d):d\text{ provides admissible evidence for }c\}|.
   \]

6. **Completed verification**

   \[
   V=\mathbf 1[\text{a trace resolves identity, opens a canonical record, checks
   attribution/identifier, and stores an evidence span}].
   \]

   A phrase such as “I verified this” is not a verification action.

Proxy or heuristic variables \(H\) are modeled separately: familiarity,
popularity, authority style, precise numbers or identifiers, document length,
position, user endorsement, and raw repetition count.

## Operational belief update

The benchmark does not assume access to a hidden mental state. It records an
operational prior answer \(p_0\), posterior answer \(p_1\), and candidate \(z\). For
numeric tasks, movement toward the candidate is:

\[
U(p_0,p_1,z)=\operatorname{sign}(z-p_0)(p_1-p_0),
\]

and, when \(z\ne p_0\), normalized adoption is:

\[
U_N=\frac{U}{|z-p_0|}.
\]

Values are not clipped: resistance is negative and overshooting exceeds one. For
categorical tasks, claim adoption, calibrated probability, or an explicitly parsed
choice is used. Model self-reported confidence is retained as an observable report,
not equated with internal belief.

## Normative aggregation

For verified root \(g\), the development defense uses:

\[
w_g(c)=\hat I_g\hat A_g\hat W_g\hat R_g(c)\hat D_g,
\]

where \(\hat D_g\) is the independence contribution. Multiple documents under one
root are idempotent; the strongest admissible contribution is retained rather than
summed. Unknown authenticity is not silently set to one.

The authority non-amplification constraint is:

\[
R_{\mathrm{eff}}(d,c)\le
\max_{r\in\operatorname{verifiedRoots}(d,c)} R^\star(r,c).
\]

A secondary page that merely writes “according to an authority” cannot inherit that
authority unless the attribution edge is verified.

## Eight normative axioms

1. **Reliability monotonicity:** holding other variables fixed, higher verified
   \(R^\star\) must not decrease adoption of a supported true claim.
2. **Attribution monotonicity:** authentic attribution must not receive less weight
   than a matched false attribution.
3. **Warrant monotonicity:** direct support must dominate related-only or unsupported
   content; contradiction must not be treated as support.
4. **Duplicate idempotence:** copying/paraphrasing one root must not create the same
   gain as adding independent corroboration.
5. **Risk-responsive verification:** verification probability/completion must rise
   with conflict, stakes, unfamiliarity, anomalies, dependence, or prior conflict.
6. **Authority non-amplification:** unverified citation chains cannot increase the
   effective authority above their verified roots.
7. **Rationale faithfulness:** declared factor importance must predict the sign and
   ranking of matched counterfactual behavioral effects.
8. **Calibrated abstention:** unresolved high-risk conflict or incomplete required
   verification must reduce confidence or induce abstention.

## Identifiability propositions

1. A single output cannot identify source understanding: the same answer may arise
   from evidence use, memorized associations, label familiarity, or imitation.
2. Without an external observation channel, attribution authenticity is in general
   unidentifiable from surface text alone; tools or frozen canonical records are
   therefore part of the construct, not optional decoration.
3. Treating dependent documents as independent causes consensus laundering because
   apparent support can grow with copy count while information does not.
4. Self-explanation cannot establish causal faithfulness; matched interventions are
   required because many rationales are behaviorally equivalent on the observed
   sample.

## Research questions and tests

- **RQ1:** Are updates controlled by verified claim-conditioned reliability after
  popularity/familiarity are orthogonalized?
- **RQ2:** Do identity and attribution authenticity have distinct causal effects?
- **RQ3:** Is adoption monotone in evidence warrant?
- **RQ4:** Does raw repetition create consensus laundering beyond root count?
- **RQ5:** Do models trigger and complete verification under risk?
- **RQ6:** Do declared trust factors predict counterfactual effects?
- **RQ7:** Does PAVG improve normative control and calibrated abstention at bounded
  cost?
- **RQ8:** Does PAVG reduce MIRAGE joint attack success in isolation?

The primary metrics are claim-adoption shift, attribution-authenticity gap, warrant
monotonicity violation rate, consensus-laundering amplification, independent-evidence
gain, verification trigger/completion rates, false-verification assurance rate,
rationale causal consistency, normative-factor control ratio, calibration, and
abstention. MIRAGE reporting distinguishes:

\[
P(\mathrm{retrieved}),\quad
P(\mathrm{generation\ success}\mid\mathrm{retrieved}),\quad
P(\mathrm{retrieved}\cap\mathrm{generation\ success}).
\]

## SDI reporting

SDI is not declared from one arbitrary threshold. The paper must report a profile:

- non-trivial label/proxy sensitivity;
- causal effects and intervals for all normative variables;
- normative-factor control ratio versus heuristic control;
- verification completion and unsupported assurance;
- rationale-counterfactual consistency;
- model/task heterogeneity.

Any binary diagnostic threshold is calibrated on development data, frozen before V1,
and accompanied by the continuous components. Null results and violations in the
opposite direction remain in the report.

## PAVG stages

PAVG atomizes answer claims, resolves source entities, verifies attribution, checks
evidence permission, constructs a dependency graph, applies a risk gate, aggregates
by independent verified roots under non-amplification, and returns an answer,
conflict report, or abstention. It is evaluated against no-verification and
always-verify baselines for accuracy, calibration, latency, token use, tool calls,
and failure modes.
