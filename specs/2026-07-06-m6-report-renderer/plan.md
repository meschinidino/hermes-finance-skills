# M6 Report Renderer - Plan

## Objective

Add D-5 Report Renderer, a deterministic presentation skill that turns an already-completed run directory into one human-readable Markdown report.

M6 is downstream of analysis. It must not change `analyze()`, add judgment, alter storage schema, or create new Senior/Analyst touchpoints. It re-presents already-ratified Handoff content so partner-facing reports stop being hand-composed.

## Scope

In scope:

- A deterministic D-5 Report Renderer bundle under `skills/synthesis/report_renderer/`.
- A typed report-rendering input that points at a completed storage-relative run directory such as `runs/AAPL/2026-07-03`.
- A Markdown output artifact, defaulting to `report.md` in the same run directory unless the caller supplies an output path.
- A CLI/function entry point that renders from an already-filed run directory.
- Rendering for full `final_handoff.json` runs.
- Rendering for `kill_memo.json` halted runs when the run has no final Handoff.
- DCF valuation display with bear/base/bull values and method metadata.
- Non-DCF and method-deferred valuation display without inventing DCF values.
- Key risks, kill metric, tail risks, exactly three falsifiable cruxes, revisit triggers, and provenance summary.
- Degenerate/anomalous valuation flags, including price at or below bear value, missing scenario values, non-monotonic bear/base/bull values, and method-deferred valuation.
- Tests that prove output text is sourced from filed artifacts and no live LLM or Senior path is used.

## NOT in scope

- No changes to `resolver.py` `analyze()` control flow.
- No automatic invocation as part of `analyze()`.
- No new Senior touchpoint.
- No new Analyst touchpoint.
- No live LLM calls.
- No new claims, flags, thesis language, or investment judgment.
- No storage schema changes.
- No changes to run artifact locations.
- No HTML/PDF generation in M6.
- No report distribution, email sending, partner portal, or hosted UI.
- No re-opening M5 calibration/performance scope.
- No M4.5 domain-calibration insertion.

## What already exists

- `final_handoff.json` is already filed by D-3 Review Packager on successful terminal runs.
- `risk.json`, `scenarios.json`, and `edge_cruxes.json` are already filed before final synthesis.
- `route_manifest.json` and M5 calibration records are already filed downstream of terminal runs, but the renderer must not require SQLite or M5 records to produce the report.
- `Storage.get_json` and `LocalStorage` already read per-run JSON artifacts.
- Pydantic models already exist for `FinalHandoff`, `RiskArtifact`, scenario artifacts, edge/crux artifacts, valuation ranges, `Number`, `Provenance`, and route-deferred valuation.
- Bundle validation already distinguishes deterministic Accountant-like bundles from Analyst bundles. D-5 should follow the deterministic shape: no `prompt.md`, no `eval/`.

## Role and Boundaries

D-5 is deterministic presentation, not judgment.

It may:

- Select fields from final artifacts.
- Reorder final fields into a readable report.
- Format numbers, dates, lists, and provenance references.
- Add mechanical labels such as `Valuation input flag` when a deterministic check detects an anomaly.
- Say a field is unavailable when the filed artifact omits it.

It must not:

- Draft new prose.
- Rewrite thesis language beyond light formatting and section placement.
- Invent explanations for missing or anomalous values.
- Choose, change, or soften the lean.
- Add risk items, cruxes, triggers, or provenance not already filed.
- Read live market data or call an LLM.
- Mutate the source Handoff, risk, scenarios, edge/cruxes, route manifest, or calibration tables.

## Data Flow

```text
completed run directory
  |
  |-- final_handoff.json? ----+
  |-- kill_memo.json? --------|-- D-5 load + validate terminal source
  |-- risk.json? -------------|
  |-- scenarios.json? --------|
  |-- edge_cruxes.json? ------+
  |
  +--> render sections from filed fields only
          |
          |-- ticker / as-of / lean / conviction
          |-- valuation method and bear/base/bull range
          |-- thesis / priced-in / key risks
          |-- kill metric / tail risks
          |-- three falsifiable cruxes
          |-- revisit triggers
          |-- provenance summary
          |-- deterministic valuation input flags
          v
      report.md
```

The renderer should prefer `final_handoff.json` as the canonical source for final, ratified fields. Auxiliary artifacts are allowed only to fill source/provenance summaries or to verify that named final fields trace back to filed artifacts. If auxiliary artifacts conflict with `final_handoff.json`, the report must fail closed instead of choosing a side.

