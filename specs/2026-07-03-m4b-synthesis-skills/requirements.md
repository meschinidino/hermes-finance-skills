# M4b Synthesis Skills - Requirements

## Functional Requirements

1. M4b must implement D-2 Conviction.
2. M4b must implement D-3 Review Packager.
3. `analyze()` must return a complete, Senior-signed Handoff on the GO path.
4. D-2 and D-3 must run only after M3.7 Senior ratification succeeds.
5. D-2 and D-3 must consume ratified artifacts only.
6. D-2 must file a pydantic conviction artifact under the run directory.
7. D-2 must produce required `SizingInputs` as part of its output artifact.
8. D-3 must file the final pydantic Handoff artifact under the run directory.
9. The current NO-GO path must remain unchanged.
10. Existing M0-M3 artifact paths must remain stable.
11. Existing Senior gate and ratify call counts must remain unchanged.
12. M4b must add no new Senior touchpoint.
13. M4b must not require live LLM access.

## Resolver Requirements

- `analyze()` currently returns `assemble_current_payload(...)` directly.
- M4b must change only that resolver extension point:
  - assign the M4a boundary output to an intermediate value;
  - validate or wrap it as `SynthesisPayload`;
  - run D-2 Conviction;
  - run D-3 Review Packager;
  - return the packaged Handoff result.
- Synthesis must remain after ratification on the GO path.
- No other resolver routing or control-flow change is in scope.
- M4b must not start M4c routing-table, KILL-halt, escalation-matrix, parallelism, or independence-check work.

## Typed Contract Requirements

- The M4a `dict[str, Any]` boundary output must be replaced by or wrapped into a validated pydantic `SynthesisPayload`.
- D-2 and D-3 must consume `SynthesisPayload`, not an unvalidated `dict[str, Any]`.
- `SynthesisPayload` must validate all required artifact fields before D-2/D-3 run.
- `SynthesisPayload` must validate that required Senior decisions are present and complete.
- `SynthesisPayload` must validate route-specific valuation state:
  - DCF requires `valuation_range` and `expectations_line`.
  - Non-DCF requires `valuation_deferred`.
- No bare floats or ints may cross into D-2 or D-3.
- Numeric values crossing into D-2 or D-3 must be `Number` models with `Provenance`.
- D-2 and D-3 outputs must be pydantic artifact models with `Header`.
- D-2 and D-3 filed outputs must be reloadable from storage and pass audit.
- D-2 output must include `SizingInputs`; conviction without sizing inputs is incomplete.

## Handoff Requirements

- The final Handoff must satisfy the schema intent in `specs/filing-rules.md`.
- The final Handoff must include:
  - ticker;
  - price;
  - as-of date;
  - Senior-signed lean;
  - conviction label and score;
  - thesis;
  - what-is-priced-in / expectations line;
  - valuation range or explicit route-compatible valuation handling;
  - exactly three cruxes;
  - risk sheet;
  - edge statement;
  - sizing inputs;
  - confidence and gaps;
  - revisit triggers when derivable from existing artifacts without M4c control-flow work;
  - data room references.
- Any `Ratifiable` reaching the final Handoff must have a Senior decision.
- A final Handoff missing `sizing_inputs` must fail closed.
- Missing required final Handoff fields must fail closed.

## Boundary Requirements

- D-2 must not call the Senior.
- D-3 must not call the Senior.
- D-2 must not call an LLM.
- D-3 must not call an LLM.
- D-2 and D-3 must not fabricate missing numbers.
- D-2 and D-3 must not impute missing valuation concepts.
- D-2 and D-3 must not read unfiled internal skill state.
- Runtime artifacts must remain under `/data` or test temp storage.

## Negative Requirements

- M4b must not modify M4a's known boundary debt unless required by the typed wrapper:
  - `CurrentSynthesisInput` carrying bare path strings remains deferred.
  - Boundary-internal storage I/O remains deferred.
  - Bare path/control strings in the M4a boundary are recorded debt, not solved in M4b.
- M4b must not implement M4c control flow.
- M4b must not implement calibration analytics.
- M4b must not introduce server, queue, or database dependencies.

## Acceptance Criteria

- `analyze("AAPL")` returns a complete, Senior-signed Handoff on the GO path.
- `analyze("MRNA")` follows the current non-DCF route without fabricating DCF artifacts and still reaches a validated synthesis result when route-compatible inputs are present.
- D-2 and D-3 artifacts are filed and reloadable.
- D-2 artifact includes required `SizingInputs`.
- D-2 and D-3 consume a validated `SynthesisPayload`.
- Full test suite passes.
- Negative-path tests cover missing ratified artifact, absent DCF paths, and absent non-DCF `valuation_deferred`.
- Existing M0-M3 tests pass unchanged.
