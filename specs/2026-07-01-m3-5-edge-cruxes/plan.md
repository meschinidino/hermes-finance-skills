# M3.5 Edge & Cruxes - Plan

## Objective

Build the `C-5 Edge & Cruxes` Analyst slice as an offline, fixture-backed planning and implementation target.

M3.5 must produce an evidence-backed Edge Statement draft that explains why the opportunity may exist, who is plausibly on the other side, why a no-trade decision may still be correct, what could change the market's view, and exactly three falsifiable cruxes. Every judgment remains a ratifiable Analyst draft. The Senior does not decide in M3.5.

## Scope

In scope:

- A `C-5 Edge & Cruxes` Analyst bundle under `skills/research/edge_cruxes/`.
- Deterministic offline drafting from existing filed artifacts and frozen fixtures.
- A schema-valid Edge Statement artifact with:
  - no-trade steelman;
  - non-trivial counterparty;
  - structural mispricing mechanism or explicit no-structural-edge/pass framing;
  - variant view or explicit fairly-priced/pass framing;
  - catalysts;
  - exactly three field-falsifiable edge cruxes when an edge is asserted;
  - zero-or-more field-falsifiable pass-falsifiers when no structural edge exists.
- Reuse of M3.1 `AnalystDraft`, `EvidenceRef`, evidence audit, no-bare-number audit, ratifiable collection, and Analyst bundle validation.
- Reuse of M3.3 period-consistency audit for evidence refs.
- Reuse of completed Business, Moat, CapAlloc, Scenarios, Gate Card, Method Directive, Expectations Line, Valuation Range, and Spine artifacts as evidence sources.
- Audit-enforced brakes for trivial counterparties, missing steelman, unsupported structural mispricing, malformed cruxes, missing catalysts, unbound evidence, unsupported variant view, and prompt-only enforcement.
- Resolver GO-branch wiring after Scenarios.
- Offline tests proving artifact shape, audit failures, stable review item collection, and resolver behavior.

Out of scope:

- `C-6 Risk`.
- M3.7 consolidated `Senior.ratify`.
- A second Senior gate or any new Senior touchpoint.
- Live LLM drafting.
- New valuation methods, valuation engines, primitive types, storage interfaces, or external dependencies.
- Risk kill sheet, bear-case value, kill metric, final Handoff synthesis, calibration analytics, or portfolio sizing.

## Dependencies And Invariants

M3.5 depends on completed M2b and M3.1 through M3.4:

- `GateCard`, `MethodDirective`, `ValuationRange`, `ExpectationsLine`, and `Spine`.
- Business, Moat, CapAlloc, and Scenario Analyst artifacts.
- `AnalystDraft`, `EvidenceRef`, `ReviewItem`, `SeniorReviewPackage`, and `collect_ratifiables`.
- M3.1 evidence and no-bare-number audits.
- M3.3 period-consistency audit.
- M3.1 Analyst bundle validation.

Standing invariants:

1. Analysts draft, flag, and attach evidence; they do not decide.
2. The Senior is not called in M3.5.
3. Every ratifiable judgment remains undecided before M3.7.
4. Brakes are audit-enforced, not prompt-enforced.
5. The counterparty cannot be trivial, empty, or contemptuous.
6. Structural mispricing must either name an evidence-backed mechanism and persistence reason, or explicitly say no durable structural edge exists.
7. The crux list must contain exactly three measurable, falsifiable `edge_crux` records when structural mispricing asserts an edge.
8. No-edge/pass framing may file zero-or-more `pass_falsifier` records; zero is valid, but every filed pass-falsifier must be structurally checkable.
9. Crux falsifiability is structural: each filed crux carries kind, metric, threshold direction, threshold value, and check-by date as populated typed fields.
9. Cruxes must bind to available artifacts, observable future evidence, or explicit missing-data gaps.
10. A no-trade steelman is mandatory even when the draft leans toward a variant view.

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
   |    `- C-5 Edge & Cruxes
   |         |- reads filed mechanical and Analyst artifacts
   |         |- emits ratifiable steelman, counterparty, structural mispricing, variant view, catalysts, and cruxes
   |         |- verifies exactly three field-falsifiable cruxes
   |         |- verifies non-trivial counterparty and no-trade steelman
   |         `- collects review items without Senior ratification
   `- if NO-GO: unchanged stop behavior
```

## Skill Bundle Created In M3.5

The bundle is an Analyst bundle (`no_llm: false`):

```text
skills/research/edge_cruxes/
|-- SKILL.md
|-- edge_cruxes.py
|-- prompt.md
|-- resolver.entry
`-- eval/
    |-- cases.jsonl
    `-- eval_edge_cruxes.py
```

`test_integration.py` is not required because M3.5 is offline. Tests may live in the bundle and/or under `tests/`, matching the M3.2 through M3.4 pattern.

## Artifact Shape

M3.5 should define the narrowest local artifact needed to represent the filing-rules `EdgeStatement` contract while staying compatible with M3.1 Analyst drafts.

Expected shape:

```text
EdgeCruxesArtifact
|-- header
|-- ticker
|-- as_of
|-- source_artifact_paths
|-- steelman_no_trade: AnalystDraft
|-- counterparty: AnalystDraft
|-- structural_mispricing: AnalystDraft
|-- variant_view: AnalystDraft
|-- catalysts: AnalystDraft
|-- cruxes: AnalystDraft containing CruxDraft records, or None for no-edge/pass with no pass-falsifiers
`-- source_evidence_summary

