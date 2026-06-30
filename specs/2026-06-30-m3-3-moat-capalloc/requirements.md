# M3.3 Moat And Capital Allocation — Requirements

## Functional Requirements

1. M3.3 must add a `C-2 Moat` Analyst bundle.
2. The Moat bundle must live under `skills/research/moat/`.
3. M3.3 must add a `C-3 CapAlloc` Analyst bundle.
4. The CapAlloc bundle must live under `skills/research/capalloc/`.
5. Both bundles must be deterministic and offline in M3.3.
6. Neither bundle may call a live LLM.
7. Neither bundle may require live LLM credentials.
8. Neither bundle may call a real human Senior.
9. M3.3 must not add a new Senior touchpoint.
10. M3.3 must not wire the consolidated M3.7 `Senior.ratify` flow.
11. M3.3 must reuse M3.1 `AnalystDraft` and `EvidenceRef` infrastructure.
12. M3.3 must reuse M3.1 evidence audit.
13. M3.3 must reuse M3.1 ratifiable collection.
14. M3.3 must reuse M3.1 Analyst-shaped bundle validation.
15. M3.3 must reuse deterministic fake LLM and Senior adapters where tests need injected roles.
16. M3.3 must follow M3.2 offline Analyst bundle patterns.
17. M3.3 must not invent a new ratifiable draft contract.
18. M3.3 must not invent a new storage interface or persistence path.
19. M3.3 must not duplicate M0 primitive, config, or storage definitions.
20. M3.3 must not introduce new external dependencies.
21. M3.3 may read existing filed artifacts and frozen fixtures as evidence sources.
22. M3.3 must fail closed if required evidence is missing.
23. M3.3 must not invent unsupported Moat or CapAlloc narrative to satisfy output shape.
24. Deterministic fake LLM output, if used by either drafter seam, must be reproducible for identical inputs.
25. Full M3.3 validation must run without network access.

## Moat Artifact Requirements

26. The Moat artifact must carry a `Header`.
27. The Moat artifact must include ticker and as-of date.
28. The Moat artifact must include a moat mechanism draft.
29. The moat mechanism draft must identify at least one forward-looking competitive mechanism.
30. Acceptable forward-looking mechanism categories include switching costs, network effects, scale advantage, cost advantage, intangible assets, regulatory position, distribution advantage, or another explicitly evidenced mechanism.
31. The Moat artifact must include historical economics evidence or a historical economics draft.
32. Historical economics evidence may include ROIC spread, WACC spread, margin durability, retention proxy, market share, segment economics, or similar evidence from existing artifacts or fixtures.
33. The Moat artifact must include a durability risk or disconfirming-evidence draft.
34. The Moat artifact must include explicit Senior-checklist mapping for moat strength.
35. The Moat artifact must include explicit Senior-checklist mapping for evidence gaps or durability risks.
36. Every Moat judgment must be represented as an `AnalystDraft` or M3.1-compatible ratifiable draft.
37. No Moat judgment may be represented as a final assertion before Senior action.
38. Every Moat draft must have `needs_ratification` semantics.
39. Every Moat draft must include non-empty evidence refs.
40. Every Moat draft evidence ref must be resolvable by artifact path, filing reference, or external source reference.
41. Every Moat draft must include Senior-checklist area and rationale.
42. Moat drafts must be collected as ratifiables for later Senior review.
43. Collected Moat review items must preserve source artifact identity and source field paths.
44. Collected Moat review items must preserve Senior-checklist mapping.

## Capital Allocation Artifact Requirements

