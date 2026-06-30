# M3.2 Business And Early Gate — Validation

## Technical Checks

After implementation, run:

```text
UV_CACHE_DIR=.uv-cache .venv/bin/uv run --no-sync pytest
UV_CACHE_DIR=.uv-cache .venv/bin/uv run --no-sync pytest skills/research/business
UV_CACHE_DIR=.uv-cache .venv/bin/uv run --no-sync python -m resolver AAPL
```

The `--no-sync` flag is intentional. M3.2 validation must run offline and must not require PyPI access, EDGAR, FRED, Damodaran, price feeds, live LLM credentials, network access, or a human Senior.

## Required Unit Tests

M3.2 implementation must add tests for these cases:

1. Valid Business artifact constructs from deterministic offline inputs.
2. Valid Business artifact passes `audit_analyst_artifact`.
3. Business artifact includes `Header`, ticker, and as-of date.
4. Business artifact includes business model summary draft.
5. Business artifact includes revenue driver or segment mix draft.
6. Business artifact includes customer or end-market draft.
7. Business artifact includes Business understanding risk or GO/NO-GO concern draft.
8. Every required Business draft is an `AnalystDraft` or M3.1-compatible ratifiable draft.
9. Every required Business draft has non-empty evidence refs.
10. Every required Business draft has a resolvable evidence target.
11. Every required Business draft has Senior-checklist area and rationale.
12. Business artifact with unsupported claim and no evidence ref is rejected by audit.
13. Business artifact with empty evidence refs is rejected by audit.
14. Business artifact with blank or null evidence trace target is rejected by audit.
15. Business artifact with bare numeric boundary value is rejected where `Number` is required.
16. Business artifact that asserts a final Analyst judgment without Senior decision metadata is rejected by audit.
17. Prompt contents do not bypass audit failure.
18. Fixture with sufficient Business evidence produces an audited Business artifact.
19. Fixture with missing required Business evidence fails closed.
20. Required draft values are not placeholder-only strings.
21. Deterministic fake LLM output, if used by the drafter seam, is identical across repeated runs.
22. Business drafter performs no network access.

## Required Bundle-Validation Tests

1. The real `skills/research/business/` bundle passes M3.1 Analyst-shaped bundle validation.
2. Business `SKILL.md` declares `type: analyst`.
3. Business `SKILL.md` declares `no_llm: false`.
4. Business bundle declares an LLM dependency.
5. Business bundle declares a ratifiable draft output contract.
6. Business bundle does not declare a final assertion output contract.
7. Bundle validation fails if `prompt.md` is removed or absent in a test copy.
8. Bundle validation fails if `eval/cases.jsonl` is removed or absent in a test copy.
9. Bundle validation fails if `eval/eval_business.py` is removed or absent in a test copy.
10. Bundle validation fails if the output contract is changed to a bare assertion in a test copy.
11. Bundle validation fails if `no_llm` is changed to `true` in a test copy.

## Required Gate-Wiring Tests

1. Same-family Analyst/Senior wiring is rejected before the gate runs.
2. Same-family rejection leaves `Senior.gate` call count at zero.
3. Same-family rejection produces an explicit wiring or validation error.
4. Different-family Analyst/Senior wiring proceeds.
5. Different-family wiring calls `Senior.gate` exactly once.
6. `Senior.gate` is called only after Business artifact construction.
7. `Senior.gate` is called only after Business audit passes.
8. Business audit failure prevents any `Senior.gate` call.
9. The early gate receives the audited Business artifact or a pointer to it.
10. GO gate decision continues the resolver path.
11. NO-GO gate decision halts the resolver path.
12. GO branch files or captures the gate result.
13. NO-GO branch files the gate result.
14. NO-GO branch files a schema-valid stop artifact.
15. Stop artifact includes header, ticker, as-of date, gate name, decision, rationale, and Business artifact pointer.
16. Stop artifact contains no valuation or final investment recommendation.
17. No test observes more than one `Senior.gate` call in a single resolver run.

## Required Resolver Integration Tests