## Proposed API

Implementation should expose a small function surface:

```python
def render_report(
    storage: Storage,
    run_dir: str,
    *,
    output_path: str | None = None,
) -> ReportRenderResult: ...
```

The Python API `run_dir` is storage-relative, matching existing artifact paths such as `runs/AAPL/2026-07-03`. The local CLI may accept either `runs/AAPL/2026-07-03` or `data/runs/AAPL/2026-07-03` and normalize before calling the API. Host-provided storage adapters are not required to understand local filesystem paths.

`ReportRenderResult` should include:

- `run_dir`
- `source_artifacts`
- `output_path`
- `format`, fixed to `markdown`
- `warnings`, limited to deterministic render warnings
- `sections_rendered`

The CLI should follow the existing resolver/module style without changing ticker analysis behavior. Acceptable forms:

```text
UV_CACHE_DIR=.uv-cache .venv/bin/uv run --no-sync python -m resolver render-report --run-dir data/runs/AAPL/2026-07-03
```

or a documented module command:

```text
UV_CACHE_DIR=.uv-cache .venv/bin/uv run --no-sync python -m skills.synthesis.report_renderer --run-dir data/runs/AAPL/2026-07-03
```

If both are easy, prefer the resolver subcommand for operator discoverability. It must remain separate from `python -m resolver AAPL`.

## Report Sections

The Markdown report must contain these sections:

1. Header
   - ticker
   - as-of date
   - report generated timestamp
   - terminal source artifact path
2. Decision
   - final lean
   - conviction band and score
   - review-by date
   - horizon
3. Valuation
   - method
   - price
   - bear/base/bull values when present
   - method-deferred statement when values are unavailable by route
   - deterministic valuation input flags
4. Thesis
   - filed thesis text only
   - whats-priced-in summary from filed expectations content when present
5. Risks
   - kill metric
   - bear-case narrative if filed
   - tail risks
   - modellable risks if present and concise enough for a partner report
6. Falsifiable Cruxes
   - exactly three cruxes from the final Handoff
7. Revisit Triggers
   - `revisit_if` / canonical revisit triggers from the final Handoff
8. Provenance Summary
   - counts of sourced fact, estimate, and judgment Numbers
   - list of source names/forms/accessions available from `data_room.sources`
   - explicit estimated/judgment fields that appear in displayed sections
   - note when a displayed value has computed/external provenance rather than filing provenance

For a killed run, the report should render a short kill report from `kill_memo.json`:

- ticker
- gate
- reason
- source artifact path
- generated timestamp

It must not backfill valuation, risk, or crux sections for killed runs.

## Valuation Flag Rules

Flags are deterministic presentation checks, not investment judgment:

- `price_at_or_below_bear`: current price value is less than or equal to bear scenario value.
- `price_at_or_above_bull`: current price value is greater than or equal to bull scenario value.
- `non_monotonic_scenarios`: bear, base, bull values are not strictly ordered when all three are present.
- `missing_scenario_value`: a named scenario exists but its value cannot be rendered.
- `method_deferred`: final Handoff carries route-deferred valuation rather than bear/base/bull values.
- `missing_provenance_for_displayed_number`: any displayed number lacks valid provenance after model validation. This should normally be impossible; fail closed unless rendering an explicit validation-error report is chosen.

Flags should be shown in a small "Valuation input flags" subsection and should avoid explanatory prose beyond the mechanical condition.

## Rendering Rules

- Use Markdown only.
- Keep all report prose derived from filed fields.
- Use deterministic templates and formatters.
- Quote filed text verbatim when it is already prose, except for whitespace normalization.
- Lightly reformat structured fields into bullets or tables.
- Include units for every rendered `Number`.
- Include dates in ISO format.
- Preserve final Senior-ratified values, not draft values.
- If a ratifiable field has no final value, fail closed.
- If `final_handoff.json` is missing but `kill_memo.json` exists, render the kill report.
- If both final Handoff and KillMemo exist in one run directory, fail closed.
- If neither terminal artifact exists, fail closed.

## File Layout Plan

