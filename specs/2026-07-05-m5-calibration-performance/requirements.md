# M5 Calibration + Performance Reviews - Requirements

## Functional Requirements

1. M5 must add a deterministic D-4 Calibration bundle.
2. D-4 must not call an LLM.
3. D-4 must not add a new Senior touchpoint.
4. D-4 must not add a new valuation method.
5. D-4 must not introduce a server, queue, scheduler, or external orchestration framework.
6. Final-Handoff runs must append one `CalibrationCall`.
7. Final-Handoff runs must append one `RouteHealthObservation`.
8. Halted runs must append one `RouteHealthObservation`.
9. Halted runs must not append `CalibrationCall` records in M5.
10. A final Handoff must not be returned silently if its `CalibrationCall` append fails.
11. A terminal run must not be returned silently if its route-health append fails.
12. Calibration storage must be append-only.
13. Calibration storage migrations must be additive and idempotent.
14. Existing `LocalStorage()` construction must continue to create `pack.db`.
15. Existing JSON run artifacts must remain under `data/runs/{ticker}/{as_of}/`.
16. Existing final-Handoff and KillMemo payload shapes must remain backward-compatible unless this spec explicitly requires additive fields.
17. M5 must add an explicit `CalibrationStore` protocol or equivalent typed capability separate from the base artifact `Storage` protocol.
18. D-4 must fail with a clear capability error when injected storage cannot persist calibration records.
19. M5 must generate one `run_id` per `analyze()` invocation.
20. `run_id` must be carried into filed artifacts or terminal metadata where D-4 can read it.
21. Same-ticker same-date reruns must produce distinct calibration call ids.
22. Route-health creation must receive the live `RouteRecorder` event snapshot on final-Handoff and halted paths.

## CalibrationCall Requirements

23. `CalibrationCall` must include a unique id.
24. `CalibrationCall` must include `run_id`.
25. `CalibrationCall` must include schema version.
26. `CalibrationCall` must include date.
27. `CalibrationCall` must include ticker.
28. `CalibrationCall` must include run directory.
29. `CalibrationCall` must include terminal artifact path.
30. `CalibrationCall` must include route manifest path.
31. `CalibrationCall` must include final lean.
32. `CalibrationCall` must include conviction band.
33. `CalibrationCall` must include conviction score as an integer 0-10.
34. `CalibrationCall` must include review date.
35. `CalibrationCall` must include kill metric.
36. `CalibrationCall` must include valuation method.
37. `CalibrationCall` must include Senior signer provider, model family, and model.
38. DCF final-Handoff `CalibrationCall` records must include base value.
39. DCF final-Handoff `CalibrationCall` records must include bear value.
40. Non-DCF route-deferred calls may omit base and bear values only when they include a valuation-deferred reason.
41. Duplicate call ids with identical payloads must be idempotent or clearly rejected as duplicates.
42. Duplicate call ids with conflicting payloads must be rejected.
43. Invalid conviction scores must be rejected.
44. Missing final lean must be rejected.
45. Missing review date must be rejected.
46. Missing kill metric must be rejected.
47. Missing `run_id` must be rejected.

## CalibrationReview Requirements

48. M5 must provide a local deterministic API for appending completed reviews.
49. M5 must provide a CLI path for appending completed reviews.
50. `CalibrationReview` must include a unique id.
51. `CalibrationReview` must include call id.
52. `CalibrationReview` must include reviewed-at date.
53. `CalibrationReview` must include reviewer identity or label.
54. `CalibrationReview` must include outcome direction.
55. `CalibrationReview` must include what happened.
56. `CalibrationReview` must include cruxes held.
57. `CalibrationReview` must include cruxes broken.
58. `CalibrationReview` must include `right_for_the_reasons`.
59. `CalibrationReview` must include primary leak phase.
60. `CalibrationReview` must include optional `supersedes_review_id`.
61. Review append must fail if the referenced call id does not exist.
62. Review append must fail if `what_happened`, `cruxes_held`, and `cruxes_broke` are all empty.
63. Review append must fail if `right_for_the_reasons` is false and `primary_leak_phase` is missing or `none`.
64. Review append must fail if `supersedes_review_id` is provided and does not resolve to a review for the same call id.
65. Review append CLI must print JSON for the filed review.
66. Review append CLI must exit non-zero without traceback on invalid input.

## RouteHealthObservation Requirements