45. The CapAlloc artifact must carry a `Header`.
46. The CapAlloc artifact must include ticker and as-of date.
47. The CapAlloc artifact must include a reinvestment behavior draft.
48. The CapAlloc artifact must include a shareholder-return or dilution behavior draft.
49. The CapAlloc artifact must include a balance-sheet and acquisition discipline draft.
50. The CapAlloc artifact must include explicit Senior-checklist mapping for capital allocation quality.
51. The CapAlloc artifact must include explicit Senior-checklist mapping for evidence gaps or concerns.
52. Every CapAlloc judgment must be represented as an `AnalystDraft` or M3.1-compatible ratifiable draft.
53. No CapAlloc judgment may be represented as a final assertion before Senior action.
54. Every CapAlloc draft must have `needs_ratification` semantics.
55. Every CapAlloc draft must include non-empty evidence refs.
56. Every CapAlloc draft evidence ref must be resolvable by artifact path, filing reference, or external source reference.
57. Every CapAlloc draft must include Senior-checklist area and rationale.
58. CapAlloc drafts must be collected as ratifiables for later Senior review.
59. Collected CapAlloc review items must preserve source artifact identity and source field paths.
60. Collected CapAlloc review items must preserve Senior-checklist mapping.

## Audit-Enforcement Requirements

61. Moat and CapAlloc evidence requirements must be enforced by audit checks.
62. Moat and CapAlloc evidence requirements must not rely on `prompt.md`.
63. `prompt.md` must carry no enforcement weight.
64. A Moat or CapAlloc draft with an unsupported claim must fail audit regardless of prompt contents.
65. A Moat or CapAlloc draft with empty evidence refs must fail audit regardless of prompt contents.
66. A Moat or CapAlloc draft with unresolvable evidence refs must fail audit regardless of prompt contents.
67. A Moat or CapAlloc draft with blank or null evidence trace targets must fail audit.
68. A Moat or CapAlloc draft with bare numeric boundary values must fail audit where `Number` is required.
69. A Moat or CapAlloc draft that asserts final Analyst judgment without Senior decision metadata must fail audit.
70. Audit failures must be explicit failures, not warnings.
71. There must be no flag-and-pass path for unsupported Moat or CapAlloc claims.
72. There must be no flag-and-pass path for unresolvable Moat or CapAlloc evidence.

## Period-Consistency Requirements

73. M3.3 must add fail-closed period-consistency audit for Analyst evidence refs.
74. Period-consistency audit must apply to both Moat and CapAlloc drafts.
75. If an evidence ref claims a fiscal period, audit must compare the claimed period to the resolved source period.
76. If an evidence ref includes attached `Provenance.period`, that period is a claimed period for audit purposes.
77. If an evidence ref includes a period field outside `Provenance`, that period is a claimed period for audit purposes.
78. If the resolved source has a fiscal period, audit must read that resolved source period.
79. Audit must reject a ref whose claimed period is inconsistent with the resolved source period.
80. Audit must reject a ref claiming `FY2025` against an `FY2024` accession or source artifact.
81. Audit must reject a ref claiming a quarterly period against a resolved annual source unless the source metadata explicitly supports that quarter.
82. Audit must not pass period consistency merely because a period field is present.
83. Audit must not pass period consistency merely because the evidence ref resolves.
84. Period mismatch failures must identify the claimed period and resolved source period.
85. Period-consistency audit may allow refs without a claimed period only if the underlying claim does not make a period-specific assertion.
86. Period-specific claims without a claimed period must fail closed.
87. Tests must include a deliberately mismatched evidence ref whose trace target resolves but whose period is wrong.

## Metric-Only Moat Rejection Requirements

88. M3.3 must add fail-closed rejection for metric-only moat durability claims.
89. A Moat draft must fail if it asserts that historical ROIC spread alone proves a moat.
90. A Moat draft must fail if it asserts durability from only historical WACC spread, margin spread, returns, or similar backward-looking economics.
91. A valid moat durability claim must include at least one forward-looking competitive mechanism.
92. A valid moat durability claim must include evidence for the forward-looking competitive mechanism.
93. A valid moat durability claim may cite historical ROIC spread as supporting evidence if it is not the sole support for durability.
94. The metric-only rejection must be structural and support-category based.
95. The metric-only rejection must not depend on keyword matching only the string `ROIC`.
96. The metric-only rejection must reject equivalent phrasing such as returns-above-cost-of-capital alone proving durability.
97. The metric-only rejection must allow historical economics drafts that make no durability assertion.
98. The metric-only rejection must allow drafts that explicitly frame historical spread as evidence to investigate rather than proof of moat.
99. Tests must include the named roadmap case: "historical ROIC spread alone proves a moat" is rejected.
100. Tests must include a non-exact equivalent phrasing to prove the condition is not simple keyword matching.

