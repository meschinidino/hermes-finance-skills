# M3.1 Analyst Contracts And Infrastructure — Validation

## Technical Checks

After implementation, run:

```text
UV_CACHE_DIR=.uv-cache .venv/bin/uv run --no-sync pytest
UV_CACHE_DIR=.uv-cache .venv/bin/uv run --no-sync python -m resolver AAPL
```

The `--no-sync` flag is intentional. M3.1 validation must run offline and must not require PyPI access, EDGAR, FRED, Damodaran, price feeds, LLM credentials, network access, or human Senior input.

## Required Unit Tests

M3.1 implementation must add tests for these cases:

1. Valid M3 artifact constructs and passes Analyst audit.
2. Artifact with an unsupported claim and no evidence ref is rejected by audit.
3. Artifact with an `EvidenceRef` whose trace target is blank or null is rejected by Analyst audit.
4. Artifact with bare numeric boundary value is rejected where `Number` is required.
5. Recursive collection finds nested ratifiable drafts.
6. Recursive collection preserves source artifact identity.
7. Recursive collection preserves nested field path.
8. Recursive collection creates stable ids across repeated runs.
9. Recursive collection preserves evidence refs and Senior-checklist mapping.
10. Empty `SeniorReviewPackage` is rejected.
11. Review and decision package contracts expose no settable `ratified` field.
12. Derived ratified status is false when one required item lacks a Senior decision.
13. A package with missing required decisions has no way to serialize or persist `ratified: true`.
14. Complete `SeniorDecisionPackage` is accepted.
15. Synthetic test-only multi-ratifiable artifact with multiple nested AnalystDrafts at distinct field paths collects one `ReviewItem` per nested draft.
16. Synthetic multi-ratifiable collection produces distinct stable ids and requires a separate Senior decision for each required item.
17. Offline fake `LLM` returns deterministic identical content across repeated runs.
18. Offline fake `Senior.gate` returns deterministic identical decisions across repeated runs.
19. Offline fake `Senior.ratify` returns deterministic identical decisions across repeated runs.
20. Offline harness wires two distinct handles: one deterministic fake `LLM`, one deterministic fake `Senior`.
21. Fake `Senior` is constructible without passing or storing any fake `LLM` object.
22. Accountant-shaped bundle without LLM dependency passes validation.
23. Analyst-shaped bundle with LLM dependency and ratifiable draft output passes validation.
24. Accountant-shaped bundle declaring an LLM dependency fails validation.
25. Analyst-shaped bundle declaring a bare assertion output contract rather than `needs_ratification` draft output fails validation.
26. Analyst-shaped bundle missing `prompt.md` fails validation.
27. Analyst-shaped bundle missing `eval/cases.jsonl` fails validation.
28. Analyst-shaped bundle missing an eval runner fails validation.
29. Full construct -> audit -> store -> collect path runs offline, performs no network access, and produces deterministic identical fake outputs across runs.

## Manual Validation

Before marking M3.1 complete:

1. Confirm no C-1 through C-6 Analyst bundle has been implemented.
2. Confirm no real LLM or real Senior call has been added.
3. Confirm `resolver.analyze` routing and escalation behavior are unchanged.
4. Confirm M3.1 uses existing `Storage` for storage validation and does not invent new persistence.
5. Confirm M3.1 imports existing M0 primitives instead of redefining `Provenance`, `Number`, `Header`, or `Ratifiable`.
6. Confirm the offline fake `LLM` and fake `Senior` are distinct handles and not aliases over one fake model object.
7. Confirm the fake Senior constructor takes no LLM argument and stores no LLM handle.
8. Confirm Analyst audit has no warning-only or flag-and-pass path for unsupported claims or unresolvable evidence refs.
9. Confirm Senior-review contracts have no stored `ratified` field or setter.
10. Confirm Senior-review validation has no warning-only or flag-and-pass path for missing required decisions.
11. Confirm Analyst assertion detection is declaration-based output-contract validation.
12. Confirm no runtime artifacts under `/data` are committed.

## Deterministic Offline Path

The validation suite must include one end-to-end offline test that:

1. Constructs a sample M3-shaped artifact with at least one required Analyst draft.
2. Audits the artifact.
3. Stores the serialized artifact through existing `Storage`.
4. Reloads it and confirms the payload round-trips.
5. Collects ratifiables into a `SeniorReviewPackage`.
6. Uses deterministic fake `LLM` and fake `Senior` test adapters without network access.
7. Confirms the fake Senior has no reference to the fake LLM.
8. Repeats the path and asserts identical outputs across runs.

This path proves M3.1 is only contracts and infrastructure, not live Analyst execution.

## Closure Criteria

M3.1 can be marked complete in `specs/roadmap.md` only after:

- typed M3 artifact contracts are implemented;
- Analyst audit helpers are implemented;
- resolvable evidence-target checks are implemented;
- ratifiable collection is implemented;
- structural Senior decision completeness is implemented as derived-only status with no stored `ratified` setter;
- synthetic multi-ratifiable collection tests pass;
- deterministic fake `LLM` and fake `Senior` adapters are implemented under tests;
- bundle-shape validation for Accountant and Analyst bundles is implemented;
- all required M3.1 tests pass;
- full offline pytest passes;
- `python -m resolver AAPL` still passes with unchanged M2b behavior.

## Validation Result

Status: implemented and validated.

- `UV_CACHE_DIR=.uv-cache .venv/bin/uv run --no-sync pytest` passed: 65 passed, 3 skipped.
- `UV_CACHE_DIR=.uv-cache .venv/bin/uv run --no-sync python -m resolver AAPL` passed and preserved the existing M2b resolver path.

## Pre-Landing Self-Review

- Independence seam: Validation explicitly requires distinct fake `LLM` and `Senior` handles, deterministic tests for each, and fake Senior construction without any LLM reference. This prevents contracts from assuming a shared model handle.
- Role shapes: Validation includes pass/fail tests for Accountant and Analyst bundle shapes, including the two mixed-shape failures requested. The assertion-detection mechanism is declaration-based output-contract validation.
- Structural ratification: Validation requires no settable `ratified` field in review or decision packages. Ratified status is derived from required decisions, so a ratified-with-missing-decision state is unrepresentable.
- Evidence resolvability: Validation rejects both missing evidence refs and refs with blank or null trace targets.
- Requested validation cases: All requested cases are present, including the full offline construct-audit-store-collect path.
- Forward compatibility: The validation plan now includes a synthetic multi-ratifiable artifact test that exercises the M3.4 Scenarios shape while remaining in scope because it does not implement C-4. The plan still does not test M3.5 specialization behavior because that bundle is out of scope; the base-type pressure points for Edge are captured in the requirements and should be revisited before implementation.
