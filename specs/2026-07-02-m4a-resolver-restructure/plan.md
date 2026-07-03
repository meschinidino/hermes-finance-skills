# M4a Resolver Restructure - Plan

## Objective

Replace the current end-of-resolver accretion-payload assembly with a real synthesis boundary while preserving existing behavior.

M4a is a refactor slice only. It prepares the resolver for M4b synthesis skills and M4c control flow, but it must not add final Handoff synthesis, conviction scoring, kill-memo behavior, routing-table orchestration, escalation routing, or new Senior touchpoints.

## Scope

In scope:

- A stable synthesis boundary that accepts filed M0-M3 artifacts and produces the same resolver return payload currently assembled inline.
- A typed or otherwise explicit input contract for the artifacts and paths the synthesis boundary consumes.
- Centralized output assembly for the current D-1 bare handoff plus M2/M3 artifacts.
- Preservation of all current filed artifact paths and payload keys.
- Tests proving `analyze()` output parity for the current AAPL DCF path and MRNA non-DCF path.
- Existing M0-M3 test suite passing unchanged.

Out of scope:

- `D-2 Conviction`.
- `D-3 Review Packager`.
- Full filing-rules `Handoff`.
- New `Handoff` schema fields.
- KILL halt behavior beyond what already exists.
- Routing-table orchestration.
- Escalation matrix behavior.
- Parallel execution.
- Revisit trigger generation.
- Wiring C-5 `pass_falsifiers` into final revisit triggers.
- Upgrading model independence checks.
- New Analyst or Accountant bundles.
- Live LLM behavior.
- Dependency changes.

## Proposed Architecture

```text
analyze(ticker)
   |- existing M0-M3 artifact construction and audits
   |- existing Senior.gate and Senior.ratify behavior
   |- build current synthesis input contract
   `- synthesis boundary assembles today's resolver payload
```

The resolver remains the orchestrator. The new boundary owns only synthesis-adjacent assembly: reading or receiving already-filed artifacts, shaping the current returned payload, and keeping output keys stable.

The boundary should be placed under `skills/synthesis/` unless implementation research finds an established local pattern that strongly points elsewhere. It may wrap the existing D-1 bare handoff, but it must not convert that skeleton into the final M4 Handoff.

## Implementation Steps

1. Capture the current `analyze()` output shape for AAPL and MRNA in focused tests before refactoring.
2. Define a synthesis input contract for current run metadata, method directive, route manifest, artifact paths, and optional DCF paths.
3. Move the inline payload assembly at the end of `analyze()` behind the new synthesis boundary.
4. Keep all existing artifact construction, audit, persistence, and Senior call ordering unchanged.
5. Keep `handoff.json` as the existing D-1 bare handoff artifact.
6. Make the resolver call the boundary only after current M3.7 ratification completes on GO paths.
7. Add tests that compare key sets and representative nested values before and after the boundary, using deterministic fixtures.
8. Run the full offline suite and resolver smoke commands.

## Risks And Decisions

- This slice exists because the resolver currently mixes orchestration with returned-payload assembly. M4b should build on a stable synthesis boundary, not on a large inline dictionary mutation block.
- Output parity matters more than architectural elegance. Any changed payload key, artifact path, Senior call count, or route behavior is a regression unless an existing test is already wrong.
- The boundary should be narrow enough that D-2/D-3 can replace or extend it later without another resolver-wide rewrite.
- M4a must not use this refactor as an opportunity to clean up unrelated M0-M3 behavior.

## Expected Result

After M4a, offline `analyze("AAPL")` and `analyze("MRNA")` return the same payload shape and filed artifacts as before, but final assembly flows through an explicit synthesis boundary that M4b can build on.
