# M3.6 Risk - Plan

## Objective

Plan the `C-6 Risk` Analyst slice as a full M3.6 implementation target, without implementing it in this docs-only step.

M3.6 must produce an evidence-backed Risk & Kill Sheet draft that states how the thesis loses money, writes the bear case as a credible skeptic would, separates modellable risks from tail risks, carries a sourced bear-case value, and defines a falsifiable kill metric. Every judgment remains an Analyst draft that requires Senior ratification. The Senior does not decide in M3.6.

## Scope

In scope for the future implementation:

- A `C-6 Risk` Analyst bundle under `skills/research/risk/`.
- Deterministic offline drafting from existing filed artifacts and frozen fixtures.
- A schema-valid Risk & Kill Sheet artifact with:
  - pre-mortem;
  - short-seller bear-case narrative;
  - modellable risk register with impact and likelihood;
  - separate non-empty tail-risk bucket;
  - bear-case value as a provenance-complete `Number`;
  - kill metric with metric, threshold, observation window, and action implication;
  - ratifiable risk-completeness draft.
- Reuse of M3.1 `AnalystDraft`, `EvidenceRef`, evidence audit, no-bare-number audit, ratifiable collection, and Analyst bundle validation.
- Reuse of M3.3 period-consistency audit for evidence refs.
- Reuse of completed Business, Moat, CapAlloc, Scenarios, Edge & Cruxes, Gate Card, Method Directive, Expectations Line, Valuation Range, and Spine artifacts as evidence sources.
- Audit-enforced brakes for empty tail risks, blended risk buckets, unsupported bear narratives, missing bear-case value provenance, malformed kill metrics, unbound evidence, and prompt-only enforcement.
- Resolver GO-branch wiring after Edge & Cruxes.
- Offline tests proving artifact shape, audit failures, stable review item collection, and resolver behavior.

Out of scope:

- M3.7 consolidated `Senior.ratify`.
- Final Handoff synthesis.
- Sizing inputs.
- Calibration analytics.
- Live LLM drafting.
- New valuation methods, valuation engines, primitive types, storage interfaces, or external dependencies.
- A second Senior gate or any new Senior touchpoint.

## Dependencies And Invariants

M3.6 depends on completed M2b and M3.1 through M3.5:

- `GateCard`, `MethodDirective`, `ValuationRange`, `ExpectationsLine`, and `Spine`.
- Business, Moat, CapAlloc, Scenario, and Edge & Cruxes Analyst artifacts.
- `AnalystDraft`, `EvidenceRef`, `ReviewItem`, `SeniorReviewPackage`, and `collect_ratifiables`.
- M3.1 evidence and no-bare-number audits.
- M3.3 period-consistency audit.
- M3.1 Analyst bundle validation.

Standing invariants:

1. Analysts draft, flag, and attach evidence; they do not decide.
2. The Senior is not called in M3.6.
3. Every ratifiable judgment remains undecided before M3.7.
4. Brakes are audit-enforced, not prompt-enforced.
5. Tail risks must be separate from modellable impact-times-likelihood risks.
6. Tail risks must be non-empty.
7. Bear-case value must be a `Number` with provenance and derivation.
8. Kill metric must be specific, falsifiable, and tied to the thesis.
9. No bare numeric values may cross skill boundaries.
10. A KILL gate upstream still halts as before; M3.6 does not revive killed names.

## Proposed Architecture

```text
analyze(ticker)
   |- existing M1/M2 path
   |- C-1 Business and early GO/NO-GO gate
   |- if GO:
   |    |- C-2 Moat
   |    |- C-3 CapAlloc
   |    |- B-4 Gate Card
   |    |- B-6 Method Directive
   |    |- B-3 ValuationRange + ExpectationsLine when method == DCF
   |    |- C-4 Scenarios
   |    |- C-5 Edge & Cruxes
   |    `- C-6 Risk
   |         |- reads filed mechanical and Analyst artifacts
   |         |- emits ratifiable pre-mortem, bear narrative, risk completeness, and kill-thesis drafts
   |         |- emits provenance-complete bear-case value
   |         |- verifies modellable and tail buckets are distinct
   |         |- verifies kill metric is structurally falsifiable
   |         `- collects review items without Senior ratification
   `- if NO-GO: unchanged stop behavior
```

## Skill Bundle To Be Created In Implementation

The bundle is an Analyst bundle (`no_llm: false`):

```text
skills/research/risk/
|-- SKILL.md
|-- risk.py
|-- test_risk.py
|-- prompt.md
|-- resolver.entry
`-- eval/
    |-- cases.jsonl
    `-- eval_risk.py
```

`test_integration.py` is not required because M3.6 is offline. Tests may live in the bundle and/or under `tests/`, matching the M3.2 through M3.5 pattern.

## Artifact Shape

M3.6 should define the narrowest local artifact needed to represent the filing-rules `RiskKillSheet` contract while staying compatible with M3.1 Analyst drafts.

Expected shape:

```text
RiskArtifact
|-- header
|-- ticker
|-- as_of
|-- source_artifact_paths
|-- premortem: AnalystDraft
|-- bear_case_narrative: AnalystDraft
|-- modellable_risks: AnalystDraft containing ModellableRiskDraft records
|-- tail_risks: AnalystDraft containing TailRiskDraft records
|-- bear_case_value: Number
|-- kill_metric: AnalystDraft containing KillMetricDraft
|-- risk_completeness: AnalystDraft
`-- source_evidence_summary

ModellableRiskDraft
|-- risk
|-- impact: "low" | "med" | "high"
|-- likelihood: "low" | "med" | "high"
|-- modeled_effect
|-- evidence_refs

TailRiskDraft
|-- risk
|-- why_not_modelled
|-- monitoring_signal
|-- evidence_refs

KillMetricDraft
|-- metric
|-- threshold_direction
|-- threshold_value
|-- observation_window
|-- thesis_action
|-- evidence_refs
```

