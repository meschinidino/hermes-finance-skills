# M3.3 Moat And Capital Allocation — Plan

## Objective

Build the next two Analyst bundles in the offline M3 skeleton: `C-2 Moat` and `C-3 CapAlloc`.

M3.3 must produce deterministic, schema-valid, evidence-backed drafts from existing artifacts and frozen fixtures. Each draft remains `needs_ratification`, maps to the Senior checklist, passes the M3.1 evidence audit, and is collected as a ratifiable for the later M3.7 consolidated ratify pass.

The milestone also adds two fail-closed audit brakes for structural holes that evidence resolvability alone cannot catch:

- period-consistency audit: an evidence ref claiming a fiscal period must match the period of the resolved source it points to;
- metric-only moat rejection: a moat claim must reject durability conclusions based only on historical ROIC spread or similar backward-looking spread metrics without a forward-looking competitive mechanism.

Evidence linkage guarantees that a claim is sourced. It does not certify that the inference from sourced evidence to investment judgment is sound. A motivated moat conclusion can cite real, resolving, period-correct evidence. M3.3 audit closes structural holes: unsupported claims, unresolvable evidence, period-mismatched evidence, and metric-only moat assertions. Residual inference quality remains Senior-owned and rubric-graded.

## Scope

In scope:
- Completed `C-2 Moat` Analyst bundle under `skills/research/moat/`.
- Completed `C-3 CapAlloc` Analyst bundle under `skills/research/capalloc/`.
- Deterministic offline drafting from existing run artifacts and frozen fixtures.
- Prompt/eval surfaces required by Analyst bundle shape, with no enforcement authority.
- M3.1 `AnalystDraft`, `EvidenceRef`, evidence audit, ratifiable collection, bundle-shape validation, and deterministic fake adapters.
- M3.2 Analyst bundle patterns for offline drafting, evidence-backed claims, bundle metadata, eval surface, and resolver-compatible artifacts.
- Fail-closed period-consistency audit that compares claimed period to the resolved source period.
- Fail-closed moat audit that rejects metric-only durability claims such as "historical ROIC spread alone proves a moat."
- Tests proving valid Moat and CapAlloc drafts construct, audit, and collect as `needs_ratification` review items.

Out of scope:
- Live LLM drafting.
- Real human Senior calls.
- `C-4 Scenarios`, `C-5 Edge & Cruxes`, or `C-6 Risk`.
- M3.7 consolidated `Senior.ratify`.
- Any second Senior touchpoint. The M3.2 early gate has already fired; M3.3 only collects ratifiables for later.
- Resolver routing or escalation changes beyond the M3.2-established path needed to invoke these offline bundle steps.
- New contracts, primitive types, storage interfaces, or persistence mechanisms.
- EDGAR, WACC, DCF, screens, base-rate, or method-router work except where existing artifacts are read as evidence.
- New external dependencies.

## Dependencies And Invariants

M3.3 depends on completed M3.1 and M3.2 infrastructure:

- `AnalystDraft`, `EvidenceRef`, `ReviewItem`, `SeniorReviewPackage`, and ratifiable collection.
- `audit_analyst_artifact` and evidence resolvability checks.
- Analyst-shaped bundle validation.
- Existing `Header`, `Provenance`, `Number`, and `Ratifiable` primitives.
- Existing storage and JSON artifact conventions.
- Deterministic fake `LLM` and fake `Senior` adapters for offline tests.
- M3.2's offline Analyst bundle layout and resolver integration pattern after the early gate.

Standing invariants:

1. Brakes are audit-enforced, not prompt-enforced. Moat and CapAlloc evidence requirements must be fail-closed audit conditions on the artifact.
2. Both bundles must pass the M3.1 Analyst validator with `no_llm: false`, ratifiable outputs, `SKILL.md`, implementation, `prompt.md`, `eval/cases.jsonl`, eval runner, and `resolver.entry`.
3. This is an offline skeleton, not a stub. Drafting must produce real, schema-valid, evidence-backed artifacts from fixtures with resolvable refs that audit actually checks.

## Proposed Architecture

```text
analyze(ticker)
   ├─ existing M1/M2 path
   ├─ C-1 Business and early gate from M3.2
   ├─ if GO:
   │    ├─ C-2 Moat offline drafter
   │    │    ├─ reads existing artifacts and fixture evidence
   │    │    ├─ emits Moat artifact with AnalystDraft fields
   │    │    └─ passes evidence + period + metric-only-moat audit
   │    ├─ C-3 CapAlloc offline drafter
   │    │    ├─ reads existing artifacts and fixture evidence
   │    │    ├─ emits CapAlloc artifact with AnalystDraft fields
   │    │    └─ passes evidence + period audit
   │    └─ ratifiable collector gathers both as needs_ratification review items
   └─ if NO-GO: unchanged M3.2 stop behavior
```

The drafters are deterministic in this milestone. They may exercise the fake LLM seam if that matches existing M3.2 patterns, but live LLM drafting is deferred. Required narrative must be reproducible from fixture inputs and existing artifacts.

## Skill Bundles Created In M3.3

Both bundles are Analyst bundles (`no_llm: false`):

```text
skills/research/moat/
├── SKILL.md
├── moat.py
├── prompt.md
├── resolver.entry
└── eval/
    ├── cases.jsonl
    └── eval_moat.py

skills/research/capalloc/
├── SKILL.md
├── capalloc.py
├── prompt.md
├── resolver.entry
└── eval/
    ├── cases.jsonl
    └── eval_capalloc.py
```

The implementation may include tests in each bundle or under the project test tree, following the existing repository pattern. `test_integration.py` is not required because M3.3 must be offline.