1. `analyze("AAPL")` reaches the Business step in the offline fake configuration.
2. `analyze("AAPL")` files or returns the Business artifact.
3. `analyze("AAPL")` audits the Business artifact before calling the early gate.
4. `analyze("AAPL")` rejects same-family fake Analyst/Senior identities.
5. `analyze("AAPL")` proceeds with different-family fake Analyst/Senior identities.
6. `analyze("AAPL")` calls `Senior.gate` exactly once with different-family identities.
7. GO fake Senior response allows the resolver to continue.
8. NO-GO fake Senior response halts the resolver and files the stop artifact.
9. Filed Business artifact survives storage round-trip.
10. Filed gate result survives storage round-trip.
11. Filed NO-GO stop artifact survives storage round-trip.

## Manual Validation

Before marking M3.2 complete:

1. Confirm only `C-1 Business` and the early gate were implemented.
2. Confirm no C-2 through C-6 Analyst bundle was implemented.
3. Confirm no consolidated `Senior.ratify` behavior was added.
4. Confirm no live LLM call was added.
5. Confirm no real human Senior call is required for tests.
6. Confirm no new M3 contracts were invented.
7. Confirm no new storage abstraction or persistence mechanism was added.
8. Confirm Business drafts reuse M3.1 `AnalystDraft` or compatible M3.1 draft infrastructure.
9. Confirm Business draft evidence support is enforced by `audit_analyst_artifact`.
10. Confirm `prompt.md` has no enforcement role beyond bundle shape and eval documentation.
11. Confirm same-family Analyst/Senior wiring fails closed before the gate call.
12. Confirm different-family Analyst/Senior wiring proceeds.
13. Confirm `Senior.gate` is called exactly once in a successful gate run.
14. Confirm GO branch continues.
15. Confirm NO-GO branch halts and files a stop artifact.
16. Confirm the stop artifact includes the gate rationale and Business artifact pointer.
17. Confirm runtime artifacts under `/data` are not committed.

## Document Validation

Before implementation:

1. Confirm this spec lives under `specs/2026-06-30-m3-2-business-early-gate/`.
2. Confirm the triplet contains exactly `plan.md`, `requirements.md`, and `validation.md`.
3. Confirm the triplet scopes only M3.2: `C-1 Business` plus the early GO/NO-GO gate.
4. Confirm the triplet specifies offline deterministic drafting and defers live LLM drafting.
5. Confirm the triplet requires reuse of M3.1 AnalystDraft, evidence audit, bundle validation, and fake adapters.
6. Confirm the triplet does not require new contracts or persistence.
7. Confirm the triplet requires model-family independence to be enforced at gate wiring time.
8. Confirm the triplet requires same-family wiring rejection and different-family wiring success tests.
9. Confirm the triplet makes Business evidence support audit-enforced, not prompt-enforced.
10. Confirm the triplet requires exactly one `Senior.gate` call after Business.
11. Confirm the triplet requires GO and NO-GO branch tests.
12. Confirm the triplet requires the Business bundle to pass M3.1 Analyst-shaped bundle validation.

## Responsive And Accessibility Checks

Not applicable in M3.2. There is no UI surface.

## Closure Criteria

M3.2 can be marked complete in `specs/roadmap.md` only after:

- the M3.2 spec files are current;
- the `C-1 Business` bundle exists and passes Analyst-shaped bundle validation;
- Business drafting is deterministic and offline;
- Business artifacts are schema-valid and evidence-backed;
- unsupported or unresolvable Business claims fail audit;
- same-family Analyst/Senior wiring fails closed before `Senior.gate`;
- different-family Analyst/Senior wiring reaches the gate;
- `Senior.gate` call count is exactly one in a successful gate run;
- GO branch continues;
- NO-GO branch halts and files a schema-valid stop artifact;
- full offline pytest passes;
- `python -m resolver AAPL` passes in the offline fake configuration.

## Validation Result

Status: implemented and validated.

Validation completed on 2026-06-30:

```text
UV_CACHE_DIR=.uv-cache .venv/bin/uv run --no-sync pytest tests/test_m3_2_business_gate.py skills/research/business
UV_CACHE_DIR=.uv-cache .venv/bin/uv run --no-sync pytest
UV_CACHE_DIR=.uv-cache .venv/bin/uv run --no-sync python -m resolver AAPL
```

Results:
- targeted M3.2 suite: 10 passed;
- full offline suite: 81 passed, 3 skipped;
- resolver smoke: passed and emitted Business plus early gate artifacts.