```text
skills/synthesis/report_renderer/
|-- SKILL.md
|-- __init__.py
|-- report_renderer.py
|-- test_report_renderer.py
`-- resolver.entry
```

No `prompt.md`. No `eval/`.

The `SKILL.md` must be filled from `specs/SKILL-template.md`:

```text
# SKILL: D-5 Report Renderer
type: accountant
triggers: [report_renderer, render_report, d5_report_renderer]
reads: [none]
knowledge: []
inputs: completed run directory containing final_handoff.json or kill_memo.json
outputs: report.md
no_llm: true
```

## Implementation Tasks

1. Define D-5 bundle metadata and deterministic role contract.
2. Add typed render result and warning models.
3. Implement run-directory terminal-source detection.
4. Implement final-Handoff report rendering.
5. Implement kill-memo report rendering.
6. Implement number/date/provenance formatting helpers.
7. Implement valuation flag detection.
8. Add CLI entry point without changing ticker analysis behavior.
9. Add focused unit tests and resolver/module CLI smoke tests.
10. Update docs only if the implementation chooses a non-obvious command form.

## Worktree Parallelization

Sequential implementation, no parallelization opportunity. The core work touches one new bundle plus one small optional CLI hook, and the CLI hook depends on the renderer API shape.

## Failure Modes

- Missing terminal artifact: fail with a clear error and do not create `report.md`.
- Unsupported run-directory path form: fail with a clear error before reading artifacts.
- Both final Handoff and KillMemo present: fail with a clear error and do not choose one.
- Invalid final Handoff JSON: pydantic validation fails and no report is emitted.
- Unresolved ratifiable field in displayed content: fail closed.
- Auxiliary artifact conflicts with final Handoff: fail closed.
- Non-DCF method-deferred run: render method-deferred valuation without fabricating scenario values.
- Degenerate valuation input: render the deterministic flag rather than hiding it.
- Output path unwritable: fail with a clear filesystem/storage error.

## Engineering Review Notes

Plan-eng-review scope challenge:

- Existing code already solves artifact filing, JSON storage, final Handoff validation, KillMemo filing, route manifests, and deterministic bundle validation.
- Minimum viable implementation is one new D-5 bundle plus an optional CLI hook. No storage schema, resolver analysis flow, Senior, Analyst, or LLM path is needed.
- Complexity is below the review threshold: one new bundle and one small command path. Sequential implementation is the right shape.
- `TODOS.md` has calibration follow-ups only; none block this milestone.

Architecture review: 1 issue found and resolved in this spec. The Python API now uses storage-relative run directories while the local CLI may normalize `data/runs/...` filesystem paths, preserving host-storage portability.

Code quality review: no issues found. The planned helpers are mechanical formatters and validators, and the spec keeps them local to D-5 rather than introducing shared abstractions early.

Test review coverage diagram:

```text
CODE PATHS                                      VALIDATION COVERAGE
[+] render_report(storage, run_dir)
  |-- [planned] final_handoff path              tests 11-28, 34-45, 57-60
  |-- [planned] kill_memo path                  tests 29-33
  |-- [planned] missing terminal artifact       tests 5-6
  |-- [planned] conflicting terminal artifacts  test 7
  |-- [planned] invalid source artifacts        tests 8-10
  |-- [planned] auxiliary conflict              test 61
  |-- [planned] run-dir path normalization      tests 64-65
  |-- [planned] output write failure            test 59
  `-- [planned] CLI wrapper                     tests 46-53

USER FLOWS
[+] Operator renders completed DCF run           render-report smoke: AAPL
[+] Operator renders completed non-DCF run       render-report smoke: MRNA
[+] Operator renders killed run                  focused fixture test
[+] Operator passes invalid run-dir              CLI non-zero, no traceback
```

Performance review: no issues found. The renderer reads a handful of small JSON files and writes one Markdown file; no caching or concurrency is warranted.

## Open Implementation Decisions

No product decision is blocked at spec time. The implementation can choose resolver subcommand vs module command as long as it documents and validates the chosen path. Resolver subcommand is preferred for discoverability if the diff stays small.

## GSTACK REVIEW REPORT

| Review | Trigger | Why | Runs | Status | Findings |
|--------|---------|-----|------|--------|----------|
| Eng Review | `/plan-eng-review` | Architecture & tests (required) | 1 | CLEAR | 1 portability issue resolved, 0 critical gaps; downstream-only renderer scope accepted |

- **UNRESOLVED:** 0
- **VERDICT:** ENG CLEARED - ready for spec review.