Each bundle metadata must declare:

- `type: analyst`;
- `no_llm: false`;
- an LLM dependency;
- outputs as `AnalystDraft` or an artifact whose judgment fields are `needs_ratification` drafts;
- no final assertion output contract.

## Offline Draft Shapes

The Moat artifact should be narrow but substantive. Required draft areas:

- moat mechanism draft, naming at least one forward-looking mechanism such as switching costs, network effects, scale advantage, intangibles, cost advantage, regulatory position, or distribution advantage;
- evidence for historical economics, such as ROIC spread, margin durability, retention proxy, market share, or segment economics;
- durability risk or disconfirming evidence draft;
- explicit Senior checklist mapping for moat strength and evidence gaps.

The CapAlloc artifact should be narrow but substantive. Required draft areas:

- reinvestment behavior draft;
- shareholder-return or dilution behavior draft;
- balance-sheet and acquisition discipline draft;
- explicit Senior checklist mapping for capital allocation quality and evidence gaps.

Every required draft must:

- be an `AnalystDraft` or M3.1-compatible ratifiable draft;
- have `needs_ratification` semantics and no final Senior decision;
- include non-empty evidence refs;
- resolve through the M3.1 evidence audit;
- pass period-consistency audit when a claimed period is present;
- map to a Senior checklist area and rationale;
- fail closed if required evidence is missing.

## Audit Brakes

Moat and CapAlloc support is enforced by audit, not by prompt text. `prompt.md` exists for Analyst bundle shape and eval documentation only.

M3.3 adds the following fail-closed audit behavior:

1. Period consistency. If an `EvidenceRef` or its attached `Provenance` claims a fiscal period, audit must resolve the target source and compare the claimed period to the resolved source period. A ref claiming `FY2025` against an `FY2024` accession or source artifact must fail even if the ref resolves.
2. Metric-only moat rejection. A moat draft asserting durability from historical ROIC spread, WACC spread, margins, or similar backward-looking metrics must fail unless the claim also identifies and evidences a forward-looking competitive mechanism. This must be structural enough to reject equivalent phrasing, not a keyword check for the string `ROIC`.
3. Existing M3.1 unsupported-claim behavior remains. Empty evidence, unresolvable refs, blank trace targets, bare numeric boundary values, and final Analyst assertions still fail audit.

The period brake applies to both Moat and CapAlloc drafts. The metric-only moat brake applies to Moat drafts and any Moat-shaped test fixture.

## Implementation Steps

1. Fill `C-2 Moat` and `C-3 CapAlloc` `SKILL.md` files from `specs/SKILL-template.md`.
2. Add the two bundle layouts and eval surfaces required by M3.1 Analyst bundle validation.
3. Define narrow Moat and CapAlloc artifact shapes by composing existing M3.1 draft infrastructure.
4. Build deterministic offline drafting from existing artifacts and frozen fixture evidence.
5. Extend Analyst audit with period-consistency checks that compare claimed period to the resolved source period.
6. Extend Moat audit with metric-only durability rejection.
7. Add valid Moat and CapAlloc fixtures with resolvable, period-correct evidence refs.
8. Add invalid fixtures for unsupported evidence, period mismatch, and metric-only moat claims.
9. Add ratifiable collection tests proving both artifacts emit `needs_ratification` review items with Senior checklist mappings.
10. Wire the resolver-compatible offline path after the M3.2 GO branch without adding a new Senior call.
11. Add deterministic offline validation and no-network tests.

## Risks And Decisions

- Period consistency must compare claimed period to the resolved source period. Merely requiring a period field would repeat the M3.2 blind spot.
- Metric-only moat rejection must be structural. It should reject a durability conclusion when the only support category is backward-looking economics, even if the prose avoids the exact word `ROIC`.
- A valid moat draft may cite ROIC spread as evidence, but only alongside a forward-looking mechanism with evidence.
- Audit does not certify judgment quality. It blocks malformed support structures; the Senior remains responsible for judging whether the inference is persuasive.
- CapAlloc evidence can be thin in offline fixtures, but it must still be real enough to exercise audit and collection.
- No new persistence or review flow is allowed. M3.3 files artifacts and collects ratifiables for the later M3.7 ratify pass.

## Expected Result

After M3.3 implementation, offline `analyze("AAPL")` with M3.2 GO fakes can:

- produce filed, evidence-backed Moat and CapAlloc artifacts;
- pass M3.1 Analyst evidence audit plus M3.3 period and moat brakes;
- prove both bundles satisfy Analyst-shaped bundle validation;
- reject unsupported and unresolvable evidence;
- reject period-mismatched evidence refs;
- reject metric-only moat durability claims;
- collect Moat and CapAlloc drafts as `needs_ratification` review items mapped to the Senior checklist;
- remain deterministic and offline with no network access.

## Pre-Implementation Self-Review

- Scope is limited to `C-2 Moat` and `C-3 CapAlloc`.
- The plan reuses M3.1/M3.2 infrastructure and does not introduce new contracts or persistence.
- Evidence enforcement is audit-based, not prompt-based.
- Both bundles are specified as Analyst bundles with `no_llm: false` and full bundle surfaces.
- Offline skeleton requirements demand substantive fixture-backed drafts, not placeholders.
- Period consistency is specified as claimed-period versus resolved-source-period comparison.
- Metric-only moat rejection is specified as a structural support-category condition, not a keyword check.
- The plan does not add a second Senior touchpoint or consolidated ratify behavior.
- Live LLM drafting, C-4/C-5/C-6, routing escalation changes, and new dependencies are explicitly out of scope.
