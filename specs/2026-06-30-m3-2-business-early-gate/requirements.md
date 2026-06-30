# M3.2 Business And Early Gate — Requirements

## Functional Requirements

1. M3.2 must add a `C-1 Business` Analyst bundle.
2. The Business bundle must live under `skills/research/business/`.
3. The Business bundle must be deterministic and offline in M3.2.
4. The Business bundle must not call a live LLM.
5. The Business bundle must not require live LLM credentials.
6. The Business bundle must not call a real human Senior.
7. The Business bundle must reuse M3.1 `AnalystDraft` and `EvidenceRef` infrastructure.
8. The Business bundle must not invent a new ratifiable draft contract.
9. The Business bundle must not invent a new storage interface or persistence path.
10. The Business artifact must carry a `Header`.
11. The Business artifact must include ticker and as-of date.
12. The Business artifact must include at least one business model summary draft.
13. The Business artifact must include at least one revenue driver or segment mix draft.
14. The Business artifact must include at least one customer or end-market draft.
15. The Business artifact must include at least one explicit Business understanding risk or GO/NO-GO concern.
16. Every Business judgment must be represented as an `AnalystDraft` or M3.1-compatible ratifiable draft.
17. No Business judgment may be represented as a final assertion before Senior action.
18. Every Business draft must have `needs_ratification` semantics.
19. Every Business draft must include non-empty evidence refs.
20. Every Business draft evidence ref must be resolvable by artifact path, filing reference, or external source reference.
21. Every Business draft must include Senior-checklist area and rationale.
22. Every numeric value crossing the Business skill boundary must use `Number`.
23. Any non-fact `Number` crossing the Business skill boundary must carry derivation.
24. The offline drafter must source Business claims from existing artifacts and frozen fixtures.
25. The offline drafter must fail closed if required evidence is missing.
26. The offline drafter must not invent unsupported Business narrative to satisfy output shape.
27. The offline drafter may use deterministic fake LLM adapter output only to exercise the injection seam.
28. Deterministic fake LLM output must be reproducible for identical inputs.
29. M3.2 must wire the Business step into `analyze(ticker)`.
30. The resolver must audit the Business artifact before the early gate.
31. The resolver must call the early gate only after Business audit passes.
32. If Business audit fails, `Senior.gate` must not be called.
33. The resolver must call `Senior.gate` exactly once for a valid run that reaches the early gate.
34. `Senior.gate` must be called after Business and before any downstream M3+ Analyst work.
35. No downstream M3+ Analyst work may run before the early gate decision.
36. A GO decision from `Senior.gate` must allow the resolver to continue.
37. A NO-GO decision from `Senior.gate` must halt the resolver.
38. A NO-GO halt must file a stop artifact.
39. The stop artifact must be schema-valid and headered.
40. The stop artifact must include ticker, as-of date, gate name, gate decision, and gate rationale.
41. The stop artifact must include a pointer to the Business artifact or evidence package that the gate reviewed.
42. The stop artifact must not present a valuation or investment recommendation.
43. The gate result must be filed or otherwise captured as a run artifact for both GO and NO-GO branches.

## Independence Requirements

44. M3.2 must enforce Analyst drafter and Senior independence at gate-wiring time.
45. The Analyst drafter adapter must expose a declared model-family identity in offline tests.
46. The Senior adapter must expose a declared model-family identity in offline tests.
47. Before calling `Senior.gate`, gate wiring must compare the declared Analyst family and Senior family.
48. If the declared Analyst family and Senior family match, gate wiring must fail closed.
49. Same-family wiring failure must happen before any `Senior.gate` call.
50. Same-family wiring failure must not run the gate.
51. Same-family wiring failure must produce an explicit validation or wiring error.
52. If the declared Analyst family and Senior family differ, gate wiring may proceed.
53. Different-family wiring must call `Senior.gate` exactly once when Business audit passes.
54. The family assertion must be based on declared adapter identities, not live model calls.
55. Tests must prove same-family wiring is rejected.
56. Tests must prove same-family wiring rejection leaves `Senior.gate` call count at zero.
57. Tests must prove different-family wiring proceeds.
58. Tests must prove different-family wiring calls `Senior.gate` exactly once.

## Audit-Enforcement Requirements

59. Business draft evidence requirements must be enforced by M3.1 audit checks.
60. Business draft evidence requirements must not rely on `prompt.md`.
61. `prompt.md` must carry no enforcement weight.
62. A Business draft with an unsupported claim must fail audit regardless of prompt contents.
63. A Business draft with empty evidence refs must fail audit regardless of prompt contents.
64. A Business draft with unresolvable evidence refs must fail audit regardless of prompt contents.
65. A Business draft with bare numeric boundary values must fail audit where `Number` is required.
66. A Business draft that asserts final Analyst judgment without Senior decision metadata must fail audit.
67. Audit failures must be explicit failures, not warnings.
68. There must be no flag-and-pass path for unsupported Business claims.
69. There must be no flag-and-pass path for unresolvable Business evidence.