67. `RouteHealthObservation` must include a unique id.
68. `RouteHealthObservation` must include `run_id` when available.
69. `RouteHealthObservation` must include ticker.
70. `RouteHealthObservation` must include as-of date.
71. `RouteHealthObservation` must include run directory.
72. `RouteHealthObservation` must include terminal status.
73. `RouteHealthObservation` must include terminal artifact path.
74. `RouteHealthObservation` must include route manifest path when a route manifest exists.
75. `RouteHealthObservation` must include expected route steps.
76. `RouteHealthObservation` must include actual route steps from the live `RouteRecorder` event snapshot.
77. `RouteHealthObservation` must include routing-correct boolean.
78. `RouteHealthObservation` must include routing findings.
79. `RouteHealthObservation` must include escalation-correct boolean.
80. `RouteHealthObservation` must include escalation findings.
81. `RouteHealthObservation` must include Senior touchpoints.
82. Halted route-health records must include halt kind.
83. Missing required route steps must set routing-correct to false.
84. Extra terminal-inconsistent route steps must set routing-correct to false.
85. Final-Handoff paths missing final lean ratification must set escalation-correct to false.
86. Final-Handoff paths with duplicate final lean ratification must set escalation-correct to false.
87. Halted paths that file final handoffs must set routing-correct to false.
88. Halt kinds inconsistent with M4c escalation behavior must set escalation-correct to false.

## Analytics Requirements

89. M5 must provide a deterministic `CalibrationAnalytics` report.
90. Analytics must include call count.
91. Analytics must include review count.
92. Analytics must include open review count.
93. Analytics must include hit-rate by conviction band.
94. Analytics must include directional bias.
95. Analytics must include leak-by-phase.
96. Analytics must include routing correctness rate.
97. Analytics must include escalation correctness rate.
98. Analytics must include routing findings.
99. Analytics must include escalation findings.
100. Empty datasets must return a schema-valid report.
101. Empty datasets must not divide by zero.
102. Unreviewed calls must be excluded from hit-rate denominators.
103. Unreviewed calls must be counted in open reviews.
104. `right_for_the_reasons=true` must count as a hit.
105. `right_for_the_reasons=false` must count as a miss and contribute to leak-by-phase.
106. When multiple reviews exist for a call, hit-rate, directional-bias, and leak-by-phase analytics must use the latest non-superseded review per call.
107. Route and escalation correctness rates must use route-health observations.
108. A local report command must print JSON analytics.

## Storage Requirements

109. M5 must add typed SQLite tables for calibration calls.
110. M5 must add typed SQLite tables for calibration reviews.
111. M5 must add typed SQLite tables for route-health observations.
112. Each typed table must preserve full payload JSON.
113. Query helpers must return typed pydantic models or model-compatible dicts.
114. The old generic `calibration_log` table may remain.
115. M5 analytics must not depend on the old generic `calibration_log` table.
116. Storage APIs must keep host portability; no direct Hermes database usage is allowed.

## Resolver Requirements

117. Resolver final-Handoff paths must append calibration after final-Handoff evidence exists.
118. Resolver final-Handoff paths must append route-health after route evidence exists.
119. Resolver halted paths must append route-health after KillMemo evidence exists.
120. Resolver return payload for successful final-Handoff paths must remain the final handoff payload.
121. Resolver return payload for halted paths must remain the halted payload.
122. Resolver CLI must keep existing ticker behavior.
123. Resolver CLI must support review ingestion or delegate it to a clearly documented module command.
124. Resolver CLI must support calibration report generation or delegate it to a clearly documented module command.

## Bundle Requirements

125. D-4 must live under `skills/synthesis/calibration/`.
126. D-4 must include `SKILL.md`.
127. D-4 must include `calibration.py`.
128. D-4 must include focused tests.
129. D-4 must include `resolver.entry`.
130. D-4 must not include `prompt.md`.
131. D-4 must not include `eval/`.
132. D-4 `SKILL.md` must be filled from `specs/SKILL-template.md`.

## Non-Goals

- No live price lookback.
- No automatic realized return calculation.
- No Hermes-host ingestion in M5.
- No portfolio sizing decision.
- No new Analyst bundle.
- No LLM prompt or eval.
- No new Senior sign-off.
- No new valuation engine.
- No historical row rewrite.
- No server, queue, scheduler, or orchestration framework.