## Bundle-Validation Requirements

101. The `C-2 Moat` bundle must pass M3.1 Analyst-shaped bundle validation.
102. The `C-3 CapAlloc` bundle must pass M3.1 Analyst-shaped bundle validation.
103. Each bundle must declare `type: analyst`.
104. Each bundle must declare `no_llm: false`.
105. Each bundle must declare an LLM dependency.
106. Each bundle must declare an output contract shaped as `AnalystDraft` or an artifact containing `needs_ratification` drafts.
107. Neither bundle may declare a bare assertion output contract.
108. The Moat bundle must include `SKILL.md`.
109. The Moat bundle must include its implementation file, `moat.py`.
110. The Moat bundle must include `prompt.md`.
111. The Moat bundle must include `resolver.entry`.
112. The Moat bundle must include `eval/cases.jsonl`.
113. The Moat bundle must include an eval runner, `eval/eval_moat.py`.
114. The CapAlloc bundle must include `SKILL.md`.
115. The CapAlloc bundle must include its implementation file, `capalloc.py`.
116. The CapAlloc bundle must include `prompt.md`.
117. The CapAlloc bundle must include `resolver.entry`.
118. The CapAlloc bundle must include `eval/cases.jsonl`.
119. The CapAlloc bundle must include an eval runner, `eval/eval_capalloc.py`.
120. Bundle validation must fail for either bundle if `prompt.md` is missing.
121. Bundle validation must fail for either bundle if eval files are missing.
122. Bundle validation must fail for either bundle if the output contract is a final assertion instead of ratifiable drafts.
123. Bundle validation must fail for either bundle if `no_llm` is changed to `true`.

## Offline-Skeleton Guardrail

124. M3.3 must be an offline skeleton, not a stub.
125. The Moat artifact must contain concrete draft content derived from inputs.
126. The CapAlloc artifact must contain concrete draft content derived from inputs.
127. Required draft values must not be placeholder-only strings such as "TODO", "stub", or "not implemented".
128. Moat drafts must be substantive enough to exercise unsupported-claim, unresolvable-evidence, period-consistency, and metric-only-moat audit paths.
129. CapAlloc drafts must be substantive enough to exercise unsupported-claim, unresolvable-evidence, and period-consistency audit paths.
130. A fixture with sufficient Moat evidence must produce a valid audited Moat artifact.
131. A fixture with sufficient CapAlloc evidence must produce a valid audited CapAlloc artifact.
132. A fixture with missing required Moat evidence must fail closed.
133. A fixture with missing required CapAlloc evidence must fail closed.
134. A fixture with malformed evidence references must fail audit.
135. A fixture with period-mismatched evidence must fail audit.
136. A fixture with metric-only moat support must fail audit.

## Resolver And Collection Requirements

137. M3.3 must wire Moat and CapAlloc only after the M3.2 early gate GO path.
138. M3.3 must not run Moat or CapAlloc after an M3.2 NO-GO stop.
139. M3.3 must not call `Senior.gate`.
140. M3.3 must not call `Senior.ratify`.
141. M3.3 must file or return Moat and CapAlloc artifacts in the established run artifact path.
142. Filed Moat artifacts must survive storage round-trip.
143. Filed CapAlloc artifacts must survive storage round-trip.
144. Ratifiable collection must collect Moat drafts as `needs_ratification` review items.
145. Ratifiable collection must collect CapAlloc drafts as `needs_ratification` review items.
146. Collected items must have stable ids across repeated deterministic runs.
147. Collected items must be mapped to the correct Senior checklist areas.
148. Collected items must remain undecided before M3.7.

