# M3.5 Edge & Cruxes - Requirements

## Functional Requirements

1. M3.5 must add a `C-5 Edge & Cruxes` Analyst bundle.
2. The bundle must live under `skills/research/edge_cruxes/`.
3. The bundle must be deterministic and offline in M3.5.
4. The bundle must not call a live LLM.
5. The bundle must not require live LLM credentials.
6. The bundle must not call a real human Senior.
7. M3.5 must not add a new Senior touchpoint.
8. M3.5 must not call `Senior.gate`.
9. M3.5 must not call `Senior.ratify`.
10. M3.5 must not implement M3.6 Risk.
11. M3.5 must not implement M3.7 consolidated ratification.
12. M3.5 must reuse M3.1 `AnalystDraft`, `EvidenceRef`, `ReviewItem`, and `SeniorReviewPackage`.
13. M3.5 must reuse M3.1 evidence audit.
14. M3.5 must reuse M3.1 no-bare-number audit.
15. M3.5 must reuse M3.3 period-consistency audit.
16. M3.5 must reuse M3.1 Analyst-shaped bundle validation.
17. M3.5 must reuse existing deterministic fake LLM and fake Senior adapters where tests need injected roles.
18. M3.5 must reuse existing filed Business, Moat, CapAlloc, Scenarios, Gate Card, Method Directive, Spine, Valuation Range, and Expectations Line artifacts where available.
19. M3.5 must not invent a new ratification contract.
20. M3.5 must not invent a new storage interface or persistence path.
21. M3.5 must not duplicate M0 primitive, config, or storage definitions.
22. M3.5 must not introduce new external dependencies.
23. Full M3.5 validation must run without network access.

## Artifact Requirements

24. The Edge & Cruxes artifact must carry a `Header`.
25. The artifact must include ticker and as-of date.
26. The artifact must include source artifact paths or equivalent resolvable references.
27. The artifact must include a no-trade steelman draft.
28. The artifact must include a counterparty draft.
29. The artifact must include a structural-mispricing draft.
30. The artifact must include a variant-view draft.
31. The artifact must include catalyst drafts.
32. Edge-asserted artifacts must include exactly three edge-crux drafts.
32a. No-edge/pass artifacts may include zero-or-more pass-falsifier drafts.
33. The artifact must include a source evidence summary.
34. Required source evidence summary fields must not be blank.
35. Required artifact fields must not be placeholder-only strings such as "TODO", "stub", or "not implemented".
36. All judgment-bearing fields must be `AnalystDraft` values or M3.1-compatible nested ratifiable drafts.
37. All Analyst drafts must remain undecided before M3.7.
38. No Analyst draft may carry `decision`, `decided_by`, or `final` in M3.5 output.
39. Each draft must include non-empty evidence refs.
40. Each evidence ref must be resolvable.
41. Each period-specific evidence ref must pass period-consistency audit.
42. Each draft must include Senior checklist area and rationale.
43. Draft payloads must not contain bare numeric values where `Number` is required.

## Steelman Requirements

44. The no-trade steelman must be non-empty.
45. The no-trade steelman must explain why a rational Senior could pass.
46. The no-trade steelman must not be a restatement of the bullish thesis.
47. The no-trade steelman must cite evidence.
48. The no-trade steelman must include at least one downside, uncertainty, opportunity-cost, or market-efficiency argument.
49. Placeholder steelman text must fail audit.

## Counterparty Requirements

50. The counterparty draft must be non-empty.
51. The counterparty draft must identify a plausible holder, seller, short, market participant, or benchmark constraint on the other side.
52. The counterparty draft must explain why that counterparty may reasonably disagree.
53. The counterparty draft must cite evidence.
54. Empty counterparties must fail audit.
55. Counterparties such as "no one", "nobody", "they are dumb", and trivial variants must fail audit.
56. Circular counterparties such as "the market" without mechanism must fail audit.
57. Contemptuous or unsupported counterparties must fail audit.

## Structural Mispricing Requirements

58. The structural-mispricing draft must be non-empty.
59. A structural-mispricing draft that asserts an edge must name a concrete mispricing mechanism explaining why the market price is wrong.
60. A structural-mispricing draft that asserts an edge must name a concrete persistence reason explaining why the mispricing has not corrected.
61. The mispricing mechanism must be evidence-backed.
62. The persistence reason must be evidence-backed.
63. The draft may explicitly use no-structural-edge/pass framing when evidence supports that no durable edge exists.
64. Audit must fail closed when a structural-mispricing draft asserts edge but names no mechanism.
65. Audit must fail closed when a structural-mispricing draft asserts edge but names no persistence reason.
66. Audit must fail closed when the structural-mispricing draft is empty or placeholder-only.
67. Generic "market misunderstands the business" language without a mechanism and persistence reason must fail audit.

## Variant View Requirements

68. The variant-view draft must be non-empty.
69. The variant-view draft must either state an evidence-backed variant view or explicitly state fairly priced/pass.
70. A variant view must identify what the draft believes the market is missing or misweighting.
71. A fairly-priced/pass view must explain why no edge exists.
72. The variant-view draft must cite evidence.
73. Unsupported variant-view claims must fail audit.
74. Generic "market misunderstands the business" language without evidence must fail audit.

