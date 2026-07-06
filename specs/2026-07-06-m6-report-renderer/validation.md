# M6 Report Renderer - Validation

## Required Commands

Run the standard offline suite:

```text
UV_CACHE_DIR=.uv-cache .venv/bin/uv run --no-sync pytest
```

Run focused D-5 tests:

```text
UV_CACHE_DIR=.uv-cache .venv/bin/uv run --no-sync pytest skills/synthesis/report_renderer
```

Run existing resolver smoke tests to prove ticker behavior did not change:

```text
UV_CACHE_DIR=.uv-cache .venv/bin/uv run --no-sync python -m resolver AAPL
UV_CACHE_DIR=.uv-cache .venv/bin/uv run --no-sync python -m resolver MRNA
```

Run report-render smoke tests against completed fixture or generated run directories:

```text
UV_CACHE_DIR=.uv-cache .venv/bin/uv run --no-sync python -m resolver render-report --run-dir data/runs/AAPL/2026-07-03
UV_CACHE_DIR=.uv-cache .venv/bin/uv run --no-sync python -m resolver render-report --run-dir data/runs/MRNA/2026-07-03
```

If implementation chooses a module command instead of a resolver subcommand, replace the render-report commands with the documented module command and record that decision here.

## Test Checklist

1. The D-5 bundle passes deterministic/accountant-like bundle validation.
2. The D-5 bundle has no `prompt.md`.
3. The D-5 bundle has no `eval/`.
4. The D-5 `SKILL.md` follows `specs/SKILL-template.md`.
5. Rendering rejects an empty run directory.
6. Rendering rejects a run directory with neither `final_handoff.json` nor `kill_memo.json`.
7. Rendering rejects a run directory with both `final_handoff.json` and `kill_memo.json`.
8. Rendering rejects invalid `final_handoff.json`.
9. Rendering rejects unresolved ratifiable fields in displayed content.
10. Rendering rejects displayed Numbers with missing provenance after model validation.
11. Rendering a valid DCF final Handoff writes `report.md`.
12. DCF report contains ticker.
13. DCF report contains final lean.
14. DCF report contains conviction band and score.
15. DCF report contains price.
16. DCF report contains bear/base/bull values.
17. DCF report contains valuation method.
18. DCF report contains kill metric.
19. DCF report contains tail risks.
20. DCF report contains exactly three cruxes.
21. DCF report contains revisit triggers.
22. DCF report contains provenance summary.
23. DCF report uses final ratified values rather than draft values.
24. DCF report does not include text absent from filed source artifacts except fixed section labels and mechanical flag labels.
25. Rendering a valid non-DCF or method-deferred final Handoff writes `report.md`.
26. Non-DCF report contains method.
27. Non-DCF report does not fabricate bear/base/bull DCF values.
28. Non-DCF report shows `method_deferred` when valuation values are deferred.
29. Rendering a valid KillMemo writes a kill report.
30. Kill report contains ticker.
31. Kill report contains gate.
32. Kill report contains reason.
33. Kill report does not include valuation/risk/crux sections.
34. `price_at_or_below_bear` appears when price is equal to bear value.
35. `price_at_or_below_bear` appears when price is below bear value.
36. `price_at_or_above_bull` appears when price is above bull value.
37. `non_monotonic_scenarios` appears when bear/base/bull are not strictly ordered.
38. `missing_scenario_value` appears when a named scenario value cannot be rendered.
39. No valuation flags appear for normal ordered bear/base/bull values with price inside range.
40. Provenance summary counts displayed fact Numbers.
41. Provenance summary counts displayed estimate Numbers.
42. Provenance summary counts displayed judgment Numbers.
43. Provenance summary lists source names where available.
44. Provenance summary lists filing forms where available.
45. Provenance summary lists accessions where available.
46. CLI accepts `--run-dir`.
47. CLI accepts `--output-path`.
48. CLI exits non-zero without traceback on invalid run directory.
49. CLI prints output path and warnings.
50. CLI does not trigger `analyze()`.
51. Existing `python -m resolver AAPL` behavior remains unchanged.
52. Existing `python -m resolver MRNA` behavior remains unchanged.
53. No live network access is required for focused D-5 tests.
54. No live LLM adapter is used or required.
55. No Senior adapter is used or required.
56. No new storage table is created by rendering.
57. Source artifacts are not mutated during rendering.
58. Custom output path writes report to that path.
59. Unwritable output path fails clearly.
60. Re-rendering the same run is deterministic except generated timestamp if included.
61. Auxiliary artifact conflict with final Handoff fails closed.
62. Rendering a final Handoff does not require M5 SQLite calibration records.
63. Rendering a final Handoff does not require `route_manifest.json`.
64. Python API accepts storage-relative run directory such as `runs/AAPL/2026-07-03`.
65. Local CLI accepts and normalizes filesystem run directory such as `data/runs/AAPL/2026-07-03`.

## Manual Closure Review

Before closing M6, confirm:

1. Rendering remains optional and downstream of completed runs.
2. `analyze()` does not invoke D-5.
3. The report contains only filed final content plus deterministic labels/formatting.
4. DCF and non-DCF Handoffs both produce useful reports.
5. KillMemo runs produce short kill reports only.
6. Degenerate valuation inputs are visible in the report.
7. The provenance summary distinguishes filing-sourced facts from computed/external/estimated fields.
8. No LLM, Senior, Analyst, network, or storage schema path was added.

## Expected Closure Note

When M6 is complete, update `specs/roadmap.md` with a status line similar to:

```text
**Status:** M6 complete (D-5 Report Renderer bundle, deterministic Markdown report generation from completed run directories, full-Handoff and KillMemo rendering, DCF and method-deferred valuation handling, valuation input flags, provenance summary, and CLI/API entry point). Validated with `UV_CACHE_DIR=.uv-cache .venv/bin/uv run --no-sync pytest`, focused D-5 tests, resolver AAPL/MRNA smokes, and report-render smokes.
```
