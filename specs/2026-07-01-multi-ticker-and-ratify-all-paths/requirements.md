# requirements.md — Multi-Ticker Enablement + Ratify All Paths

## Scope

This slice reopens the M3.7 capstone only to prove the pack is not AAPL-bound before M4 synthesis depends on it. It has two coupled outcomes:

1. The resolver can run fixture-backed end to end for multiple real tickers, including at least one genuine non-DCF route.
2. M3.7 consolidated Senior ratification runs on every GO path, with manifest completeness enforced per method route.

This slice does not start M4 synthesis.

## Workstream A — Multi-Ticker Enablement

1. `fetch_edgar_facts(ticker)` must support at least the target tickers through explicit fixture data when live EDGAR is not available.
2. The local ticker-to-CIK fixture must include every fixture-backed target ticker.
3. Each target ticker must have a matching `{ticker_lower}_companyfacts.json` fixture with enough five-year 10-K data for the existing M1/M2 accountant path.
4. Each EDGAR companyfacts fixture for a real target ticker, especially MRNA, must be derived from actual SEC EDGAR data downloaded once and frozen as a committed fixture.
5. EDGAR companyfacts fixtures must contain real CIKs, real SEC accessions, real fiscal periods, and real reported values; hand-synthesized companyfacts fixtures are not allowed for this proof.
6. If pulling real SEC data is not possible in this environment, implementation must stop and flag the blocker before substituting any synthesized fixture.
7. A synthesized-fixture run, if separately authorized later, must be labeled in validation output as "pipeline executes on non-AAPL-shaped input" and explicitly not as evidence that the audits generalize.
8. The validation report must state which fixture-provenance case applies: real SEC-derived frozen fixture, live SEC run, or explicitly non-proving synthesized input.
9. The target set must include:
   - AAPL as the DCF regression case.
   - One real non-DCF ticker, preferably MRNA or an equivalent biotech/optionality name.
   - One ordinary second DCF ticker if fixture cost is low.
10. If the implementation remains fixture-backed with real SEC-derived fixtures, the spec and validation output must state that this proves frozen-real-data multi-ticker generalization, not live-EDGAR generalization.
11. The slice must not silently add a broad SIC/industry classifier. Per-ticker sector/beta config may remain the source of industry classification, and that limitation must be explicit.
12. `config/conventions.yaml` must include beta/sector entries for each target ticker needed by `_industry_classification()` and `Config.beta_for_ticker()`.
13. The non-DCF target must cause `B-6 Method Router` to select a non-DCF method from the existing method set.
14. A pre-revenue/optionality classification must route to `rNPV` unless the existing router rules intentionally choose another non-DCF method.
15. The non-DCF run must not invoke `B-3 DCF`.
16. The non-DCF run must not file `valuation_range.json` or `expectations_line.json` as fake DCF substitutes.
17. The non-DCF run must still produce substantive stage artifacts for Business, Gate Card, Moat, CapAlloc, Scenarios, Edge/Cruxes, Risk, Senior Review Package, and Senior Decision Package.
18. Non-DCF scenarios must be method-appropriate, not empty schema placeholders. They must include route-specific scenario drivers, evidence refs, and Senior-owned probabilities or clearly defined method-specific probability drafts.
19. Non-DCF edge/cruxes must use the non-DCF route context and must not depend on DCF-only valuation or expectations artifacts.
20. Non-DCF risk must be implemented as a real C-6 artifact on the selected method route, not returned as `risk_deferred`.
21. Non-DCF risk must include a pre-mortem, short/bear case, modellable risks, tail risks, bear-case value or route-appropriate downside anchor, kill metric, and risk completeness draft.
22. Any route-appropriate downside anchor used instead of DCF bear-case value must be a `Number` with provenance and derivation.
23. Analyst evidence fixtures for every target ticker must be ticker-specific and must not reuse AAPL claims, driver names, product language, or risk language unless factually applicable.
24. Analyst evidence fixtures are inherently authored, but they must be traceable to real public information for the ticker, such as actual 10-K risk factors, actual filed business descriptions, actual segment disclosures, actual pipeline/program disclosures, or other cited public sources.
25. Analyst evidence fixtures must not invent business, moat, capital allocation, edge, crux, or risk claims.
26. Validation output must flag analyst evidence fixtures as the weakest link in the generalization proof because they remain authored even when traceable to public information.
27. Analyst fixture loaders must continue to fail closed when a ticker-specific evidence fixture is missing.
28. Price and cost-of-capital paths must either provide fixture/default coverage for the target tickers or fail with a clear audit error during validation.

## Workstream B — Ratify All Paths + Method-Aware Manifest

29. Consolidated M3.7 review aggregation must run after all required review packages for the selected route are built, not only inside the DCF branch.
30. `Senior.ratify` must be called exactly once on every GO path that reaches M3.7, including non-DCF routes.
31. The ratify independence assertion must fire on every GO path: analyst family and Senior family must both be declared and must differ.
32. The non-DCF path must return and persist `senior_review_package.json`.
33. The non-DCF path must return and persist `senior_decision_package.json`.
34. Ratification summary/rate must be present on non-DCF decision packages exactly as on DCF packages.
35. The consolidated manifest must be method-aware.
36. The DCF manifest must require DCF-route sources and review items, including the current gate/business/moat/capalloc/scenarios/edge/risk sources and any DCF-specific review sources that are part of the final route contract.
37. The non-DCF manifest must require the method-appropriate sources for that selected route and must not require DCF-only artifacts that legitimately do not exist.
38. The non-DCF manifest must still require a real C-6 risk review package.
39. The non-DCF manifest must still require the B-6 method directive as part of route completeness, either directly as a source or through a route manifest section that is explicitly audited.
40. Missing a required route source must fail closed during consolidation.
41. Missing review items for a required route source must fail closed during consolidation.
42. The DCF manifest must not be loosened to pass when a DCF-required source or item is missing.
43. The non-DCF manifest must not be loosened to pass when a non-DCF-required source or item is missing.
44. The manifest model or builder must encode route/method identity clearly enough that review failures identify which method contract failed.
45. Manifest required-source construction should be centralized rather than inlined in the middle of `analyze()`.
46. The resolver payload should expose which method-aware manifest contract was used.

## Non-Goals

47. Do not build M4 handoff synthesis.
48. Do not add a broad live SEC ingestion layer unless it is strictly needed and explicitly accepted as part of this slice.
49. Do not add a general SIC/industry classifier in this slice.
50. Do not replace the existing deterministic offline Analyst fixture strategy with live LLM drafting.
51. Do not weaken provenance, `Number`, or Analyst evidence audit rules to make non-DCF pass.