## Catalyst Requirements

75. The catalyst draft must include one or more catalysts.
76. Each catalyst must name a concrete event, disclosure, operating data point, capital allocation action, or other observable update.
77. Each catalyst must include timing or observation window.
78. Each catalyst must cite evidence or a source artifact.
79. Generic catalysts such as "market realizes value" must fail audit.
80. Empty catalyst lists must fail audit.

## Crux Requirements

81. An edge-asserted artifact must contain exactly three `edge_crux` records.
82. A no-edge/pass artifact may contain zero-or-more `pass_falsifier` records.
83. A no-edge/pass artifact must reject any `edge_crux` record.
84. An edge-asserted artifact must reject any `pass_falsifier` record.
85. Each filed crux must include a claim.
86. Each filed crux must include a populated `kind` field.
87. Each filed crux must include a populated `metric` field.
88. Each filed crux must include a populated `threshold_direction` field.
89. Each filed crux must include a populated `threshold_value` field.
90. Each filed crux must include a populated `check_by` date field.
91. Each filed crux must cite evidence or identify an explicit missing-data gap.
92. The populated kind, metric, threshold direction, threshold value, and check-by date fields are the falsifiability guarantee.
89. Audit must not enforce crux falsifiability by keyword-matching the crux text.
90. Cruxes must be distinct from one another.
91. Cruxes must connect to the thesis, valuation, scenario, moat, capital-allocation, or business evidence.
96. More than three edge cruxes must fail audit when an edge is asserted.
97. Fewer than three edge cruxes must fail audit when an edge is asserted.
98. A filed crux missing any required falsifiability field must fail audit.
99. Duplicate cruxes must fail audit.

## Audit-Enforcement Requirements

96. Edge & Cruxes evidence requirements must be enforced by audit checks.
97. Edge & Cruxes structure requirements must be enforced by audit checks.
98. Steelman, counterparty, structural-mispricing, variant-view, catalyst, and crux requirements must not rely on `prompt.md`.
99. `prompt.md` must carry no enforcement weight.
100. An artifact with unsupported claims must fail audit regardless of prompt contents.
101. An artifact with empty evidence refs must fail audit regardless of prompt contents.
102. An artifact with unresolvable evidence refs must fail audit regardless of prompt contents.
103. Audit failures must be explicit failures, not warnings.
104. There must be no flag-and-pass path for malformed edge support.

## Bundle-Validation Requirements

105. The `C-5 Edge & Cruxes` bundle must pass M3.1 Analyst-shaped bundle validation.
106. The bundle must declare `type: analyst`.
107. The bundle must declare `no_llm: false`.
108. The bundle must declare an LLM dependency.
109. The bundle must declare output shaped as `AnalystDraft` values or an artifact containing `needs_ratification` drafts.
110. The bundle must not declare a bare assertion output contract.
111. The bundle must include `SKILL.md`.
112. The bundle must include `edge_cruxes.py`.
113. The bundle must include `prompt.md`.
114. The bundle must include `resolver.entry`.
115. The bundle must include `eval/cases.jsonl`.
116. The bundle must include `eval/eval_edge_cruxes.py`.
117. Bundle validation must fail if `prompt.md` is missing.
118. Bundle validation must fail if eval files are missing.
119. Bundle validation must fail if the output contract is a final assertion instead of ratifiable drafts.
120. Bundle validation must fail if `no_llm` changes to `true`.

## Resolver Requirements

121. M3.5 must wire Edge & Cruxes only after the M3.2 early gate GO path.
122. M3.5 must run Edge & Cruxes after Scenarios.
123. M3.5 must not run Edge & Cruxes after an M3.2 NO-GO stop.
124. M3.5 must file or return the Edge & Cruxes artifact in the established run artifact path.
125. Filed Edge & Cruxes artifacts must survive storage round-trip.
126. Ratifiable collection must collect Edge & Cruxes drafts as undecided review items.
127. Collected items must remain undecided before M3.7.
128. Resolver wiring must remain deterministic and offline.

## Non-Functional Requirements

- M3.5 must stay portable and standalone.
- M3.5 validation must run offline.
- M3.5 must not require network access.
- M3.5 must not add external dependencies.
- M3.5 must follow existing pydantic v2 style.
- M3.5 must follow existing storage and audit patterns.
- Runtime state must stay under `/data` or test temp directories.
- Skill code must live under `/skills`.
- Frozen fixtures must live under `tests/fixtures/` or the bundle test fixture surface.
- Failures must be validation, audit, or explicit resolver failures, not warnings.

## Acceptance Criteria

- A valid fixture-backed Edge & Cruxes artifact can be constructed.
- The valid artifact passes Analyst audit.
- The valid artifact collects into a Senior review package.
- Invalid steelman, counterparty, structural-mispricing, variant-view, catalyst, and crux cases fail closed.
- Exactly three edge cruxes are required when an edge is asserted.
- No-edge/pass artifacts may file zero pass-falsifiers, but any filed pass-falsifier must be structurally falsifiable.
- Crux falsifiability is enforced by typed fields, not prose keyword checks.
- The resolver reaches Edge & Cruxes only on the GO path and after Scenarios.
- No Senior ratification occurs.
