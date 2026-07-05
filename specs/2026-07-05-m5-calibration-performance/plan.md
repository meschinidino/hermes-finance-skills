# M5 Calibration + Performance Reviews - Plan

## Objective

Implement D-4 Calibration so every terminal analysis run feeds an append-only outcome-quality loop, and so the org can inspect calibration quality, directional bias, process leaks, routing correctness, and escalation correctness over time.

M5 is an accountability and measurement slice. It must not add new valuation methods, new Analyst bundles, new Senior touchpoints, or a server. It turns the existing complete M4c handoff/kill-memo route into durable calibration records and deterministic performance reports.

## Scope

In scope:

- A deterministic D-4 Calibration bundle under `skills/synthesis/calibration/`.
- Typed pydantic models for `CalibrationCall`, `CalibrationReview`, `CalibrationAnalytics`, and route/escalation health summaries.
- Additive SQLite schema in `data/pack.db` for append-only calibration calls, reviews, and route-health observations.
- An explicit `CalibrationStore` capability for appending and querying calibration records, implemented by `LocalStorage`.
- Resolver writes a `CalibrationCall` after every final Handoff.
- Resolver writes a terminal route-health observation after every final Handoff or KillMemo halt.
- A local review-ingestion API and CLI command for recording completed outcomes at review time.
- Analytics for hit-rate by conviction band, directional bias, and leak-by-phase.
- Routing-correctness and escalation-correctness checks derived from the live `RouteRecorder` event snapshot, terminal artifacts, and the documented M4c route table.
- Fixture-backed tests for AAPL final-Handoff calls, MRNA non-DCF final-Handoff calls, KILL/halt routes, manual review ingestion, aggregate analytics, and fail-closed bad records.
- Documentation of the M5 feedback loop in the spec and, if implementation discovers a natural place, in `resolver.md`.

## NOT in scope

- Live market-price lookback or automatic return calculation.
- Hermes-host outcome ingestion.
- Portfolio sizing decisions or realized P&L attribution.
- New Analyst prompts, evals, or LLM behavior.
- New Senior decisions or changes to the constitutionally allowed Senior touchpoint classes.
- New valuation engines.
- Rewriting historical calibration rows.
- Server, queue, scheduler, or external orchestration framework.
- Broad storage replacement beyond additive SQLite helpers.

## What already exists

- `LocalStorage` already owns `data/pack.db`, JSON run artifacts, and the M0 `calibration_log` proof point. M5 should extend that SQLite initialization additively instead of creating a second database path.
- `Storage` already covers run artifact JSON reads/writes. M5 should keep that surface for artifacts and add a separate `CalibrationStore` capability for typed calibration persistence.
- `RouteRecorder`, `RouteEvent`, `DOCUMENTED_ROUTE_STEPS`, and `audit_route_events` already encode M4c route truth. M5 should measure those events instead of rebuilding route rules from scratch.
- `FinalHandoff` and `KillMemo` already define terminal run outcomes. M5 should extract calibration and route-health records from those terminal artifacts plus the live route snapshot.

## Current State

M4c produces either:

- a complete `FinalHandoff` with ticker, price, lean, conviction, conviction score, valuation range or route-deferred valuation, risk kill metric, review date, Senior signer identity, and route manifest; or
- a halted payload with a filed `KillMemo`.

`LocalStorage` currently creates `pack.db` and exposes a generic `append_log("calibration_log", payload)` method backed by a JSON blob table. That proved the storage seam in M0, but M5 needs typed append-only tables and query helpers so analytics can be deterministic.

The filing rules already define the calibration loop conceptually:

```text
CalibrationCall:
  id, date, ticker, lean, conviction, conviction_score,
  base_value, bear_value, review_by, kill_metric

CalibrationReview:
  call_id, reviewed_at, what_happened,
  cruxes_held, cruxes_broke, right_for_the_reasons
```

M5 should implement these as the durable feedback layer, preserving compatibility with existing storage construction.

## Data Model Plan

