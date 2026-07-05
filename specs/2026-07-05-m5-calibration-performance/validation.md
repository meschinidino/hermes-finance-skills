# M5 Calibration + Performance Reviews - Validation

## Required Commands

Run the standard offline suite:

```text
UV_CACHE_DIR=.uv-cache .venv/bin/uv run --no-sync pytest
```

Run focused D-4 tests:

```text
UV_CACHE_DIR=.uv-cache .venv/bin/uv run --no-sync pytest skills/synthesis/calibration
```

Run resolver smoke tests:

```text
UV_CACHE_DIR=.uv-cache .venv/bin/uv run --no-sync python -m resolver AAPL
UV_CACHE_DIR=.uv-cache .venv/bin/uv run --no-sync python -m resolver MRNA
```

Run local report smoke after seeded or resolver-produced records:

```text
UV_CACHE_DIR=.uv-cache .venv/bin/uv run --no-sync python -m resolver calibration-report
```

Run local review-ingestion smoke with a fixture or generated call id:

```text
UV_CACHE_DIR=.uv-cache .venv/bin/uv run --no-sync python -m resolver calibration-review --json-file <fixture-review.json>
```

If implementation chooses a separate module command instead of resolver subcommands, replace the last two commands with the documented module command and record that decision here.

## Test Checklist

1. `LocalStorage()` creates the old `calibration_log` table and the new typed M5 tables idempotently.
2. Re-instantiating `LocalStorage()` against the same root does not drop calibration rows.
3. `LocalStorage` satisfies the explicit `CalibrationStore` capability.
4. D-4 entry points reject injected storage that lacks `CalibrationStore` methods with a clear capability error.
5. Appending a valid `CalibrationCall` stores typed query columns and full payload JSON.
6. Querying calls returns a pydantic-valid `CalibrationCall`.
7. Duplicate same-payload call append is idempotent or rejected with an explicit duplicate error, matching the implementation decision.
8. Duplicate conflicting call append is rejected.
9. Missing ticker is rejected.
10. Missing run directory is rejected.
11. Missing terminal artifact path is rejected.
12. Missing route manifest path on final-Handoff paths is rejected.
13. Missing lean is rejected.
14. Missing conviction is rejected.
15. Conviction score below 0 is rejected.
16. Conviction score above 10 is rejected.
17. Missing review date is rejected.
18. Missing kill metric is rejected.
19. Missing `run_id` is rejected.
20. Same-ticker same-date resolver reruns produce distinct `run_id` values and distinct calibration call ids.
21. DCF final-Handoff call missing base value is rejected.
22. DCF final-Handoff call missing bear value is rejected.
23. Non-DCF route-deferred call without valuation-deferred reason is rejected if base/bear values are null.
24. Appending a valid `CalibrationReview` stores typed query columns and full payload JSON.
25. Querying reviews returns a pydantic-valid `CalibrationReview`.
26. Review append fails for unknown call id.
27. Review append fails when `what_happened`, `cruxes_held`, and `cruxes_broke` are all empty.
28. Review append fails when a miss has `primary_leak_phase=none`.
29. Review append accepts a hit with `primary_leak_phase=none`.
30. Review append with `supersedes_review_id` fails when the superseded review belongs to a different call id.
31. Review CLI prints JSON for a valid review.
32. Review CLI exits non-zero without traceback on unknown call id.
33. Review CLI exits non-zero without traceback on invalid date.
34. Review CLI exits non-zero without traceback on invalid leak phase.
35. A valid final-Handoff route produces a valid `RouteHealthObservation`.
36. A valid halted route produces a valid `RouteHealthObservation`.
37. Halted route health uses the live `RouteRecorder` snapshot rather than inferring actual steps from artifacts only.
38. Missing expected route step sets routing-correct false.
39. Extra terminal-inconsistent route step sets routing-correct false.
40. Duplicated final lean ratification sets escalation-correct false.
41. Missing final lean ratification on a final-Handoff route sets escalation-correct false.
42. Halted path with a filed final handoff sets routing-correct false.
43. Gate KILL halt maps to the expected halt kind.
44. Business NO-GO halt maps to the expected halt kind.
45. Route audit violation halt maps to the expected halt kind.
46. Identity audit violation halt maps to the expected halt kind.
47. Live Senior API failure halt maps to the expected halt kind.
48. Final lean overturn-without-replacement halt maps to the expected halt kind.
49. AAPL resolver run appends one `CalibrationCall`.
50. AAPL resolver run appends one `RouteHealthObservation`.
51. AAPL resolver run still returns a final Handoff payload.
52. MRNA resolver run appends one `CalibrationCall` with non-DCF route-deferred handling.
53. MRNA resolver run appends one `RouteHealthObservation`.
54. MRNA resolver run still returns a final Handoff or valid terminal payload matching M4c behavior.
55. A forced KillMemo path appends route-health and no calibration call.
56. If calibration append fails after final Handoff construction, `analyze()` fails closed.
57. If route-health append fails, `analyze()` fails closed.
58. Empty analytics report is schema-valid.
59. Empty analytics report has zero counts.
60. Empty analytics report has no division-by-zero errors.
61. Reviewed Low/Med/High calls produce hit-rate buckets with correct denominators.
62. Unreviewed calls increase open review count and do not affect hit-rate denominators.
63. `right_for_the_reasons=true` increments hit numerator.
64. `right_for_the_reasons=false` increments miss/leak counts.
65. Multiple reviews for one call count only the latest non-superseded review in hit-rate, directional-bias, and leak-by-phase analytics.
66. Superseded reviews remain queryable as append-only history.
67. Directional bias groups reviewed calls by lean and outcome direction.
68. Leak-by-phase groups misses by primary leak phase.
69. Routing correctness rate uses route-health observations.
70. Escalation correctness rate uses route-health observations.
71. Report CLI prints JSON.
72. Report CLI handles no records.
73. Report CLI handles seeded fixture records.
74. D-4 bundle has no `prompt.md`.
75. D-4 bundle has no `eval/`.
76. D-4 `SKILL.md` follows `specs/SKILL-template.md`.
77. No live network access is required for the D-4 focused tests.
78. No new dependency is added without justification against `specs/tech-stack.md`.

## Manual Closure Review

Before closing M5, confirm:

1. The implementation is limited to calibration/performance measurement and does not add new Analyst or valuation behavior.
2. The resolver still returns the same terminal payload classes as M4c.
3. Final-Handoff runs cannot silently skip calibration logging.
4. Halted runs cannot silently skip route-health logging.
5. Calibration rows are append-only.
6. Review ingestion is deterministic and local.
7. Analytics are reproducible from SQLite only.
8. Routing and escalation correctness checks measure the existing M4c route evidence rather than inventing a second route definition.
9. Hermes-host outcome ingestion remains out of scope.
10. Live market-price lookback remains out of scope.

## Expected Closure Note

When M5 is complete, update `specs/roadmap.md` with a status line similar to:

```text
**Status:** M5 complete (D-4 Calibration bundle, append-only typed calibration/review/route-health SQLite tables, resolver final-Handoff call logging, halted-route health logging, local review ingestion, deterministic analytics for hit-rate by conviction band, directional bias, leak-by-phase, routing correctness, and escalation correctness). Validated with `UV_CACHE_DIR=.uv-cache .venv/bin/uv run --no-sync pytest`, focused D-4 tests, and resolver AAPL/MRNA smokes.
```
