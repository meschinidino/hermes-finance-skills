# M3.2 Business And Early Gate — Plan

## Objective

Build the first real Analyst slice: `C-1 Business` plus the single early GO/NO-GO gate after Business understanding.

M3.2 is an offline skeleton, not a live-LLM implementation and not a placeholder. It must produce a schema-valid, evidence-backed Business draft from existing artifacts and frozen fixtures, audit that draft with the M3.1 evidence checks, call one injected `Senior.gate` exactly once after Business, and branch deterministically:

- GO continues to the existing downstream resolver path.
- NO-GO halts and files a schema-valid stop artifact with the gate rationale.

## Scope

In scope:
- A completed `C-1 Business` Analyst bundle under `skills/research/business/`.
- Deterministic offline Business drafting from existing artifacts and fixtures.
- A prompt/eval surface required by Analyst bundle shape, with no enforcement authority.
- Business artifact construction using the M3.1 `AnalystDraft` and evidence-reference infrastructure.
- M3.1 evidence audit as the enforcement point for Business draft support.
- M3.1 Analyst-shaped bundle validation as a required validation target for the first real Analyst bundle.
- Resolver wiring that invokes `Senior.gate` exactly once after Business audit and before downstream work.
- Gate wiring that enforces Analyst drafter and Senior model-family independence from declared adapter identities.
- GO and NO-GO resolver branches, including a filed stop artifact for NO-GO.
- Offline tests using deterministic fake `LLM` and fake `Senior` adapters.

Out of scope:
- Live LLM drafting.
- Real human Senior interaction.
- C-2 through C-6 Analyst bundles.
- Consolidated `Senior.ratify` behavior from M3.7.
- New contracts, primitive types, storage interfaces, or persistence mechanisms.
- EDGAR, WACC, DCF, screen, base-rate, or method-router changes except where existing artifacts are read as Business evidence.
- New external dependencies.

## Dependencies And Invariants

M3.2 depends on completed M3.1 infrastructure:

- `AnalystDraft`, `EvidenceRef`, `SeniorReviewPackage`, and ratifiable collection.
- `audit_analyst_artifact` and existing evidence resolvability checks.
- Existing `Senior` and `LLM` injection interfaces.
- Deterministic fake adapters under the test surface.
- Analyst-shaped bundle validation.
- Existing storage and JSON artifact conventions.

M3.2 must not duplicate M3.1 contracts, create a new Business-only ratifiable type, or invent a second stop-artifact persistence path.

## Proposed Architecture

```text
analyze(ticker)
   ├─ existing M1/M2 path through EDGAR, Normalize, Spine, Price, CoC, Screens, Router, DCF as applicable
   ├─ C-1 Business offline drafter
   │    ├─ reads existing filed artifacts and deterministic fixture evidence
   │    ├─ emits Business artifact containing AnalystDraft fields
   │    └─ passes audit_analyst_artifact(...)
   ├─ early gate wiring
   │    ├─ asserts analyst_family != senior_family
   │    ├─ calls Senior.gate exactly once
   │    └─ files gate result
   ├─ if GO: continue downstream path
   └─ if NO-GO: file stop artifact and halt
```

The Business drafter is deterministic in this milestone. It may use the fake LLM adapter to exercise the injection seam, but live LLM text generation is deferred. Any generated-looking narrative must be reproducible from fixture inputs and existing artifacts.

## Skill Bundle Created In M3.2

`C-1 Business` is an Analyst bundle (`no_llm: false`) and must be the first production bundle that proves M3.1 Analyst-shaped bundle validation works against a real skill.

```text
skills/research/business/
├── SKILL.md
├── business.py
├── prompt.md
├── resolver.entry
└── eval/
    ├── cases.jsonl
    └── eval_business.py
```

The implementation may include tests in the same bundle or under the project test tree, following the existing repository pattern. `test_integration.py` is not required because M3.2 must be offline.

The bundle metadata must declare:

- `type: analyst`
- `no_llm: false`
- LLM dependency declared
- outputs as `AnalystDraft` or a Business artifact whose judgment fields are `needs_ratification` drafts
- no final assertion output contract

## Offline Business Draft Shape

The Business artifact should be narrow and useful. It should prove the Business workflow can work without pretending to complete the full research program.

Required draft areas:

- business model summary draft;
- revenue driver or segment mix draft;
- customer/end-market draft;
- one explicit Business understanding risk or GO/NO-GO concern.

