# M3.6 Risk - Requirements

## Functional Requirements

1. M3.6 must add a `C-6 Risk` Analyst bundle in the future implementation.
2. The bundle must live under `skills/research/risk/`.
3. The bundle must be deterministic and offline in M3.6.
4. The bundle must not call a live LLM.
5. The bundle must not require live LLM credentials.
6. The bundle must not call a real human Senior.
7. M3.6 must not add a new Senior touchpoint.
8. M3.6 must not add or call any `Senior.gate` beyond the existing M3.2 early gate.
9. M3.6 must not call `Senior.ratify`.
10. M3.6 must not implement M3.7 consolidated ratification.
11. M3.6 must not implement final Handoff synthesis.
12. M3.6 must not implement sizing inputs.
13. M3.6 must reuse M3.1 `AnalystDraft`, `EvidenceRef`, `ReviewItem`, and `SeniorReviewPackage`.
14. M3.6 must reuse M3.1 evidence audit.
15. M3.6 must reuse M3.1 no-bare-number audit.
16. M3.6 must reuse M3.3 period-consistency audit.
17. M3.6 must reuse M3.1 Analyst-shaped bundle validation.
18. M3.6 must reuse existing deterministic fake LLM and fake Senior adapters where tests need injected roles.
19. M3.6 must reuse existing filed Business, Moat, CapAlloc, Scenarios, Edge & Cruxes, Gate Card, Method Directive, Spine, Valuation Range, and Expectations Line artifacts where available.
20. M3.6 must not invent a new ratification contract.
21. M3.6 must not invent a new storage interface or persistence path.
22. M3.6 must not duplicate M0 primitive, config, or storage definitions.
23. M3.6 must not introduce new external dependencies.
24. Full M3.6 validation must run without network access.

## Artifact Requirements

25. The Risk artifact must carry a `Header`.
26. The artifact must include ticker and as-of date.
27. The artifact must include source artifact paths or equivalent resolvable references.
28. The artifact must include a pre-mortem draft.
29. The artifact must include a short-seller bear-case narrative draft.
30. The artifact must include a modellable risk register draft.
31. The artifact must include a tail-risk draft.
32. The artifact must include a bear-case value.
33. The artifact must include a kill metric draft.
34. The artifact must include a risk-completeness draft.
35. The artifact must include a source evidence summary.
36. Required source evidence summary fields must not be blank.
37. Required artifact fields must not be placeholder-only strings such as "TODO", "stub", or "not implemented".
38. All judgment-bearing fields must be `AnalystDraft` values or M3.1-compatible nested ratifiable drafts.
39. All Analyst drafts must remain undecided before M3.7.
40. No Analyst draft may carry `decision`, `decided_by`, or `final` in M3.6 output.
41. Each draft must include non-empty evidence refs.
42. Each evidence ref must be resolvable.
43. Each period-specific evidence ref must pass period-consistency audit.
44. Each draft must include Senior checklist area and rationale.
45. Draft payloads must not contain bare numeric values where `Number` is required.
46. Bear-case value must be a `Number`.
47. Bear-case value must include provenance.
48. Bear-case value must include derivation because it is not a filing fact.

## Pre-Mortem Requirements

49. The pre-mortem must be non-empty.
50. The pre-mortem must explain how the investment loses money.
51. The pre-mortem must use a concrete time horizon.
52. The pre-mortem must cite evidence.
53. The pre-mortem must connect to at least one business, financial, scenario, edge, or valuation artifact.
54. Placeholder pre-mortem text must fail audit.
55. Purely bullish or neutral pre-mortems must fail audit.

## Bear-Case Narrative Requirements

56. The bear-case narrative must be non-empty.
57. The bear-case narrative must be written as a credible skeptic or short seller would write it.
58. The bear-case narrative must identify the central mechanism of downside.
59. The bear-case narrative must explain why the downside can persist or compound.
60. The bear-case narrative must cite evidence.
61. The bear-case narrative must connect to the bear scenario, valuation range, business quality, moat, capital allocation, or edge evidence.
62. Empty bear narratives must fail audit.
63. Generic lists of risks without a coherent downside mechanism must fail audit.
64. Unsupported short-seller claims must fail audit.

## Modellable Risk Requirements

65. The modellable risk register must contain one or more risks.
66. Each modellable risk must include a non-empty risk description.
67. Each modellable risk must include impact as `low`, `med`, or `high`.
68. Each modellable risk must include likelihood as `low`, `med`, or `high`.
69. Each modellable risk must include a modeled effect.
70. Each modellable risk must cite evidence.
71. Each modellable risk must be plausibly estimable or scenario-modelled.
72. Empty modellable risk registers must fail audit.
73. Modellable risks without impact must fail audit.
74. Modellable risks without likelihood must fail audit.
75. Modellable risks without modeled effect must fail audit.
76. Modellable risks without evidence must fail audit.

## Tail-Risk Requirements

77. The tail-risk bucket must contain one or more risks.
78. Each tail risk must include a non-empty risk description.
79. Each tail risk must explain why impact-times-likelihood modelling is inappropriate.
80. Each tail risk must include a monitoring signal or evidence gap.
81. Each tail risk must cite evidence or identify an explicit missing-data gap.
82. Tail risks must be stored separately from modellable risks.
83. Tail risks must not carry likelihood scores.
84. Tail risks must not be silently omitted because they are hard to model.
85. Empty tail-risk buckets must fail audit.
86. Tail risks blended into the modellable register must fail audit.
87. Duplicate risk records across modellable and tail buckets must fail audit.

