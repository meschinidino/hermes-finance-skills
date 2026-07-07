# M4.5 Phase 1 Sector-Aware DCF Base Rates - Requirements

## Functional Requirements

1. M4.5 Phase 1 must be spec-first only until explicitly approved for implementation.
2. M4.5 Phase 1 must stop treating one global DCF assumption table as sufficient for every routed DCF company.
3. M4.5 Phase 1 must add a sector-keyed DCF scenario convention surface at `config.dcf.sector_scenarios`.
4. Existing `config.dcf.scenarios` must remain present and unchanged.
5. Existing `config.dcf.scenarios` must remain the fallback for tickers that do not resolve to a known sector scenario block.
6. The fallback path must produce zero behavior change for existing fixture-backed tickers unless they are explicitly tagged into a sector bucket.
7. Existing AAPL fixture behavior must remain unchanged.
8. Existing MRNA fixture behavior must remain unchanged.
9. Existing UBER fixture behavior must remain unchanged in this phase unless the implementation plan is explicitly amended and approved.
10. The first sector block must be SaaS.
11. The SaaS block must be sourced to Aswath Damodaran, NYU Stern, data as of January 2026.
12. The SaaS block must use Damodaran industry category `Software (System & Application)`.
13. The SaaS source metadata must record 309 firms in the Damodaran industry category.
14. The SaaS revenue growth values must be bear `0.06`, base `0.123`, bull `0.20`.
15. The SaaS revenue growth base value must cite Damodaran `Historical Growth Rates by Sector`, expected growth in revenues, next 5 years, for `Software (System & Application)`.
16. The SaaS NOPAT margin values must be bear `0.22`, base `0.326`, bull `0.38`.
17. The SaaS NOPAT margin base value must cite Damodaran `Margins and ROC by Sector`, after-tax operating margin, for `Software (System & Application)`.
18. The SaaS sales-to-capital values must be bear `1.2`, base `1.54`, bull `2.0`.
19. The SaaS sales-to-capital base value must cite Damodaran `Margins and ROC by Sector`, sales/invested capital, for `Software (System & Application)`.
20. The implementation must not impute missing sector drivers.
21. Sector assumptions must carry enough source metadata to generate auditable derivation and `base_rate_check` text.
22. Source metadata must include at minimum source name, source URLs, source date, industry category, firm count, and a short rationale.
23. Source metadata must include `https://pages.stern.nyu.edu/~adamodar/New_Home_Page/datafile/mgnroc.html`.
24. Source metadata must include `https://pages.stern.nyu.edu/~adamodar/New_Home_Page/datafile/histgr.html`.
25. Sector-sourced DCF assumptions must emit `base_rate_check` text naming the sector, source family, source date, and config path.
26. SaaS sector-sourced text must use a label like `SaaS sector base rate - Aswath Damodaran, NYU Stern, Software (System & Application) industry averages, data as of January 2026 - see config.dcf.sector_scenarios.saas`.
27. Sector-sourced text must not use stale generic labels like `Config-backed M2a default`.
28. Global fallback assumptions may keep existing generic labels only when the global fallback is actually used.
29. DCF forward valuation must select assumptions through one explicit resolver function instead of directly indexing `config.dcf.scenarios` at every use site.
30. Reverse DCF must use the same assumption-source selection for its base scenario as forward DCF.
31. The assumption-source selection function must accept the routed method directive or a narrowly equivalent sector key input.
32. The resolver must pass routing context from B-6 Method Router into B-3 DCF when method is `DCF`.
33. If no method directive is available to B-3, B-3 must fall back to the existing global default and flag that no sector context was supplied.
34. The selected assumption source must be visible in DCF artifacts.
35. The selected assumption source must be testable without reading rendered report text.
36. SaaS must be represented with `calibration_sector="saas"` as a separate field from `asset_class`.
37. The implementation must not add `asset_class="saas"`.
38. SaaS companies must remain eligible for `asset_class="cash-generator"` and `method="DCF"` when they meet current B-6 profitability criteria.
39. B-6 must expose `calibration_sector` without breaking the existing method taxonomy.
40. Sector matching must be deterministic.
41. Sector matching must be manually configured per ticker for M4.5 Phase 1.
42. Manual ticker coverage must live under `config.dcf.sector_scenarios.<sector>.tickers`.
43. B-6 must set `calibration_sector` by checking the routed ticker against active `sector_scenarios` ticker coverage.
44. Sector matching must be config-backed, not guessed from ticker names.
45. Sector matching must fail closed when a configured ticker claims a sector whose assumptions are invalid.
46. Sector matching must not use LLM classification.
47. Sector matching must not use live web lookups in offline tests.
48. A new SaaS fixture ticker must be added during implementation.
49. The SaaS ticker must be a real, well-known US-listed SaaS company with clean 10-K data and a subscription-heavy model.
50. The SaaS ticker must not already have a fixture.
51. The SaaS ticker selection must be recorded in the implementation notes with a short reason.
52. Suggested candidates are Salesforce (`CRM`), ServiceNow (`NOW`), Adobe (`ADBE`), Datadog (`DDOG`), or Snowflake (`SNOW`), but the final ticker must be chosen based on clean fixture extraction.
53. The new SaaS fixture must include `company_tickers.json` coverage and companyfacts fixture data.
54. The new SaaS fixture must support the existing EDGAR concept extraction rules or the implementation must add narrowly-scoped concept fallbacks with tests.
55. The SaaS fixture must pass EDGAR extraction, normalization, cost-of-capital, method routing, DCF, scenario, and resolver smoke paths as applicable.
56. The SaaS test must prove routing selects the sector block.
57. The SaaS test must prove the SaaS valuation range differs from the valuation range produced by global defaults for the same company.
58. The SaaS test must compare assumption source selection directly, not just final valuation values.
59. The SaaS test must assert `base_rate_check` source text for revenue growth, NOPAT margin, and sales-to-capital.
60. Existing DCF tests for AAPL must continue to prove global fallback behavior.
61. Existing method-router tests must continue to prove non-SaaS profitable software-like labels do not accidentally become cyclical or optionality.
62. Config validation must reject malformed sector blocks.
63. Config validation must reject missing source metadata for active sector drivers.
64. Config validation must reject sector blocks with missing bear/base/bull values for any active driver.
65. Config validation must reject sector blocks that claim to be active while containing unresolved implementation placeholders.
66. No new runtime dependency may be added.
67. No new server, queue, scheduler, database, or orchestration framework may be added.
68. No Analyst prompt or eval surface may be added for M4.5 Phase 1.
69. No new Senior touchpoint may be added.
70. No live calibration or partner-advisor feedback loop may be added in this phase.
71. Runtime artifacts must remain under `data/`.
72. All `Number` outputs must retain provenance and derivation.
73. Non-fact sector assumption `Number`s must carry derivation that points to the selected config path and source metadata.
74. The implementation must update specs or filing rules only if it changes artifact schema, such as adding `calibration_sector`.

## Resolved Decisions

1. SaaS `sales_to_capital` is resolved with Damodaran `Software (System & Application)` sales/invested capital.
2. SaaS routing uses `calibration_sector="saas"` and does not overload `asset_class`.
3. Sector assignment is manually configured per ticker at `config.dcf.sector_scenarios.<sector>.tickers` for M4.5 Phase 1.
4. SaaS source metadata uses Damodaran `Margins and ROC by Sector` and `Historical Growth Rates by Sector`, data as of January 2026.

## Open Questions Before Implementation

1. Fixture ticker: which SaaS company should be the first golden fixture after checking EDGAR concept cleanliness?

## Non-Goals

- No implementation before spec approval.
- No change to global DCF defaults.
- No behavior change for AAPL, MRNA, or UBER.
- No live finance-advisor calibration loop.
- No LLM-based sector classification.
- No new valuation method.
- No new Senior ratification step.
- No dependency expansion.