Each draft must:

- be an `AnalystDraft` or M3.1-compatible ratifiable draft;
- include non-empty, resolvable `EvidenceRef` entries;
- map to a Senior checklist area and rationale;
- remain unratified before the Senior gate;
- avoid final asserted judgment.

The offline drafter must source from existing filed artifacts and frozen fixtures. If required evidence is missing, the Business drafter must fail closed instead of inventing a narrative.

## Early Gate Behavior

The early gate is the first place the injected Senior runs. M3.2 must enforce role independence at wiring time.

Before calling `Senior.gate`, the resolver or gate wrapper must compare declared model-family identities for the Analyst drafter and Senior. If the identities match, gate wiring fails closed and `Senior.gate` is not called. This is an offline identity assertion on adapter metadata, not a live model call.

If model-family identities differ, the gate receives the audited Business artifact plus enough run context to decide GO or NO-GO. `Senior.gate` is called exactly once. Its result is filed as a run artifact.

GO continues. NO-GO halts and files a stop artifact with:

- `Header`;
- ticker;
- as-of date;
- gate name;
- gate decision;
- gate rationale;
- pointer to the Business artifact and evidence package;
- no valuation or investment recommendation.

## Enforcement Boundary

Business draft support is enforced by audit, not by prompt instructions.

`prompt.md` exists because Analyst bundles require a prompt/eval surface, but it carries no enforcement weight. A Business artifact with unsupported claims, empty evidence, or unresolvable evidence must fail `audit_analyst_artifact` regardless of what `prompt.md` says.

## Implementation Steps

1. Fill the `C-1 Business` `SKILL.md` from `specs/SKILL-template.md`.
2. Add the Business bundle files and eval surface required by Analyst bundle validation.
3. Add a narrow Business artifact shape that reuses M3.1 `AnalystDraft` and existing primitives.
4. Build deterministic offline drafting from existing artifacts and fixture evidence.
5. Add Business audit coverage using `audit_analyst_artifact`.
6. Add gate-family identity metadata handling for fake Analyst and fake Senior adapters.
7. Add gate wiring that rejects same-family Analyst/Senior identities before calling `Senior.gate`.
8. Wire the resolver to call the Business drafter and audit it before the early gate.
9. Wire the resolver to call `Senior.gate` exactly once after Business and before downstream work.
10. Implement GO continuation and NO-GO halt with a filed stop artifact.
11. Add tests for bundle validation, audit failure, family mismatch failure, exactly-once gate call, GO branch, and NO-GO branch.

## Risks And Decisions

- The offline skeleton must not degrade into a stub. It must file a real Business artifact with evidence-backed drafts that audit can reject when broken.
- The prompt must not become the brake. Enforcement lives in schema and audit checks so bad drafts fail even if the prompt text is ignored.
- Role independence is no longer merely possible after M3.1. Because M3.2 runs the Senior, same-family Analyst/Senior wiring is a hard failure.
- Exactly-once gate behavior is load-bearing. Multiple calls create hidden review checkpoints; zero calls skip the Senior's first required touchpoint.
- NO-GO must halt cleanly and inspectably. A stop artifact is required so downstream consumers can distinguish an intentional gate halt from a crash.
- Live LLM behavior is deferred to protect deterministic offline validation and keep M3.2 focused on wiring, artifact shape, and gates.

## Expected Result

After M3.2 implementation, `analyze("AAPL")` with offline fakes can:

- produce a filed, evidence-backed Business artifact;
- pass M3.1 Analyst evidence audit;
- prove the `C-1 Business` bundle satisfies Analyst-shaped bundle validation;
- reject same-family Analyst/Senior wiring before any Senior call;
- call `Senior.gate` exactly once for valid different-family wiring;
- continue on GO;
- halt on NO-GO with a filed, schema-valid stop artifact.

## Pre-Implementation Self-Review

- Scope is limited to `C-1 Business` and the early gate.
- The plan reuses M3.1 infrastructure and does not introduce new contracts or persistence.
- Evidence enforcement is audit-based, not prompt-based.
- The early gate enforces different model-family identities at wiring time.
- The gate call is specified as exactly once, after Business and before downstream work.
- Both GO and NO-GO branches are required and testable.
- Live LLM drafting and real Senior calls are explicitly out of scope.