Add `skills/synthesis/calibration/calibration.py` with pydantic models.

### CalibrationCall

Minimum fields:

- `id`: stable deterministic id that includes `run_id`, e.g. `{ticker}:{as_of}:{run_id}`.
- `run_id`: generated once per `analyze()` invocation and carried into filed run artifacts and D-4 records.
- `schema_version`.
- `date`: handoff `as_of`.
- `ticker`.
- `run_dir`.
- `terminal_artifact_path`: final handoff path.
- `route_manifest_path`.
- `lean`: final Senior-signed lean.
- `conviction`: Low, Med, or High.
- `conviction_score`: integer 0-10 extracted from the existing `Number`.
- `base_value`: numeric value from the base scenario when a valuation range exists.
- `bear_value`: numeric value from the bear scenario or risk bear-case value.
- `review_by`.
- `kill_metric`.
- `method`: selected method or route-deferred method.
- `asset_class`: from the method directive when available.
- `final_lean_signed_by`.
- `final_lean_signed_by_provider`.
- `final_lean_signed_by_model_family`.
- `final_lean_signed_by_model`.
- `created_at`.

Validation rules:

- Final-Handoff calls require a non-empty ticker, run directory, lean, conviction, review date, and kill metric.
- `run_id` is required and must be stable across all artifacts produced by one resolver invocation.
- `conviction_score` must be 0-10.
- `base_value` and `bear_value` must be present for DCF final-Handoff paths.
- Non-DCF route-deferred final-Handoff paths may set valuation values to null only if method routing explains the deferral and the record carries `valuation_deferred_reason`.
- A call id must be unique; duplicate append attempts for the same call id must be idempotent for identical payloads and reject conflicting payloads.
- Same-ticker same-date reruns must produce distinct `run_id` values so reviews can attach to immutable call records.

### CalibrationReview

Minimum fields:

- `id`.
- `call_id`.
- `reviewed_at`.
- `reviewed_by`.
- `outcome_direction`: `up`, `down`, `flat`, or `unknown`.
- `what_happened`.
- `cruxes_held`.
- `cruxes_broke`.
- `right_for_the_reasons`.
- `primary_leak_phase`: one of `P0`, `P1`, `P2`, `P3`, `P4`, `P5`, `P6`, `D2`, `D3`, `route`, `escalation`, or `none`.
- `supersedes_review_id`: optional id of the prior review this row replaces in analytics.
- `notes`.
- `created_at`.

Validation rules:

- `call_id` must resolve to an existing `CalibrationCall`.
- At least one of `cruxes_held`, `cruxes_broke`, or `what_happened` must be non-empty.
- `right_for_the_reasons` is required; `unknown` should be represented by a specific boolean policy rather than omitted. If implementation needs tri-state, the spec must update this field before coding.
- `primary_leak_phase` is required when `right_for_the_reasons` is false.
- Reviews are append-only history, but analytics must use the latest non-superseded review per call so one call cannot be double-counted by correction history.

### RouteHealthObservation

Minimum fields:

- `id`.
- `ticker`.
- `as_of`.
- `run_dir`.
- `terminal_status`: `final_handoff` or `halted`.
- `terminal_artifact_path`.
- `route_manifest_path`.
- `method`.
- `expected_route_steps`.
- `actual_route_steps`: copied from the live `RouteRecorder` event snapshot at terminal time.
- `routing_correct`: boolean.
- `routing_findings`.
- `escalation_correct`: boolean.
- `escalation_findings`.
- `senior_touchpoints`.
- `halt_kind`.
- `created_at`.

Validation rules:

- Every terminal run must record one route-health observation.
- Every route-health observation must receive the live route event snapshot from the resolver path that produced the terminal artifact.
- `routing_correct` must be false if a required step is missing, extra, duplicated, reordered, or produces a terminal artifact inconsistent with the route.
- `escalation_correct` must be false if early gate, consolidated ratification, final lean ratification, route-audit halt, identity-audit halt, or live Senior failure behavior does not match the M4c escalation matrix.
- A route-health observation must not mutate or override `route_manifest.json`; it measures it.