CruxDraft
|-- claim
|-- kind: "edge_crux" | "pass_falsifier"
|-- metric
|-- threshold_direction
|-- threshold_value
|-- check_by
|-- evidence_refs
```

Each `AnalystDraft` must:

- carry non-empty resolvable evidence refs;
- include a Senior checklist area and rationale;
- remain `needs_ratification`;
- have no `decision`, `decided_by`, or `final` before M3.7;
- avoid bare numeric payloads where a `Number` is required.

## Audit Brakes

M3.5 must add deterministic audit behavior for edge and crux artifacts. Required brakes:

1. Evidence support. Existing M3.1 evidence checks apply to every draft.
2. Period consistency. Existing M3.3 period checks apply to every period-specific claim.
3. No-trade steelman. Empty, placeholder, or purely bullish steelman drafts fail.
4. Counterparty quality. Empty, trivial, circular, or contemptuous counterparties fail.
5. Structural mispricing. A draft that asserts edge must name both an evidence-backed mispricing mechanism and an evidence-backed persistence reason. A draft may instead explicitly state no structural edge/pass.
6. Variant view support. A variant view must cite evidence or explicitly state fairly priced/pass.
7. Catalyst usefulness. Catalysts must be concrete events or evidence releases, not generic "market realizes value" language.
8. Edge crux count. Edge-asserted artifacts require exactly three `edge_crux` records; more or fewer fail.
9. No-edge pass-falsifiers. No-edge/pass artifacts allow zero-or-more `pass_falsifier` records and reject any `edge_crux`.
10. Crux falsifiability. Each filed crux must carry kind, metric, threshold direction, threshold value, and check-by date as populated typed fields.
10. No keyword falsifiability. Audit must not rely on keyword-matching crux prose; the typed fields are the falsifiability guarantee.
11. Source binding. Cruxes and edge claims must cite filed artifacts, external refs, or explicit missing-data gaps.
12. Review collection. The artifact must collect into stable `ReviewItem`s without calling `Senior.ratify`.
13. Prompt independence. Audit failures must occur regardless of `prompt.md` contents.

## Implementation Steps

1. Fill `skills/research/edge_cruxes/SKILL.md` from `specs/SKILL-template.md`.
2. Add the Analyst bundle file set: implementation, prompt, eval cases, eval runner, and resolver entry.
3. Define `EdgeCruxesArtifact` and `CruxDraft` using existing M3.1 models.
4. Build deterministic fixture-backed drafting from filed Business, Moat, CapAlloc, Scenarios, Gate Card, Method Directive, and valuation artifacts.
5. Add fixtures sufficient to support a valid AAPL edge and three cruxes.
6. Add audit checks for steelman, counterparty, structural mispricing, catalysts, variant view, and crux structure.
7. Prove trivial counterparties and unsupported edge claims fail closed.
8. Prove structural-mispricing drafts that assert edge without mechanism or persistence fail closed.
9. Prove exactly-three crux enforcement.
10. Prove each filed crux has kind, metric, threshold direction, threshold value, and check-by date.
11. Prove `collect_ratifiables` emits stable review items for Edge & Cruxes drafts.
12. Wire the resolver GO branch after Scenarios to file and collect Edge & Cruxes without calling `Senior.ratify`.
13. Keep all tests offline, deterministic, and no-network.

## Risks And Decisions

- The highest-risk issue is producing persuasive prose that is not falsifiable. M3.5 must make cruxes structured and audit-checkable.
- The counterparty check must reject bad faith placeholders without requiring a perfect market microstructure explanation.
- A "fairly priced, pass" variant view is allowed, but it must be explicit and evidence-backed.
- Catalysts are not predictions. They are observable events that would update the thesis.
- Crux thresholds must be typed as direction plus value. Qualitative prose may explain the threshold, but it cannot substitute for the structural fields.
- If existing M3.1 collection cannot represent the chosen draft granularity, implementation must stop and flag the contract gap rather than creating a parallel ratification path.

## Expected Result

After M3.5 implementation, offline `analyze("AAPL")` with the existing fake Senior/LLM seams can:

- produce a filed, evidence-backed Edge & Cruxes artifact;
- collect edge and crux drafts as undecided review items;
- reject empty or one-sided no-trade steelman drafts;
- reject trivial or contemptuous counterparties;
- reject structural-mispricing drafts that assert edge without mechanism or persistence;
- accept explicit no-structural-edge/pass framing when evidence-backed;
- reject unsupported variant views;
- reject generic catalysts;
- reject cruxes missing metric, threshold direction, threshold value, or check-by date;
- enforce exactly three cruxes;
- preserve the two-Senior-touchpoint architecture by adding no Senior call in M3.5.

## Pre-Implementation Self-Review

- Scope is limited to `C-5 Edge & Cruxes`.
- The plan reuses M3.1 through M3.4 infrastructure.
- The plan does not add C-6 Risk, M3.7 ratification, or final Handoff synthesis.
- The plan does not add new primitives, storage abstractions, valuation engines, or dependencies.
- All brakes are deterministic and prompt-independent.
- Structural mispricing is its own required draft with a no-edge/pass escape valve.
- Crux falsifiability is field-based, not keyword-based.
- The plan keeps every Analyst judgment ratifiable and undecided.