Each `AnalystDraft` must:

- carry non-empty resolvable evidence refs;
- include a Senior checklist area and rationale;
- remain `needs_ratification`;
- have no `decision`, `decided_by`, or `final` before M3.7;
- avoid bare numeric payloads where a `Number` is required.

## Audit Brakes

M3.6 must add deterministic audit behavior for risk artifacts. Required brakes:

1. Evidence support. Existing M3.1 evidence checks apply to every draft.
2. Period consistency. Existing M3.3 period checks apply to every period-specific claim.
3. Pre-mortem quality. Empty, placeholder, purely bullish, or non-loss narratives fail.
4. Bear-case quality. The bear case must be a credible short-seller narrative, not a generic downside list.
5. Two-bucket separation. Modellable and tail risks must be separate fields and cannot contain the same risk.
6. Modellable risk structure. Every modellable risk must include risk, impact, likelihood, modeled effect, and evidence.
7. Tail-risk structure. Tail risks must be non-empty and must include why the risk is not responsibly modelled.
8. Bear-case value. The value must be a `Number`, must be finite, must use compatible units, and must trace to scenario or valuation inputs.
9. Kill metric. The kill metric must include metric, threshold direction, threshold value, observation window, and thesis action.
10. No keyword falsifiability. Audit must not accept kill metrics because prose contains words such as "if" or "below"; typed fields are the guarantee.
11. Source binding. Risk claims must cite filed artifacts, filing refs, external refs, or explicit missing-data gaps.
12. Review collection. The artifact must collect into stable `ReviewItem`s without calling `Senior.ratify`.
13. Prompt independence. Audit failures must occur regardless of `prompt.md` contents.

## Implementation Steps

1. Fill `skills/research/risk/SKILL.md` from `specs/SKILL-template.md`.
2. Add the Analyst bundle file set: implementation, prompt, eval cases, eval runner, and resolver entry.
3. Define `RiskArtifact`, `ModellableRiskDraft`, `TailRiskDraft`, and `KillMetricDraft` using existing M3.1 models.
4. Build deterministic fixture-backed drafting from filed Business, Moat, CapAlloc, Scenarios, Edge & Cruxes, Gate Card, Method Directive, and valuation artifacts.
5. Add fixtures sufficient to support a valid AAPL risk sheet.
6. Derive bear-case value from the existing bear scenario or valuation artifact using a provenance-complete `Number`.
7. Add audit checks for pre-mortem, bear narrative, two-bucket separation, modellable risks, tail risks, bear-case value, and kill metric structure.
8. Prove missing tail risks fail closed.
9. Prove blended or duplicate risks across buckets fail closed.
10. Prove unsupported bear-case narratives fail closed.
11. Prove kill metrics missing metric, threshold direction, threshold value, observation window, or thesis action fail closed.
12. Prove `collect_ratifiables` emits stable review items for Risk drafts.
13. Wire the resolver GO branch after Edge & Cruxes to file and collect Risk without calling `Senior.ratify`.
14. Keep all tests offline, deterministic, and no-network.

## Risks And Decisions

- The highest-risk issue is letting a generic risk list substitute for a real bear thesis. M3.6 must force the Analyst to state how money is lost.
- Tail risks are intentionally not scored with likelihood. Mixing them into the matrix defeats the runbook's matrix fix.
- Bear-case value must be numeric and auditable, but the story behind it is judgment and remains ratifiable.
- Kill metrics must be structurally checkable. Prose can explain the line, but cannot substitute for metric, direction, threshold, and observation window.
- M3.6 should not create a final action such as exit or sell. It only drafts what would end the thesis for Senior ratification.
- If existing M3.1 collection cannot represent the chosen draft granularity, implementation must stop and flag the contract gap rather than creating a parallel ratification path.

## Expected Result

After future M3.6 implementation, offline `analyze("AAPL")` with the existing fake Senior/LLM seams can:

- produce a filed, evidence-backed Risk & Kill Sheet artifact;
- collect risk drafts as undecided review items;
- reject empty or upside-only pre-mortems;
- reject generic or unsupported bear-case narratives;
- reject missing, empty, or blended tail-risk buckets;
- reject modellable risks without impact, likelihood, modeled effect, or evidence;
- reject bear-case values that are bare numerics or lack provenance;
- reject kill metrics missing falsifiable typed fields;
- preserve the two-Senior-touchpoint architecture by adding no Senior call in M3.6.

## Pre-Implementation Self-Review

- Scope is limited to `C-6 Risk`.
- The plan reuses M3.1 through M3.5 infrastructure.
- The plan does not add M3.7 ratification, final Handoff synthesis, sizing, or calibration.
- The plan does not add new primitives, storage abstractions, valuation engines, or dependencies.
- All brakes are deterministic and prompt-independent.
- Tail risks remain separate from modellable risks.
- Kill-metric falsifiability is field-based, not keyword-based.
- The plan keeps every Analyst judgment ratifiable and undecided.
