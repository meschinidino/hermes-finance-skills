# M4b Synthesis Skills - Plan

## Objective

Implement the D-2 Conviction and D-3 Review Packager synthesis skills on top of the M4a synthesis boundary so `analyze()` returns a complete, Senior-signed Handoff on the GO path.

M4b is a synthesis slice. It consumes already-ratified M2/M3 artifacts and produces final signed synthesis artifacts. It must not add routing-table orchestration, kill-memo control flow, parallelism, escalation-matrix behavior, or independence-check upgrades.

## Scope

In scope:

- D-2 Conviction synthesis skill.
- D-3 Review Packager synthesis skill.
- A validated pydantic `SynthesisPayload` contract that replaces or wraps the current `dict[str, Any]` M4a boundary output before D-2/D-3 consume it.
- Minimal resolver extension point: replace the direct `return assemble_current_payload(...)` with an intermediate assignment, then run D-2 followed by D-3, then return the packaged result.
- Synthesis remains after M3.7 ratification on the GO path.
- D-2 and D-3 consume only ratified artifacts and filed payloads from the M4a boundary.
- D-2 and D-3 emit pydantic artifact models and file those artifacts to storage.
- Final resolver output is a complete, Senior-signed Handoff.
- Tests for happy paths and every new M4b failure mode.

Out of scope:

- M4c control flow: routing table, escalation matrix, parallelism, KILL halt, revisit-trigger wiring from C-5 `pass_falsifiers`, and model-provider identity independence checks.
- Reworking `CurrentSynthesisInput`.
- Removing bare path strings from `CurrentSynthesisInput`.
- Removing I/O from the M4a boundary.
- New Analyst or Accountant research bundles.
- Live LLM behavior.
- Dependency changes unless required by existing project dependencies.
- Non-US or non-XBRL support.
- Calibration analytics.

## Required Resolver Extension Point

Current M4a resolver shape:

```python
return assemble_current_payload(...)
```

M4b requires the smallest resolver change needed for D-2/D-3 to consume the boundary output:

```text
current_payload = assemble_current_payload(...)
synthesis_payload = SynthesisPayload.model_validate(current_payload)
conviction = build_conviction(synthesis_payload, ...)
review_package = build_review_packager(synthesis_payload, conviction, ...)
return review_package / final handoff payload
```

This extension point must remain after:

1. Business early gate GO.
2. M2/M3 artifact construction and audit.
3. M3.7 consolidated Senior review package.
4. `Senior.ratify`.
5. Senior decision package audit and persistence.

No other resolver control-flow change is in scope.

## Typed Contract Plan

The M4a boundary currently returns `dict[str, Any]`. M4b introduces a validated pydantic `SynthesisPayload` model that either replaces that return type or wraps the existing dictionary before D-2/D-3 consume it.

The contract must:

- Validate required filed artifacts for D-2/D-3.
- Preserve the existing artifact payloads as typed pydantic models where models already exist.
- Reject unresolved or unratified Senior review/decision state.
- Reject bare numeric values crossing into D-2/D-3.
- Carry numbers only as `Number` models with `Provenance`.
- Keep route-specific valuation inputs explicit:
  - DCF requires `valuation_range` and `expectations_line`.
  - Non-DCF requires `valuation_deferred` until those valuation methods are implemented.

D-2 and D-3 outputs must be pydantic artifacts with `Header` and must be filed under the run directory.

## D-2 Conviction

D-2 consumes `SynthesisPayload` and ratified Senior decisions to produce a pydantic conviction artifact.

Expected responsibilities:

- Derive final lean only from Senior-ratified evidence and available valuation/risk artifacts.
- Produce conviction label and score.
- Produce confidence-and-gaps fields.
- Preserve explicit evidence references to source artifacts and Senior decisions.
- Fail closed if required ratified artifacts or required valuation inputs are absent.

D-2 must not:

- Call the Senior.
- Call an LLM.
- Invent missing numbers.
- Impute unsupported valuation inputs.
- Read unfiled artifacts directly from skill internals.

## D-3 Review Packager

D-3 consumes `SynthesisPayload` plus the filed D-2 artifact and produces the final complete Handoff.

Expected responsibilities:

- Assemble the final filing-rules Handoff shape.
- Include signed/risk/edge/crux/valuation/data-room fields required by `specs/filing-rules.md`.
- Include the Senior-signed lean/decision state.
- Preserve provenance-bearing numbers.
- File the final handoff artifact under the run directory.
- Return the final packaged result from `analyze()`.

D-3 must not:

- Re-run M2/M3 skills.
- Change Senior decisions.
- Add new Senior touchpoints.
- Add M4c revisit-trigger wiring beyond fields that can be populated from already-filed artifacts without new routing/control-flow behavior.

## Known Debt Deferred

The M4a domain review identified debt in the current boundary:

- `CurrentSynthesisInput` carries bare path strings.
- `CurrentSynthesisInput` also carries bare control strings such as `ticker`, `method`, and `valuation_deferred`.
- The M4a boundary performs storage I/O internally.

This is explicitly out of scope for M4b. It is a candidate for M4c or a later boundary-hardening slice.

## Implementation Steps

1. Define the M4b pydantic `SynthesisPayload` contract and validation rules.
2. Add D-2 Conviction skill bundle following the project skill layout and `specs/SKILL-template.md`.
3. Add D-3 Review Packager skill bundle following the project skill layout and `specs/SKILL-template.md`.
4. Add D-2 and D-3 pydantic artifact models.
5. Extend the resolver minimally: assign the M4a boundary output, validate it as `SynthesisPayload`, run D-2, file/audit D-2, run D-3, file/audit D-3, return final Handoff.
6. Keep the NO-GO path unchanged.
7. Add happy-path tests for AAPL and MRNA as supported by existing route behavior.
8. Add negative-path tests for every new failure mode introduced by M4b.
9. Run the full suite and resolver smoke commands.

## Risks And Decisions

- D-2/D-3 must consume ratified artifacts only. If any required judgment is not ratified, M4b must fail closed.
- `SynthesisPayload` must be strict enough to block bare-number leakage into synthesis without prematurely redesigning M4a path-string/I/O debt.
- Non-DCF names currently have deferred valuation behavior. M4b must explicitly validate that state rather than fabricate unsupported valuation outputs.
- Final Handoff assembly is user-facing and becomes the first complete end-to-end product result, so missing fields should fail validation rather than silently degrade.

## Expected Result

After M4b, `analyze()` on a GO path returns a complete, Senior-signed Handoff assembled by D-2 Conviction and D-3 Review Packager, with D-2/D-3 artifacts filed to storage and all numbers crossing into synthesis carried as provenance-bearing `Number` models.
