# M3.4 Scenarios - Requirements

## Functional Requirements

1. M3.4 must add a `C-4 Scenarios` Analyst bundle.
2. The Scenarios bundle must live under `skills/research/scenarios/`.
3. The Scenarios bundle must be deterministic and offline in M3.4.
4. The Scenarios bundle must not call a live LLM.
5. The Scenarios bundle must not require live LLM credentials.
6. The Scenarios bundle must not call a real human Senior.
7. M3.4 must not add a new Senior touchpoint.
8. M3.4 must not call `Senior.ratify`.
9. M3.4 must not implement the M3.7 consolidated ratification flow.
10. M3.4 must reuse M3.1 `AnalystDraft`, `EvidenceRef`, `ReviewItem`, and `SeniorReviewPackage` infrastructure.
11. M3.4 must reuse M3.1 evidence audit.
12. M3.4 must reuse M3.3 period-consistency audit for Analyst evidence refs.
13. M3.4 must reuse M3.1 ratifiable collection unless a contract gap is found.
14. M3.4 must reuse M3.1 Analyst-shaped bundle validation.
15. M3.4 must reuse existing deterministic fake LLM and Senior adapters where tests need injected roles.
16. M3.4 must reuse existing `ValuationRange` and `ExpectationsLine` artifacts.
17. M3.4 must reuse existing `B-5 Base-Rate` behavior and `BaseRateResult`.
18. M3.4 must reuse existing `B-6 Method Router` behavior and `MethodDirective`.
19. M3.4 must not invent a new valuation engine.
20. M3.4 must not invent a new valuation method.
21. M3.4 must not invent a new ratification contract.
22. M3.4 must not invent a new storage interface or persistence path.
23. M3.4 must not duplicate M0 primitive, config, or storage definitions.
24. M3.4 must not introduce new external dependencies.
25. M3.4 may read existing filed artifacts and frozen fixtures as evidence sources.
26. M3.4 must fail closed if required scenario evidence is missing.
27. M3.4 must fail closed if required base-rate anchors are missing or unresolvable.
28. M3.4 must fail closed if method-router evidence is missing or unresolvable.
29. Full M3.4 validation must run without network access.

## Scenario Artifact Requirements

30. The scenario artifact must carry a `Header`.
31. The scenario artifact must include ticker and as-of date.
32. The scenario artifact must include exactly three scenario entries: bear, base, and bull.
33. The scenario entries must preserve the order bear, base, bull.
34. Each scenario entry must include a scenario name.
35. Each scenario entry must include a scenario value using existing `Number` provenance rules.
36. Each scenario entry must include one or more driver-tied assumptions.
37. Each scenario entry must include an independently ratifiable probability draft.
38. Each probability draft must be an `AnalystDraft` or M3.1-compatible nested ratifiable draft.
39. Each probability draft must have `needs_ratification` semantics.
40. No probability draft may be represented as a final Senior decision before M3.7.
41. Each probability draft must carry the probability as a provenance-backed `Number` or an object containing one.
42. No probability draft may carry its probability as a bare float or integer.
43. Each probability draft must include non-empty evidence refs.
44. Each probability draft evidence ref must be resolvable.
45. Each probability draft evidence ref must pass period-consistency audit when period-specific.
46. Each probability draft must include Senior-checklist area and rationale.
47. Scenario probabilities must remain undecided before M3.7.
48. The scenario artifact must include the method directive source path or equivalent resolvable reference.
49. The scenario artifact must include the valuation range source path when DCF is selected.
50. The scenario artifact must include the expectations line source path when DCF is selected and available.
51. The scenario artifact must include source evidence summary sufficient to debug all scenario inputs.
52. Required scenario fields must not be placeholder-only strings such as "TODO", "stub", or "not implemented".

## Multi-Ratifiable Requirements

53. The scenario artifact must contain nested probability drafts at distinct field paths.
54. The collector must emit one `ReviewItem` per scenario probability.
55. The collector must emit distinct stable ids for bear, base, and bull probability review items.
56. Stable ids must remain stable across repeated deterministic runs for the same artifact shape.
57. Each scenario probability review item must preserve its source artifact identity.
58. Each scenario probability review item must preserve its source field path.
59. Each scenario probability review item must preserve evidence refs.
60. Each scenario probability review item must preserve Senior-checklist mapping.
61. Each scenario probability must require its own Senior decision.
62. A package with only the base scenario probability decided must not be marked ratified.
63. A package with only bear and base decided must not be marked ratified.
64. A package may be marked ratified only when every required scenario probability item has a decision.
65. If the current M3.1 collection contract cannot represent one review item per scenario probability, implementation must stop and flag the needed contract change.
66. Implementation must not work around a collection gap by flattening all probabilities into one combined draft.

