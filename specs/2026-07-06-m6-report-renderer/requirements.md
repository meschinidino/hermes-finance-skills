# M6 Report Renderer - Requirements

## Functional Requirements

1. M6 must add a deterministic D-5 Report Renderer bundle.
2. D-5 must live under `skills/synthesis/report_renderer/`.
3. D-5 must render from an already-completed storage-relative run directory.
4. D-5 must not be invoked by `analyze()`.
5. D-5 must not change `resolver.py` ticker analysis control flow.
6. D-5 must not add or require a new Senior touchpoint.
7. D-5 must not add or require a new Analyst touchpoint.
8. D-5 must not call an LLM.
9. D-5 must not fetch live market data.
10. D-5 must not mutate source artifacts.
11. D-5 must not change storage schema.
12. D-5 must output Markdown.
13. The default output path must be `report.md` in the completed run directory unless a caller supplies another output path.
14. The renderer must return or print the output path and warnings.
15. The renderer must fail closed when it cannot validate source artifacts.

## Input Requirements

16. The primary Python API input must be a completed storage-relative run directory such as `runs/AAPL/2026-07-03`.
17. A full-report run must contain `final_handoff.json`.
18. A killed-run report must contain `kill_memo.json` and no `final_handoff.json`.
19. A run directory containing both `final_handoff.json` and `kill_memo.json` must be rejected.
20. A run directory containing neither `final_handoff.json` nor `kill_memo.json` must be rejected.
21. The renderer may read `risk.json`, `scenarios.json`, `edge_cruxes.json`, and `route_manifest.json` when present.
22. The renderer must prefer `final_handoff.json` for final ratified content.
23. Auxiliary artifacts must not override final Handoff fields.
24. Auxiliary artifact conflict with the final Handoff must fail closed.
25. The renderer must not require M5 SQLite calibration records.
26. The renderer must not require `route_manifest.json` when `final_handoff.json` is otherwise valid.
27. Host-provided storage adapters must not be required to understand local filesystem paths.
28. The local CLI may accept either `runs/{ticker}/{as_of}` or `data/runs/{ticker}/{as_of}` and normalize to storage-relative form.

## Output Requirements

29. A full Handoff report must include ticker.
30. A full Handoff report must include as-of date.
31. A full Handoff report must include final lean.
32. A full Handoff report must include conviction band.
33. A full Handoff report must include conviction score.
34. A full Handoff report must include valuation method.
35. A full Handoff report must include current price when present in the Handoff.
36. A DCF full Handoff report must include bear, base, and bull values.
37. A non-DCF or method-deferred report must clearly show the method and avoid fake DCF values.
38. A full Handoff report must include key risks.
39. A full Handoff report must include kill metric.
40. A full Handoff report must include tail risks.
41. A full Handoff report must include exactly three falsifiable cruxes.
42. A full Handoff report must include revisit triggers.
43. A full Handoff report must include provenance summary.
44. A full Handoff report must include generated timestamp.
45. A full Handoff report must include terminal source artifact path.
46. A killed-run report must include ticker.
47. A killed-run report must include gate.
48. A killed-run report must include reason.
49. A killed-run report must include generated timestamp.
50. A killed-run report must include source artifact path.
51. A killed-run report must not fabricate valuation, risk, or crux sections.

## Presentation Requirements

52. Filed prose may be rendered verbatim or whitespace-normalized.
53. Structured fields may be lightly reformatted into bullets or Markdown tables.
54. Rendered `Number` values must include units.
55. Rendered dates must use ISO format.
56. Rendered ratifiable fields must use final values, not drafts.
57. Unresolved ratifiable fields in displayed content must be rejected.
58. Missing optional fields must be shown as unavailable only when the schema permits absence.
59. Missing required fields must fail closed.
60. The renderer must not add new thesis claims.
61. The renderer must not add new risk claims.
62. The renderer must not add new cruxes.
63. The renderer must not add new revisit triggers.
64. The renderer must not soften or reinterpret the final lean.

## Valuation Flag Requirements

65. The renderer must detect `price_at_or_below_bear` when price is less than or equal to bear value.
66. The renderer must detect `price_at_or_above_bull` when price is greater than or equal to bull value.
67. The renderer must detect `non_monotonic_scenarios` when bear/base/bull values are not strictly ordered.
68. The renderer must detect `missing_scenario_value` when a required named scenario value cannot render.
69. The renderer must detect `method_deferred` when valuation is route-deferred.
70. Valuation flags must be shown in the report.
71. Valuation flags must be mechanical and must not explain causes beyond the condition.

## Provenance Requirements

72. The provenance summary must count displayed fact Numbers.
73. The provenance summary must count displayed estimate Numbers.
74. The provenance summary must count displayed judgment Numbers.
75. The provenance summary must list source names when available.
76. The provenance summary must list filing forms when available.
77. The provenance summary must list accessions when available.
78. Displayed computed/external values must be identifiable as computed/external.
79. Any displayed `Number` missing provenance after model validation must fail closed.

## CLI/API Requirements

80. M6 must expose a Python function suitable for standalone use.
81. M6 must expose a local CLI path.
82. The CLI must accept a run directory.
83. The CLI must accept an optional output path.
84. The CLI must preserve existing `python -m resolver AAPL` behavior.
85. The CLI must exit non-zero without traceback on invalid input.
86. The CLI must print JSON or concise machine-readable output with `output_path` and warnings.
87. The CLI must not run analysis implicitly when given a run directory.

## Bundle Requirements

88. D-5 must include `SKILL.md`.
89. D-5 must include `report_renderer.py`.
90. D-5 must include focused tests.
91. D-5 must include `resolver.entry`.
92. D-5 must include `__init__.py`.
93. D-5 must not include `prompt.md`.
94. D-5 must not include `eval/`.
95. D-5 `SKILL.md` must be filled from `specs/SKILL-template.md`.
96. D-5 bundle validation must treat the skill as deterministic/accountant-like.

## Non-Goals

- No report generation inside `analyze()`.
- No HTML/PDF in M6.
- No partner delivery workflow.
- No email sending.
- No hosted UI.
- No new storage tables.
- No LLM call.
- No Senior call.
- No Analyst call.
- No new valuation method.
- No changes to M5 calibration/performance behavior.
- No M4.5 insertion work.