## Storage Plan

Add an explicit calibration persistence capability while keeping the base `Storage` protocol focused on run artifacts.

Preferred API:

```python
class CalibrationStore(Protocol):
    def append_calibration_call(call: CalibrationCall) -> None: ...
    def append_calibration_review(review: CalibrationReview) -> None: ...
    def append_route_health(observation: RouteHealthObservation) -> None: ...
    def list_calibration_calls(...) -> list[CalibrationCall]: ...
    def list_calibration_reviews(...) -> list[CalibrationReview]: ...
    def list_route_health(...) -> list[RouteHealthObservation]: ...
```

`LocalStorage` must implement `Storage` and `CalibrationStore`. D-4 entry points must require the calibration capability explicitly and fail at construction or entry with a clear capability error if the injected storage cannot persist calibration records.

Do not special-case `LocalStorage` inside D-4 helpers. That would preserve standalone tests while hiding a portability trap for host-provided storage adapters.

Concrete capability methods:

```python
append_calibration_call(call: CalibrationCall) -> None
append_calibration_review(review: CalibrationReview) -> None
append_route_health(observation: RouteHealthObservation) -> None
list_calibration_calls(...) -> list[CalibrationCall]
list_calibration_reviews(...) -> list[CalibrationReview]
list_route_health(...) -> list[RouteHealthObservation]
```

SQLite tables should be typed enough for deterministic queries while preserving a full JSON payload for future compatibility:

- `calibration_calls`: `id`, `run_id`, `ticker`, `date`, `review_by`, `lean`, `conviction`, `conviction_score`, `method`, `payload_json`, `created_at`.
- `calibration_reviews`: `id`, `call_id`, `reviewed_at`, `right_for_the_reasons`, `primary_leak_phase`, `outcome_direction`, `supersedes_review_id`, `payload_json`, `created_at`.
- `route_health_observations`: `id`, `run_id`, `ticker`, `as_of`, `terminal_status`, `routing_correct`, `escalation_correct`, `halt_kind`, `payload_json`, `created_at`.

Migrations must be additive and idempotent. The old `calibration_log` table may remain for compatibility, but M5 analytics must use the typed M5 tables.

## Resolver Integration Plan

On final-Handoff paths:

0. Generate one `run_id` per `analyze()` invocation and carry it through filed artifacts and D-4 records.
1. Build the final handoff exactly as M4c does today.
2. File or confirm `final_handoff.json` and `route_manifest.json`.
3. Build and append one `CalibrationCall`.
4. Build and append one `RouteHealthObservation` from the live `RouteRecorder` event snapshot plus terminal artifacts.
5. Return the existing final handoff payload unchanged unless a calibration append fails.

Fail-closed rule:

- If final handoff exists but `CalibrationCall` append fails, `analyze()` must fail rather than silently returning an unmeasured call.
- If route-health append fails, `analyze()` must fail rather than silently returning an unaudited terminal route.

On halted paths:

1. File the `KillMemo` exactly as M4c does today.
2. Pass the live `RouteRecorder` event snapshot into D-4.
3. Build and append one `RouteHealthObservation`.
4. Return the existing halted payload shape.

Halted paths do not produce `CalibrationCall` records unless the implementation introduces a separate `CalibrationTerminal` model. Do not overload call analytics with killed names in M5.

## Review Ingestion Plan

Add a deterministic local entry point for completed outcome reviews:

```python
record_calibration_review(storage, review_payload) -> CalibrationReview
```

Add a CLI mode to `python -m resolver` or a small module command, preferring the repo's existing CLI style:

```text
python -m resolver calibration-review --call-id ... --reviewed-at ... --what-happened ... --right-for-the-reasons true --primary-leak-phase none
```

The CLI must:

- validate the referenced call id exists;
- append a typed review row;
- print JSON for the filed review;
- exit non-zero without traceback on bad call id, invalid phase, invalid date, or missing required fields.