## Audit-Enforcement Requirements

67. Scenarios evidence requirements must be enforced by audit checks.
68. Scenarios coherence requirements must be enforced by audit checks.
69. Scenarios method-router requirements must be enforced by audit checks.
70. Scenarios base-rate requirements must be enforced by audit checks.
71. Scenarios driver-binding requirements must be enforced by audit checks.
72. Scenarios evidence and coherence requirements must not rely on `prompt.md`.
73. `prompt.md` must carry no enforcement weight.
74. A scenario artifact with unsupported claims must fail audit regardless of prompt contents.
75. A scenario artifact with empty evidence refs must fail audit regardless of prompt contents.
76. A scenario artifact with unresolvable evidence refs must fail audit regardless of prompt contents.
77. A scenario artifact with blank or null evidence trace targets must fail audit.
78. A scenario artifact with bare numeric boundary values must fail audit where `Number` is required.
79. A scenario artifact that asserts final Analyst judgment without Senior decision metadata must fail audit.
80. Audit failures must be explicit failures, not warnings.
81. There must be no flag-and-pass path for malformed scenario support.

## Probability Coherence Requirements

82. Scenario probability drafts must form a coherent distribution.
83. Each scenario probability must be finite.
84. Each scenario probability must be greater than or equal to 0.
85. Each scenario probability must be less than or equal to 1.
86. The sum of bear, base, and bull probabilities must equal 1.0 within a documented tolerance.
87. Audit must reject a distribution such as bear=0.3, base=0.6, bull=0.5.
88. Audit must reject negative probability values.
89. Audit must reject probability values greater than 1.
90. Audit must reject missing probability drafts.
91. Audit must extract probability values from provenance-backed `Number` payloads or objects containing those `Number` values.
92. Audit must reject bare numeric probability drafts before distribution coherence is evaluated.
93. Audit must reject non-numeric draft probability values unless they can be deterministically resolved to the existing ratifiable probability shape without ambiguity.
94. Probability coherence failure must identify the offending condition.

## Value Ordering Requirements

95. Bear-case value must be less than base-case value.
96. Base-case value must be less than bull-case value.
97. Audit must reject bear >= base.
98. Audit must reject base >= bull.
99. Audit must reject equal values between adjacent scenarios.
100. Value ordering must compare the scenario `Number.value` values.
101. Value ordering failure must identify the offending scenario order.

## Driver-Name Binding Requirements

102. Every scenario assumption must name a driver.
103. Every scenario driver must bind to the same driver names consumed by `B-3 DCF` or present in the filed `ExpectationsLine`.
104. Driver-name binding must compare against actual filed valuation artifacts where available.
105. Driver-name binding must not rely only on an unrelated hardcoded allow-list.
106. The valid driver set may be derived from filed `ValuationRange.scenarios[].assumptions[].driver`.
107. The valid driver set may be supplemented from filed `ExpectationsLine.implied` keys where applicable.
108. A scenario assumption tied to an unrecognized driver must fail audit.
109. A decorative scenario driver that does not connect to valuation inputs must fail audit.
110. Driver-name binding failure must identify the invalid driver.
111. Tests must prove driver binding compares against the actual `B-3`/`ExpectationsLine` output shape.

## Base-Rate Anchor Requirements

112. Every scenario assumption must carry a base-rate anchor.
113. The base-rate anchor must reference a `B-5 BaseRateResult`.
114. The base-rate anchor must be resolvable by storage path or equivalent trace target.
115. Audit must load or otherwise resolve the referenced base-rate artifact.
116. Audit must verify the resolved base-rate artifact was produced by `B-5`.
117. Audit must verify the resolved base-rate metric matches the scenario driver being checked when a direct metric mapping exists.
118. Audit must verify the resolved base-rate result carries a probability `Number`.
119. Audit must verify the resolved base-rate result carries a citation.
120. A scenario assumption without a base-rate anchor must fail audit.
121. A scenario assumption with an unresolvable base-rate anchor must fail audit.
122. A scenario assumption whose base-rate anchor resolves to the wrong driver or metric must fail audit.
123. Checking that a string field says "base-rate checked" is insufficient.
124. Base-rate anchor failure must identify the scenario and driver.

## Method-Router Respect Requirements

