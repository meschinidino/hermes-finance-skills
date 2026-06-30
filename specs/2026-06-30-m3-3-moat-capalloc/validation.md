# M3.3 Moat And Capital Allocation — Validation

## Technical Checks

After implementation, run:

```text
UV_CACHE_DIR=.uv-cache .venv/bin/uv run --no-sync pytest
UV_CACHE_DIR=.uv-cache .venv/bin/uv run --no-sync pytest skills/research/moat skills/research/capalloc
UV_CACHE_DIR=.uv-cache .venv/bin/uv run --no-sync python -m resolver AAPL
```

The `--no-sync` flag is intentional. M3.3 validation must run offline and must not require PyPI access, EDGAR, FRED, Damodaran, price feeds, live LLM credentials, network access, a human Senior, or a consolidated Senior ratification pass.

## Required Moat Unit Tests

1. Valid Moat artifact constructs from deterministic offline inputs.
2. Valid Moat artifact passes M3.1 evidence audit.
3. Valid Moat artifact passes M3.3 period-consistency audit.
4. Valid Moat artifact passes M3.3 metric-only-moat audit.
5. Moat artifact includes `Header`, ticker, and as-of date.
6. Moat artifact includes a moat mechanism draft.
7. Moat mechanism draft identifies a forward-looking competitive mechanism.
8. Moat artifact includes historical economics evidence or draft.
9. Moat artifact includes durability risk or disconfirming-evidence draft.
10. Every required Moat draft is an `AnalystDraft` or M3.1-compatible ratifiable draft.
11. Every required Moat draft has `needs_ratification` semantics.
12. Every required Moat draft has non-empty evidence refs.
13. Every required Moat draft has a resolvable evidence target.
14. Every required Moat draft has Senior-checklist area and rationale.
15. Moat artifact with unsupported claim and no evidence ref is rejected by audit.
16. Moat artifact with empty evidence refs is rejected by audit.
17. Moat artifact with blank or null evidence trace target is rejected by audit.
18. Moat artifact with unresolvable evidence ref is rejected by audit.
19. Moat artifact with bare numeric boundary value is rejected where `Number` is required.
20. Moat artifact that asserts a final Analyst judgment without Senior decision metadata is rejected by audit.
21. Prompt contents do not bypass Moat audit failure.
22. Fixture with sufficient Moat evidence produces an audited Moat artifact.
23. Fixture with missing required Moat evidence fails closed.
24. Required Moat draft values are not placeholder-only strings.
25. Deterministic fake LLM output, if used by the Moat drafter seam, is identical across repeated runs.
26. Moat drafter performs no network access.

## Required Capital Allocation Unit Tests

1. Valid CapAlloc artifact constructs from deterministic offline inputs.
2. Valid CapAlloc artifact passes M3.1 evidence audit.
3. Valid CapAlloc artifact passes M3.3 period-consistency audit.
4. CapAlloc artifact includes `Header`, ticker, and as-of date.
5. CapAlloc artifact includes reinvestment behavior draft.
6. CapAlloc artifact includes shareholder-return or dilution behavior draft.
7. CapAlloc artifact includes balance-sheet and acquisition discipline draft.
8. Every required CapAlloc draft is an `AnalystDraft` or M3.1-compatible ratifiable draft.
9. Every required CapAlloc draft has `needs_ratification` semantics.
10. Every required CapAlloc draft has non-empty evidence refs.
11. Every required CapAlloc draft has a resolvable evidence target.
12. Every required CapAlloc draft has Senior-checklist area and rationale.
13. CapAlloc artifact with unsupported claim and no evidence ref is rejected by audit.
14. CapAlloc artifact with empty evidence refs is rejected by audit.
15. CapAlloc artifact with blank or null evidence trace target is rejected by audit.
16. CapAlloc artifact with unresolvable evidence ref is rejected by audit.
17. CapAlloc artifact with bare numeric boundary value is rejected where `Number` is required.
18. CapAlloc artifact that asserts a final Analyst judgment without Senior decision metadata is rejected by audit.
19. Prompt contents do not bypass CapAlloc audit failure.
20. Fixture with sufficient CapAlloc evidence produces an audited CapAlloc artifact.
21. Fixture with missing required CapAlloc evidence fails closed.
22. Required CapAlloc draft values are not placeholder-only strings.
23. Deterministic fake LLM output, if used by the CapAlloc drafter seam, is identical across repeated runs.
24. CapAlloc drafter performs no network access.

## Required Period-Consistency Tests

1. Evidence ref with claimed `FY2025` pointing to a resolved `FY2025` source passes period-consistency audit.
2. Evidence ref with claimed `FY2025` pointing to a resolved `FY2024` source is rejected.
3. Evidence ref with attached `Provenance.period` inconsistent with the resolved source period is rejected.
4. Evidence ref with a non-provenance claimed period inconsistent with the resolved source period is rejected.
5. Evidence ref whose target resolves but whose period is wrong is rejected.
6. Evidence ref claiming an annual period against an incompatible quarterly source is rejected.
7. Period-specific claim without a claimed period fails closed.
8. Non-period-specific claim without a claimed period is allowed only when the resolved source and claim do not require fiscal-period matching.
9. Period mismatch failure reports the claimed period and resolved source period.
10. Test assertions prove the implementation compares claimed period to resolved source period, not merely that both contain period fields.
11. Period-consistency tests run against both a Moat-shaped artifact and a CapAlloc-shaped artifact.