## Bear-Case Value Requirements

88. Bear-case value must be a finite `Number`.
89. Bear-case value must use an allowed valuation unit such as `USD_per_share` or `USD_millions`.
90. Bear-case value must not be a bare numeric payload.
91. Bear-case value must derive from filed scenario, valuation, or mechanical inputs.
92. Bear-case value derivation must include input references.
93. Bear-case value must be auditable back to source Numbers.
94. Bear-case value missing provenance must fail audit.
95. Bear-case value missing derivation must fail audit.
96. Bear-case value with incompatible units must fail audit.
97. Bear-case value disconnected from valuation or scenario evidence must fail audit.

## Kill-Metric Requirements

98. The kill metric must be non-empty.
99. The kill metric must include a metric name.
100. The kill metric must include threshold direction.
101. The kill metric must include threshold value.
102. The kill metric must include an observation window.
103. The kill metric must include a thesis action or consequence.
104. The kill metric must cite evidence.
105. The kill metric must connect to a thesis crux, bear scenario, risk, business driver, or valuation driver.
106. The populated metric, threshold direction, threshold value, and observation window fields are the falsifiability guarantee.
107. Audit must not enforce kill-metric falsifiability by keyword-matching prose.
108. Empty kill metrics must fail audit.
109. Kill metrics missing metric name must fail audit.
110. Kill metrics missing threshold direction must fail audit.
111. Kill metrics missing threshold value must fail audit.
112. Kill metrics missing observation window must fail audit.
113. Kill metrics missing thesis action must fail audit.
114. Kill metrics without evidence must fail audit.

## Risk-Completeness Requirements

115. The risk-completeness draft must state whether the Analyst believes the risk sheet is decision-ready.
116. The risk-completeness draft must identify what could not be verified.
117. The risk-completeness draft must identify what would raise or lower confidence in the downside assessment.
118. The risk-completeness draft must cite evidence or missing-data gaps.
119. The risk-completeness draft must remain ratifiable and undecided.

## Audit-Enforcement Requirements

120. Risk evidence requirements must be enforced by audit checks.
121. Risk structure requirements must be enforced by audit checks.
122. Pre-mortem, bear narrative, risk buckets, bear-case value, kill metric, and risk-completeness requirements must not rely on `prompt.md`.
123. `prompt.md` must carry no enforcement weight.
124. An artifact with unsupported claims must fail audit regardless of prompt contents.
125. An artifact with empty evidence refs must fail audit regardless of prompt contents.
126. An artifact with unresolvable evidence refs must fail audit regardless of prompt contents.
127. Audit failures must be explicit failures, not warnings.
128. There must be no flag-and-pass path for malformed risk support.

## Bundle-Validation Requirements

129. The `C-6 Risk` bundle must pass M3.1 Analyst-shaped bundle validation.
130. The bundle must declare `type: analyst`.
131. The bundle must declare `no_llm: false`.
132. The bundle must declare an LLM dependency.
133. The bundle must declare output shaped as `AnalystDraft` values or an artifact containing `needs_ratification` drafts.
134. The bundle must not declare a bare assertion output contract.
135. The bundle must include `SKILL.md`.
136. The bundle must include `risk.py`.
137. The bundle must include `test_risk.py` or an explicit M3.6 test module under `tests/`.
138. The bundle must include `prompt.md`.
139. The bundle must include `resolver.entry`.
140. The bundle must include `eval/cases.jsonl`.
141. The bundle must include `eval/eval_risk.py`.
142. Bundle validation must fail if `prompt.md` is missing.
143. Bundle validation must fail if eval files are missing.
144. Bundle validation must fail if the output contract is a final assertion instead of ratifiable drafts.
145. Bundle validation must fail if `no_llm` changes to `true`.

## Resolver Requirements

146. M3.6 must wire Risk only after the M3.2 early gate GO path.
147. M3.6 must run Risk after Edge & Cruxes.
148. M3.6 must not run Risk after an M3.2 NO-GO stop.
149. M3.6 must file or return the Risk artifact in the established run artifact path.
150. Filed Risk artifacts must survive storage round-trip.
151. Ratifiable collection must collect Risk drafts as undecided review items.
152. Collected items must remain undecided before M3.7.
153. Resolver wiring must remain deterministic and offline.
154. Resolver wiring must not call `Senior.ratify`.
155. Resolver wiring must not call `Senior.gate` except for the existing M3.2 early gate.

## Non-Functional Requirements

- M3.6 must stay portable and standalone.
- M3.6 validation must run offline.
- M3.6 must not require network access.
- M3.6 must not add external dependencies.
- M3.6 must follow existing pydantic v2 style.
- M3.6 must follow existing storage and audit patterns.
- Runtime state must stay under `/data` or test temp directories.
- Skill code must live under `/skills`.
- Frozen fixtures must live under `tests/fixtures/` or the bundle test fixture surface.
- Failures must be validation, audit, or explicit resolver failures, not warnings.

## Acceptance Criteria

- A valid fixture-backed Risk artifact can be constructed.
- The valid artifact passes Analyst audit.
- The valid artifact collects into a Senior review package.
- Invalid pre-mortem, bear narrative, risk bucket, bear-case value, kill metric, and risk-completeness cases fail closed.
- Tail risks are non-empty and separate from modellable risks.
- Bear-case value is a provenance-complete `Number`.
- Kill-metric falsifiability is enforced by typed fields, not prose keyword checks.
- The resolver reaches Risk only on the GO path and after Edge & Cruxes.
- No Senior ratification occurs.