125. The scenario drafter must consult `B-6 Method Router`.
126. The scenario artifact must reference the method directive used.
127. Audit must resolve the referenced method directive.
128. Audit must verify the resolved method directive was produced by `B-6`.
129. If the method directive selects `DCF`, the scenario artifact may use DCF drivers.
130. If the method directive selects a non-DCF method, the scenario artifact must not impose DCF-specific drivers.
131. If the method directive selects `rNPV`, `SOTP`, `NAV`, `financial_model`, or `normalized_mid_cycle`, the scenario artifact must respect that route.
132. Optionality or pre-revenue names must not be forced into plain DCF.
133. A non-DCF route may produce a deferred scenario artifact with method-appropriate evidence instead of DCF assumptions.
134. Audit must reject a non-DCF method directive paired with DCF-only scenario drivers.
135. Tests must include a fixture that the router classifies as non-DCF.
136. Tests must prove the non-DCF fixture does not force DCF drivers.

## Bundle-Validation Requirements

137. The `C-4 Scenarios` bundle must pass M3.1 Analyst-shaped bundle validation.
138. The bundle must declare `type: analyst`.
139. The bundle must declare `no_llm: false`.
140. The bundle must declare an LLM dependency.
141. The bundle must declare output shaped as `AnalystDraft` values or an artifact containing `needs_ratification` drafts.
142. The bundle must not declare a bare assertion output contract.
143. The bundle must include `SKILL.md`.
144. The bundle must include its implementation file, `scenarios.py`.
145. The bundle must include `prompt.md`.
146. The bundle must include `resolver.entry`.
147. The bundle must include `eval/cases.jsonl`.
148. The bundle must include an eval runner, `eval/eval_scenarios.py`.
149. Bundle validation must fail if `prompt.md` is missing.
150. Bundle validation must fail if eval files are missing.
151. Bundle validation must fail if the output contract is a final assertion instead of ratifiable drafts.
152. Bundle validation must fail if `no_llm` is changed to `true`.

## Resolver Requirements

153. M3.4 must wire Scenarios only after the M3.2 early gate GO path.
154. M3.4 must run Scenarios after Moat and CapAlloc in the GO path.
155. M3.4 must not run Scenarios after an M3.2 NO-GO stop.
156. M3.4 must not call `Senior.gate`.
157. M3.4 must not call `Senior.ratify`.
158. M3.4 must file or return the scenario artifact in the established run artifact path.
159. Filed scenario artifacts must survive storage round-trip.
160. Ratifiable collection must collect scenario probabilities as undecided review items.
161. Collected items must remain undecided before M3.7.
162. Resolver wiring must remain deterministic and offline.

## Non-Functional Requirements

- M3.4 must stay portable and standalone.
- M3.4 validation must run offline.
- M3.4 must not require network access.
- M3.4 must not add external dependencies.
- M3.4 must follow existing pydantic v2 style.
- M3.4 must follow existing storage and audit patterns.
- Runtime state must stay under `/data` or test temp directories.
- Skill code must live under `/skills`.
- Frozen fixtures must live under `tests/fixtures/` or the bundle test fixture surface.
- Failures must be validation, audit, or explicit resolver failures, not warnings.

## Content And Data Requirements

The deterministic Scenarios drafter must use existing artifacts and frozen evidence sufficient to support:

- bear/base/bull scenario values;
- driver-tied assumptions for each scenario;
- base-rate anchors for each assumption;
- probability drafts for each scenario;
- method-router respect;
- checklist mapping for Senior review.

Acceptable evidence sources in M3.4:

- filed run artifacts produced by existing M1/M2/M3 skills;
- filed `ValuationRange` and `ExpectationsLine` artifacts;
- filed or constructed `BaseRateResult` artifacts;
- filed or constructed `MethodDirective` artifacts;
- frozen fixture excerpts that simulate relevant filing or analyst evidence;
- existing EDGAR-derived source metadata where available;
- resolver-filed artifacts with stable paths.

Unacceptable evidence behavior:

- scenario claims with no evidence refs;
- base-rate anchors that are only prose;
- method-router checks that only inspect a copied string;
- evidence refs that only name a source but provide no trace target;
- evidence refs with blank artifact paths, filing references, or external references;
- evidence refs whose claimed period conflicts with the resolved source period;
- prompt-only instructions presented as proof of support.

## Acceptance Criteria

M3.4 is acceptable only when:

- the Scenarios bundle passes M3.1 Analyst validation;
- a valid scenario set constructs and passes audit;
- nested bear/base/bull probability ratifiables collect into distinct review items;
- partial Senior decisions cannot mark the package ratified;
- incoherent probabilities fail audit;
- incorrect value ordering fails audit;
- unbound driver names fail audit;
- missing or unresolvable base-rate anchors fail audit;
- non-DCF method routing is respected;
- resolver GO branch files and collects Scenarios after Moat and CapAlloc;
- no Senior ratify call is made;
- all validation runs offline and deterministically.