## Required Metric-Only Moat Tests

1. The named roadmap case is rejected: "historical ROIC spread alone proves a moat."
2. A moat claim asserting durability from returns above cost of capital alone is rejected even without the exact string `ROIC`.
3. A moat claim asserting durability from margin history alone is rejected.
4. A moat claim using historical ROIC spread as one evidence item plus an evidenced switching-cost mechanism passes this audit.
5. A moat claim using historical spread as a prompt for investigation, without asserting durability, passes this audit if otherwise evidence-backed.
6. A moat claim naming a forward-looking mechanism but providing no evidence for that mechanism is rejected.
7. A moat claim with evidence for historical economics but no forward-looking mechanism category is rejected.
8. Test assertions prove the rejection is support-category based rather than keyword matching on `ROIC`.

## Required Bundle-Validation Tests

1. The real `skills/research/moat/` bundle passes M3.1 Analyst-shaped bundle validation.
2. The real `skills/research/capalloc/` bundle passes M3.1 Analyst-shaped bundle validation.
3. Moat `SKILL.md` declares `type: analyst`.
4. CapAlloc `SKILL.md` declares `type: analyst`.
5. Moat `SKILL.md` declares `no_llm: false`.
6. CapAlloc `SKILL.md` declares `no_llm: false`.
7. Both bundles declare an LLM dependency.
8. Both bundles declare ratifiable draft output contracts.
9. Neither bundle declares a final assertion output contract.
10. Bundle validation fails if Moat `prompt.md` is removed or absent in a test copy.
11. Bundle validation fails if CapAlloc `prompt.md` is removed or absent in a test copy.
12. Bundle validation fails if Moat `eval/cases.jsonl` is removed or absent in a test copy.
13. Bundle validation fails if CapAlloc `eval/cases.jsonl` is removed or absent in a test copy.
14. Bundle validation fails if Moat `eval/eval_moat.py` is removed or absent in a test copy.
15. Bundle validation fails if CapAlloc `eval/eval_capalloc.py` is removed or absent in a test copy.
16. Bundle validation fails if either output contract is changed to a bare assertion in a test copy.
17. Bundle validation fails if either bundle changes `no_llm` to `true` in a test copy.

## Required Ratifiable Collection Tests

1. Valid Moat artifact collects into one or more review items.
2. Valid CapAlloc artifact collects into one or more review items.
3. Collected Moat review items are marked `needs_ratification`.
4. Collected CapAlloc review items are marked `needs_ratification`.
5. Collected Moat review items preserve source artifact identity.
6. Collected CapAlloc review items preserve source artifact identity.
7. Collected Moat review items preserve source field paths.
8. Collected CapAlloc review items preserve source field paths.
9. Collected Moat review items preserve evidence refs.
10. Collected CapAlloc review items preserve evidence refs.
11. Collected Moat review items preserve Senior-checklist mappings.
12. Collected CapAlloc review items preserve Senior-checklist mappings.
13. Collected review item ids are stable across repeated deterministic runs.
14. Collected items remain undecided before M3.7.
15. Collection does not call `Senior.ratify`.

## Required Resolver Integration Tests

1. `analyze("AAPL")` reaches the Moat step after the M3.2 early gate GO path in offline fake configuration.
2. `analyze("AAPL")` reaches the CapAlloc step after the M3.2 early gate GO path in offline fake configuration.
3. `analyze("AAPL")` does not run Moat after an M3.2 NO-GO stop.
4. `analyze("AAPL")` does not run CapAlloc after an M3.2 NO-GO stop.
5. `analyze("AAPL")` files or returns the Moat artifact.
6. `analyze("AAPL")` files or returns the CapAlloc artifact.
7. `analyze("AAPL")` audits the Moat artifact before collection.
8. `analyze("AAPL")` audits the CapAlloc artifact before collection.
9. Moat audit failure prevents Moat ratifiable collection.
10. CapAlloc audit failure prevents CapAlloc ratifiable collection.
11. Filed Moat artifact survives storage round-trip.
12. Filed CapAlloc artifact survives storage round-trip.
13. Offline resolver run calls no live LLM.
14. Offline resolver run calls no real human Senior.
15. Offline resolver run does not call a second `Senior.gate`.
16. Offline resolver run does not call `Senior.ratify`.
17. Repeated offline resolver runs produce deterministic Moat and CapAlloc drafts.

## Manual Validation

Before marking M3.3 complete:

