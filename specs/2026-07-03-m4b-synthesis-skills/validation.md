# M4b Synthesis Skills - Validation

## Technical Checks

Run:

```text
UV_CACHE_DIR=.uv-cache .venv/bin/uv run --no-sync pytest
UV_CACHE_DIR=.uv-cache .venv/bin/uv run --no-sync python -m resolver AAPL
UV_CACHE_DIR=.uv-cache .venv/bin/uv run --no-sync python -m resolver MRNA
```

The full pytest command is required. Focused D-2/D-3 tests are not sufficient to mark M4b complete.

## Required Unit Tests

1. `SynthesisPayload` accepts a valid AAPL DCF payload from the M4a boundary.
2. `SynthesisPayload` accepts a valid MRNA non-DCF payload from the M4a boundary when `valuation_deferred` is present.
3. `SynthesisPayload` rejects missing required filed artifacts.
4. `SynthesisPayload` rejects incomplete Senior decision packages.
5. `SynthesisPayload` rejects unresolved required ratifiables that would reach final Handoff.
6. `SynthesisPayload` rejects bare numeric values in fields consumed by D-2/D-3.
7. D-2 Conviction emits a pydantic artifact with `Header`.
8. D-2 Conviction files its artifact to storage and reloads cleanly.
9. D-2 Conviction fails closed when required ratified artifacts are missing.
10. D-2 Conviction emits required `SizingInputs`.
11. D-3 Review Packager emits a pydantic final Handoff artifact with `Header`.
12. D-3 Review Packager files its artifact to storage and reloads cleanly.
13. D-3 Review Packager fails closed when the D-2 artifact is missing.

## Required Resolver Tests

1. GO-path `analyze("AAPL")` runs M4a boundary, validates `SynthesisPayload`, runs D-2, runs D-3, and returns the final Handoff.
2. GO-path synthesis happens after `Senior.ratify`.
3. `Senior.gate` is still called exactly once on the GO path.
4. `Senior.ratify` is still called exactly once on the GO path.
5. No Senior call happens inside D-2.
6. No Senior call happens inside D-3.
7. NO-GO path remains unchanged and does not run D-2 or D-3.
8. D-2 and D-3 filed artifacts exist under the run directory after a successful GO path.
9. Existing M0-M3 artifact filenames remain stable.

## Required Negative-Path Tests

M4b introduces new failure modes. Each must have at least one test:

1. Missing ratified artifact:
   - Remove or omit a required ratified artifact from `SynthesisPayload`.
   - Expect validation or D-2/D-3 construction to fail closed before final Handoff return.
2. DCF paths absent:
   - Build a DCF-route payload with missing `valuation_range` or missing `expectations_line`.
   - Expect validation to fail before D-2/D-3 consume the payload.
3. `valuation_deferred` absent for non-DCF:
   - Build a non-DCF payload without `valuation_deferred`.
   - Expect validation to fail before D-2/D-3 consume the payload.
4. Bare numeric leakage:
   - Inject a bare `float` or `int` where a synthesis-consumed numeric field should be a `Number`.
   - Expect pydantic validation to reject it.
5. Missing D-2 artifact:
   - Invoke D-3 without a filed D-2 artifact.
   - Expect D-3 to fail closed.
6. Missing `sizing_inputs`:
   - Build or mutate a final Handoff candidate without `sizing_inputs`.
   - Expect the Handoff completeness check to fail closed.

## Manual Validation

Before marking M4b complete:

1. Confirm the only resolver change is the extension point after M4a boundary output and after M3.7 ratification.
2. Confirm synthesis still happens after Senior ratification on the GO path.
3. Confirm no M4c routing table, escalation matrix, KILL halt, parallelism, or model identity independence checks were implemented.
4. Confirm `CurrentSynthesisInput` path-string and boundary-I/O debt was recorded but not expanded.
5. Confirm no new Senior touchpoint was added.
6. Confirm no live LLM dependency was introduced.
7. Confirm D-2 and D-3 comply with skill bundle conventions and `specs/SKILL-template.md`.
8. Confirm final Handoff fields are pydantic-validated and filed to storage.

## Output Checks

For `analyze("AAPL")`:

- Returns final Handoff, not the M4a intermediate payload.
- Includes filed D-2 Conviction artifact.
- Includes filed D-3 Review Packager / final Handoff artifact.
- Includes Senior-signed lean.
- Includes conviction label and score.
- Includes required sizing inputs.
- Includes provenance-bearing price and valuation numbers.
- Includes exactly three cruxes.
- Includes risk and edge artifacts.

For `analyze("MRNA")`:

- Does not fabricate DCF `valuation_range` or `expectations_line`.
- Preserves current non-DCF route behavior.
- Fails closed or returns a route-compatible final synthesis result according to the implemented M4b non-DCF contract.

## Closure Criteria

M4b can be marked complete in `specs/roadmap.md` only after:

- the M4b spec files are current;
- D-2 and D-3 skill bundles exist and pass validation;
- `SynthesisPayload` is used before D-2/D-3 consumption;
- D-2 and D-3 artifacts are filed and reloadable;
- D-2 produces required `SizingInputs`;
- `analyze()` returns a complete, Senior-signed Handoff on the GO path;
- all required negative-path tests pass;
- the full test suite passes;
- resolver smoke commands for AAPL and MRNA run;
- no M4c features have been implemented.