If argument ergonomics become awkward, accept a `--json-file` payload. Do not add an interactive prompt.

## Analytics Plan

Implement a deterministic D-4 analytics function:

```python
build_calibration_analytics(storage, *, as_of=None) -> CalibrationAnalytics
```

Minimum outputs:

- `calls_count`.
- `reviews_count`.
- `open_reviews_count`.
- `hit_rate_by_conviction_band`: for each band, reviewed count and right-for-the-reasons rate.
- `directional_bias`: reviewed counts by final lean and outcome direction.
- `leak_by_phase`: counts grouped by `primary_leak_phase` for reviewed misses.
- `routing_correctness_rate`.
- `escalation_correctness_rate`.
- `routing_findings`.
- `escalation_findings`.
- `generated_at`.

Rules:

- Empty datasets return a schema-valid report with zero counts and empty rates, not division by zero.
- Unreviewed calls are excluded from hit-rate and bias denominators but counted in open reviews.
- `right_for_the_reasons=true` is the hit numerator.
- `right_for_the_reasons=false` contributes to leak-by-phase.
- When multiple reviews exist for one call, hit-rate, directional-bias, and leak-by-phase analytics use the latest non-superseded review per call. Raw review counts may still report total review rows separately.
- Route/escalation rates use route-health observations, including halted paths.

Add a local report command:

```text
python -m resolver calibration-report
```

It should print JSON first. A human-readable table can be a later enhancement.

## Routing And Escalation Correctness Plan

Reuse M4c route semantics; do not create a parallel source of truth.

The D-4 check should compare terminal run evidence against:

- documented route steps from `skills.control_flow.DOCUMENTED_ROUTE_STEPS`;
- route audit expectations already enforced by `audit_route_events`;
- terminal artifact constraints from `FinalHandoff` and `KillMemo`;
- Senior touchpoint classifications in route events.

Minimum checks:

- Final-Handoff DCF path includes required A/B/C/D steps and Senior touchpoints.
- Non-DCF route-deferred path records the method routing decision and does not force plain DCF.
- Gate KILL, business NO-GO, route audit, identity audit, live Senior API failure, and final lean overturn-without-replacement halt cases record the expected halt kind.
- Final-Handoff paths include final lean ratification exactly once.
- Halted paths do not file final handoffs.
- Route audit violations are reported as escalation/routing failures rather than successful routes.

## Skill Bundle Plan

Create `skills/synthesis/calibration/`:

```text
skills/synthesis/calibration/
├── SKILL.md
├── calibration.py
├── test_calibration.py
└── resolver.entry
```

D-4 is deterministic synthesis/accountability work and must not include `prompt.md` or `eval/`.

`SKILL.md` must be filled from `specs/SKILL-template.md` and state:

- role: deterministic synthesis/accountability;
- inputs: final handoff, kill memo, route manifest, storage;
- outputs: calibration call, calibration review, calibration analytics, route-health observation;
- failure: fail closed on invalid or missing terminal evidence.

## Implementation Phases

Full M5 should ship as one milestone, but implementation should be phased so each layer is reviewable.

```text
Phase 1: contracts + storage
  Calibration models -> CalibrationStore -> LocalStorage typed tables

Phase 2: resolver terminal logging
  run_id -> final-Handoff CalibrationCall -> RouteRecorder-backed route health -> halt route health

Phase 3: review ingestion
  record_calibration_review -> validation -> CLI/json-file path

Phase 4: analytics + reporting
  latest-review read model -> hit-rate/bias/leak/route reports -> report CLI

Phase 5: bundle docs + integration validation
  SKILL.md/resolver.entry -> resolver.md docs -> AAPL/MRNA/halts smoke validation
```

## Implementation Steps