## Bundle-Validation Requirements

70. The `C-1 Business` bundle must pass M3.1 Analyst-shaped bundle validation.
71. The bundle must declare `type: analyst`.
72. The bundle must declare `no_llm: false`.
73. The bundle must declare an LLM dependency.
74. The bundle must declare an output contract shaped as `AnalystDraft` or a Business artifact containing `needs_ratification` drafts.
75. The bundle must not declare a bare assertion output contract.
76. The bundle must include `SKILL.md`.
77. The bundle must include its implementation file, `business.py`.
78. The bundle must include `prompt.md`.
79. The bundle must include `resolver.entry`.
80. The bundle must include `eval/cases.jsonl`.
81. The bundle must include an eval runner, `eval/eval_business.py`.
82. Bundle validation must fail if `prompt.md` is missing.
83. Bundle validation must fail if eval files are missing.
84. Bundle validation must fail if the output contract is a final assertion instead of ratifiable drafts.
85. Bundle validation must fail if the Business bundle declares `no_llm: true`.
86. The triplet and implementation must treat the Business bundle as the first real customer of M3.1 Analyst-shaped bundle validation.

## Offline-Skeleton Guardrail

87. M3.2 must be an offline skeleton, not a stub.
88. The Business artifact must contain concrete draft content derived from inputs.
89. The Business artifact must not contain placeholder-only strings such as "TODO", "stub", or "not implemented" in required draft values.
90. The Business artifact must be useful for a Senior gate decision.
91. The Business artifact must preserve links back to the evidence used by each draft.
92. A test fixture with sufficient Business evidence must produce a valid audited Business artifact.
93. A test fixture with missing required Business evidence must fail closed.
94. A test fixture with malformed evidence references must fail audit.

## Non-Functional Requirements

- M3.2 must stay portable and standalone.
- M3.2 validation must run offline.
- M3.2 must not require network access.
- M3.2 must not add external dependencies.
- M3.2 must follow existing pydantic v2 style.
- M3.2 must follow existing storage and audit patterns.
- Runtime state must stay under `/data` or test temp directories.
- Skill code must live under `/skills`.
- Frozen fixtures must live under `tests/fixtures/` or the bundle test fixture surface.
- Failures must be validation, audit, or explicit wiring failures, not warnings.

## Content And Data Requirements

The deterministic Business drafter must use existing artifacts and frozen evidence sufficient to support:

- what the company sells or does;
- how the company makes money;
- major revenue or segment drivers when available;
- customer, channel, or end-market context when available;
- one explicit concern that the Senior can use for GO/NO-GO.

Acceptable evidence sources in M3.2:

- filed run artifacts produced by existing M1/M2 skills;
- frozen fixture excerpts that simulate business-description evidence;
- existing EDGAR-derived source metadata where available;
- resolver-filed artifacts with stable paths.

Unacceptable evidence behavior:

- claim text with no evidence refs;
- evidence refs that only name a source but provide no trace target;
- evidence refs with blank artifact paths, filing references, or external references;
- prompt-only instructions presented as proof of support;
- invented segment/customer claims not present in fixtures or existing artifacts.

## Artifact Requirements

### Business Artifact

The Business artifact must include:

- `Header`;
- ticker;
- as-of date;
- source artifact summary or source evidence summary;
- business model draft;
- revenue driver or segment mix draft;
- customer or end-market draft;
- Business understanding risk or GO/NO-GO concern draft.

Every draft field must be ratifiable and evidence-backed.

### Early Gate Result

The early gate result must include:

- `Header` or equivalent filed metadata;
- ticker;
- as-of date;
- gate name;
- decision, limited to GO or NO-GO;
- rationale;
- Senior identity;
- pointer to the Business artifact reviewed.

### Stop Artifact

The stop artifact filed on NO-GO must include:

- `Header`;
- ticker;
- as-of date;
- stop reason;
- gate decision;
- gate rationale;
- pointer to the Business artifact reviewed;
- evidence package pointer or summary;
- no Senior ratification package;
- no final investment recommendation.

## Acceptance Criteria

- The M3.2 spec triplet contains only `plan.md`, `requirements.md`, and `validation.md`.
- The `C-1 Business` bundle is specified as an Analyst bundle.
- The Business bundle is specified as deterministic and offline for M3.2.
- Business draft evidence support is enforced by audit, not prompt text.
- The Business bundle must pass M3.1 Analyst-shaped bundle validation.
- Same-family Analyst/Senior gate wiring is rejected before `Senior.gate`.
- Different-family Analyst/Senior gate wiring proceeds.
- `Senior.gate` is called exactly once after audited Business.
- GO branch continues.
- NO-GO branch halts and files a schema-valid stop artifact.
- No live LLM drafting, real Senior call, new contracts, or new persistence are required.