1. Confirm only `C-2 Moat` and `C-3 CapAlloc` were implemented.
2. Confirm no `C-4`, `C-5`, or `C-6` Analyst bundle was implemented.
3. Confirm no consolidated M3.7 `Senior.ratify` behavior was added.
4. Confirm no second Senior touchpoint was added.
5. Confirm no live LLM call was added.
6. Confirm no real human Senior call is required for tests.
7. Confirm no new M3 contracts were invented.
8. Confirm no new storage abstraction or persistence mechanism was added.
9. Confirm Moat and CapAlloc drafts reuse M3.1 `AnalystDraft` or compatible M3.1 draft infrastructure.
10. Confirm Moat and CapAlloc draft evidence support is enforced by audit.
11. Confirm `prompt.md` has no enforcement role beyond bundle shape and eval documentation.
12. Confirm period-consistency audit compares claimed period to resolved source period.
13. Confirm period-consistency audit rejects a resolving-but-period-wrong evidence ref.
14. Confirm metric-only moat rejection is structural and support-category based.
15. Confirm metric-only moat rejection is not simple keyword matching on `ROIC`.
16. Confirm a valid moat claim can use historical ROIC spread only when paired with an evidenced forward-looking mechanism.
17. Confirm Moat and CapAlloc drafts collect as undecided `needs_ratification` review items.
18. Confirm runtime artifacts under `/data` are not committed.

## Document Validation

Before implementation:

1. Confirm this spec lives under `specs/2026-06-30-m3-3-moat-capalloc/`.
2. Confirm the triplet contains exactly `plan.md`, `requirements.md`, and `validation.md`.
3. Confirm the triplet scopes only M3.3: `C-2 Moat` plus `C-3 CapAlloc`.
4. Confirm the triplet specifies offline deterministic drafting and defers live LLM drafting.
5. Confirm the triplet requires reuse of M3.1 AnalystDraft, evidence audit, ratifiable collection, bundle validation, and fake adapters.
6. Confirm the triplet requires M3.2 patterns and does not reopen the early gate design.
7. Confirm the triplet does not require new contracts or persistence.
8. Confirm the triplet makes evidence support audit-enforced, not prompt-enforced.
9. Confirm the triplet requires both bundles to pass M3.1 Analyst-shaped bundle validation.
10. Confirm the triplet requires valid Moat and CapAlloc drafts to construct and pass evidence audit.
11. Confirm the triplet requires unsupported-evidence drafts to be rejected.
12. Confirm the triplet requires metric-only moat claims to be rejected.
13. Confirm the triplet requires period-mismatched evidence refs to be rejected.
14. Confirm the triplet requires collection as `needs_ratification` with Senior-checklist mappings.
15. Confirm the triplet requires full offline deterministic validation.
16. Confirm the triplet does not include live LLM drafting, C-4/C-5/C-6, M3.7 ratify, or a second Senior touchpoint.

## Responsive And Accessibility Checks

Not applicable in M3.3. There is no UI surface.

## Closure Criteria

M3.3 can be marked complete in `specs/roadmap.md` only after:

- the M3.3 spec files are current;
- the `C-2 Moat` bundle exists and passes Analyst-shaped bundle validation;
- the `C-3 CapAlloc` bundle exists and passes Analyst-shaped bundle validation;
- Moat drafting is deterministic and offline;
- CapAlloc drafting is deterministic and offline;
- Moat and CapAlloc artifacts are schema-valid and evidence-backed;
- unsupported or unresolvable Moat and CapAlloc claims fail audit;
- period-mismatched evidence refs fail audit by comparing claimed period to resolved source period;
- metric-only moat durability claims fail audit structurally;
- Moat and CapAlloc drafts collect as undecided `needs_ratification` review items;
- full offline pytest passes;
- `python -m resolver AAPL` passes in the offline fake configuration.

## Pre-Landing Self-Review

Before landing M3.3 implementation, complete this review and flag anything waved through:

1. Invariant 1, audit-enforced brakes: Confirm unsupported claims, unresolvable evidence, period mismatch, and metric-only moat failures are enforced by audit code, not prompt text.
2. Invariant 2, Analyst validator: Confirm both bundles pass M3.1 Analyst validation with `no_llm: false`, ratifiable outputs, `SKILL.md`, implementation, `prompt.md`, eval cases, eval runner, and `resolver.entry`.
3. Invariant 3, offline skeleton: Confirm valid Moat and CapAlloc drafts are concrete fixture-backed artifacts, not placeholder strings or trivially passing shells.
4. Invariant 4, period consistency: Confirm the check actually compares claimed period versus resolved source period, and that a resolving `FY2025` ref against an `FY2024` accession/source fails.
5. Invariant 5, moat rejection: Confirm "historical ROIC spread alone proves a moat" fails and that equivalent non-`ROIC` phrasing fails because support categories are insufficient.
6. Validation cases: Confirm Moat draft constructs and passes audit, CapAlloc draft constructs and passes audit, unsupported evidence rejects, metric-only moat rejects, period mismatch rejects, both bundles pass validation, drafts collect as `needs_ratification`, and full path is offline and deterministic.
7. Senior ownership: Confirm no test or audit result implies inference-soundness is certified; residual judgment quality remains Senior-owned and rubric-graded.
8. Scope fence: Confirm no live LLM drafting, C-4/C-5/C-6, M3.7 ratify, second Senior touchpoint, routing escalation changes, new contracts, or new persistence slipped in.

## Validation Result

Status: planned, not implemented.

Implementation validation is intentionally pending user review of this triplet.