## Non-Functional Requirements

- M3.3 must stay portable and standalone.
- M3.3 validation must run offline.
- M3.3 must not require network access.
- M3.3 must not add external dependencies.
- M3.3 must follow existing pydantic v2 style.
- M3.3 must follow existing storage and audit patterns.
- Runtime state must stay under `/data` or test temp directories.
- Skill code must live under `/skills`.
- Frozen fixtures must live under `tests/fixtures/` or the bundle test fixture surface.
- Failures must be validation, audit, or explicit resolver failures, not warnings.

## Content And Data Requirements

The deterministic Moat drafter must use existing artifacts and frozen evidence sufficient to support:

- a named competitive mechanism;
- relevant historical economics without treating those metrics alone as proof of durability;
- a durability risk, counterpoint, or evidence gap;
- checklist mapping for Senior review.

The deterministic CapAlloc drafter must use existing artifacts and frozen evidence sufficient to support:

- reinvestment behavior;
- shareholder returns, dilution, or capital return behavior;
- balance sheet, acquisition, or discipline behavior;
- checklist mapping for Senior review.

Acceptable evidence sources in M3.3:

- filed run artifacts produced by existing M1/M2/M3.2 skills;
- frozen fixture excerpts that simulate 10-K, DEF 14A, proxy, or management commentary evidence;
- existing EDGAR-derived source metadata where available;
- resolver-filed artifacts with stable paths.

Unacceptable evidence behavior:

- claim text with no evidence refs;
- evidence refs that only name a source but provide no trace target;
- evidence refs with blank artifact paths, filing references, or external references;
- evidence refs whose claimed period conflicts with the resolved source period;
- prompt-only instructions presented as proof of support;
- historical spread metrics presented as sole proof of moat durability;
- invented capital allocation or moat claims not present in fixtures or existing artifacts.

## Acceptance Criteria

- The M3.3 spec triplet contains only `plan.md`, `requirements.md`, and `validation.md`.
- `C-2 Moat` and `C-3 CapAlloc` are specified as Analyst bundles.
- Both bundles are deterministic and offline for M3.3.
- Both bundles reuse M3.1/M3.2 infrastructure.
- Moat and CapAlloc evidence support is enforced by audit, not prompt text.
- Both bundles pass M3.1 Analyst-shaped bundle validation.
- Valid Moat and CapAlloc drafts construct, audit, store, and collect as `needs_ratification`.
- Unsupported or unresolvable evidence drafts are rejected.
- Period-mismatched evidence refs are rejected by comparing claimed period to resolved source period.
- Metric-only moat durability claims are rejected structurally.
- No live LLM drafting, new Senior touchpoint, new contracts, new persistence, C-4/C-5/C-6 bundle, or M3.7 ratify behavior is required.

## Pre-Landing Self-Review

- Invariant 1, audit-enforced brakes: Covered by requirements 61-72, 73-87, and 88-100. Prompt files have no enforcement weight.
- Invariant 2, Analyst validator: Covered by requirements 101-123 for both bundles.
- Invariant 3, offline skeleton: Covered by requirements 124-136 and content requirements demanding concrete fixture-derived drafts.
- Invariant 4, period consistency: Covered by requirements 73-87. The required check compares claimed period to resolved source period, not just field presence.
- Invariant 5, unsupported moat rejection: Covered by requirements 88-100. The required check is support-category based and includes non-exact phrasing, not keyword matching on `ROIC`.
- Validation cases requested by the milestone are represented in the validation plan.
- The residual quality of moat and capital allocation inference is explicitly Senior-owned; audit does not claim to certify judgment quality.
- No scoped-out behavior is waved through: live LLM, C-4/C-5/C-6, M3.7 ratify, second Senior touchpoint, routing escalation changes, new contracts, and new persistence remain out.