1. Add D-4 calibration models and audits.
2. Define a `CalibrationStore` protocol and make `LocalStorage` implement it.
3. Extend `LocalStorage` with additive typed SQLite tables and query helpers.
4. Add per-invocation `run_id` generation and carry it into filed artifacts and D-4 records.
5. Add calibration call extraction from `FinalHandoff`.
6. Add route-health extraction from the live `RouteRecorder` event snapshot plus terminal artifacts.
7. Wire final-Handoff resolver paths to append call and route-health records.
8. Wire halted resolver paths to append route-health records from the live route snapshot.
9. Add `record_calibration_review`, including `supersedes_review_id` support.
10. Add local CLI commands for review ingestion and report generation.
11. Add D-4 analytics aggregation with latest non-superseded review semantics.
12. Create D-4 bundle metadata and resolver entry.
13. Add focused unit tests and resolver integration tests.
14. Update `resolver.md` or adjacent docs to mention the D-4 feedback loop if not already obvious.

## Worktree Parallelization Strategy

M5 has enough independent surface to split after the model names stabilize.

| Step | Modules touched | Depends on |
|------|-----------------|------------|
| Contracts + storage | `skills/synthesis/calibration/`, `skills/storage.py`, `skills/interfaces.py` | — |
| Resolver terminal logging | `resolver.py`, `skills/control_flow.py`, `skills/synthesis/calibration/` | Contracts + storage |
| Review ingestion CLI | `resolver.py` or module CLI, `skills/synthesis/calibration/` | Contracts + storage |
| Analytics/reporting | `skills/synthesis/calibration/` | Contracts + storage, review semantics |
| Bundle/docs/validation | `skills/synthesis/calibration/`, `resolver.md`, `specs/` | All implementation lanes |

Parallel lanes:

- Lane A: Contracts + storage first; this is the shared foundation and should land before parallel work.
- Lane B: Resolver terminal logging after Lane A.
- Lane C: Review ingestion CLI after Lane A.
- Lane D: Analytics/reporting after Lane A.
- Lane E: Bundle/docs/validation after B + C + D.

Execution order: land Lane A, then B + C + D can proceed in parallel worktrees with coordination on `skills/synthesis/calibration/`. Finish with E.

Conflict flags: B, C, and D all touch `skills/synthesis/calibration/`; keep model names and helper signatures frozen after Lane A to avoid merge churn.

## Risks And Decisions

- Calibration must be append-only. Do not "fix" old reviews by updating rows; append a superseding review record if needed.
- Do not hide calibration failures. A final Handoff that was not logged is not fully complete after M5.
- Do not mix killed names into hit-rate denominators unless a separate, explicit killed-name metric is added.
- Do not compute market returns in M5. Review ingestion is manual/local because live price lookback introduces data policy and timing questions outside this milestone.
- Do not create a second route source of truth. D-4 measures M4c route evidence.
- Do not treat `conviction` as self-report only; the report must connect it to reviewed outcomes.

## Expected Result

After M5, `analyze("AAPL")` or `analyze("MRNA")` produces the same final Handoff behavior as M4c and also appends durable calibration and route-health records. A local review can be recorded later against a call id, and a deterministic D-4 report can show hit-rate by conviction band, directional bias, leak-by-phase, routing correctness, and escalation correctness from SQLite without contacting external services.

## GSTACK REVIEW REPORT

| Review | Trigger | Why | Runs | Status | Findings |
|--------|---------|-----|------|--------|----------|
| CEO Review | `/plan-ceo-review` | Scope & strategy | 0 | not run | optional for this backend/spec slice |
| Codex Review | `/codex review` | Independent 2nd opinion | 0 | not run | no outside voice requested |
| Eng Review | `/plan-eng-review` | Architecture & tests (required) | 1 | clear | 5 issues found, 0 critical gaps; accepted phased Full M5, `CalibrationStore`, `run_id`, route-recorder health, latest-review analytics, and added decision tests |
| Design Review | `/plan-design-review` | UI/UX gaps | 0 | not applicable | no UI scope |
| DX Review | `/plan-devex-review` | Developer experience gaps | 0 | not run | local CLI shape reviewed in eng plan |

- **UNRESOLVED:** 0
- **VERDICT:** ENG CLEARED — ready to implement M5.
