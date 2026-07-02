# plan.md — Multi-Ticker Enablement + Ratify All Paths

## Why This Slice Exists

The M3.7 capstone was validated only on AAPL, which follows the DCF branch. A non-AAPL run currently fails before routing because EDGAR is fixture-gated and the ticker index only contains AAPL. The non-DCF branch is also not ratified: consolidated review and Senior decision package construction sit inside the DCF block in `resolver.analyze()`.

M4 synthesis should not build on top of that. This slice proves the resolver can carry more than AAPL and fixes M3.7 so the Senior signs every GO route, not only DCF.

## Current Findings To Preserve

- EDGAR is local-fixture-backed today. `resolve_cik()` reads `skills/data/edgar/fixtures/company_tickers.json`; `fetch_edgar_facts()` then reads `skills/data/edgar/fixtures/{ticker_lower}_companyfacts.json`.
- There is no live SEC fallback in the current EDGAR path.
- The current ticker index contains only AAPL.
- `config/conventions.yaml` contains only one beta/sector mapping: `Computers/Peripherals` with `tickers: ["AAPL"]`.
- `_industry_classification()` raises `missing_industry_classification:{ticker}` if the ticker is absent from config betas.
- Offline Analyst drafters are ticker-fixture-backed for Business, Moat, CapAlloc, Edge/Cruxes, and Risk.
- Existing non-DCF coverage is mostly AAPL data mutated or monkeypatched into optionality in tests, not a real `python -m resolver TICKER` route.
- M3.7 consolidated ratify currently runs only inside `if method_directive.method == "DCF"`.
- The current non-DCF resolver branch returns `valuation_deferred` and `risk_deferred` and exits without `senior_review_package` or `senior_decision_package`.
- The current `ReviewSourceManifest` has only `required_sources`; it is not method-aware.

## Target Tickers

Primary target set:

1. `AAPL`: existing DCF regression.
2. `MRNA`: preferred real non-DCF route. Configure as biotech/optionality so `B-6` selects `rNPV` and DCF is not invoked.
3. Optional second DCF ticker if cheap to fixture, such as `MSFT`, to prove ordinary DCF is not AAPL-only.

MRNA companyfacts fixtures must be real SEC-derived fixtures: download actual EDGAR data once, commit the frozen fixture, and preserve real CIK/accession/period/value data. If real SEC data cannot be pulled in this environment, stop and flag the blocker rather than hand-synthesizing a passing fixture. A synthesized fixture may only be used later with explicit approval and must be labeled as pipeline execution on non-AAPL-shaped input, not as audit generalization evidence.

## Workstream A Plan — Multi-Ticker Enablement

1. Extend EDGAR fixture coverage.
   - Add CIK entries to `company_tickers.json` for the selected target tickers.
   - Add `{ticker_lower}_companyfacts.json` fixtures with enough 10-K concept coverage for the existing `CONCEPT_FALLBACKS`.
   - Source those companyfacts fixtures from actual SEC EDGAR data, frozen after download.
   - Preserve real accessions, fiscal periods, forms, and reported values.
   - Do not hand-author companyfacts rows to satisfy the current audits.
   - Keep `fetch_edgar_facts()` fail-closed on missing concepts.

2. Extend config per ticker.
   - Add beta/sector config for MRNA and the optional second DCF ticker.
   - Keep per-ticker classification explicit; do not implement a broad SIC classifier in this slice.
   - Use an industry string that intentionally exercises router behavior, for example `pre-revenue biotech` or another biotech/optionality label for MRNA.

3. Extend deterministic offline Analyst fixtures.
   - Add ticker-specific Business, Moat, CapAlloc, Edge/Cruxes, and Risk evidence fixtures for every target ticker.
   - The MRNA/non-DCF fixtures must describe the actual route context and must not reuse AAPL-specific product, ecosystem, buyback, services, or installed-base claims.
   - Analyst fixtures are authored, but they must be traceable to real public information: actual 10-K risk factors, filed business descriptions, segment or pipeline/program disclosures, and cited public sources.
   - Treat analyst fixtures as the weakest link in the proof even when they are traceable, because they are not raw SEC companyfacts.
   - Preserve fail-closed behavior for missing fixtures.

4. Make non-DCF scenarios substantive.
   - Replace the current `method_deferred` skeleton for selected non-DCF routes with route-appropriate scenario entries.
   - For `rNPV`, use method-specific drivers such as pipeline/program stage, probability-of-success, addressable patient/population assumption, launch timing, cash runway, dilution/financing need, or equivalent fixture-backed assumptions.
   - Keep DCF-only drivers out of non-DCF scenarios.
   - File ratifiable scenario probability drafts backed by evidence and method-appropriate base-rate/context anchors where available.

5. Make non-DCF risk substantive.
   - Build and audit C-6 Risk on non-DCF routes.
   - Allow route-appropriate downside anchors where DCF bear value is absent, with `Number` provenance and derivation.
   - Remove the resolver-level `risk_deferred` exit as the final behavior for the target non-DCF route.

6. Keep DCF behavior stable.
   - AAPL must still file DCF `valuation_range.json` and `expectations_line.json`.
   - AAPL must still reach M3.7 and produce the same core Senior review/decision package shape.

## Workstream B Plan — Ratify All Paths + Method-Aware Manifest

1. Extract route-completion boundaries.
   - Build all route-required review packages first.
   - After route artifacts are complete, call one shared M3.7 consolidation/ratification block.
   - The shared block receives the selected `method_directive`, route source paths, review packages, Senior, analyst family, and schema version.

2. Build a method-aware manifest contract.
   - Introduce a helper such as `build_review_source_manifest(method_directive, run_dir, paths)` or a richer `RouteReviewManifest`.
   - Include method identity in the manifest.
   - For DCF, require the DCF route's current review-bearing sources and preserve existing completeness guarantees.
   - For non-DCF, require method-appropriate sources: Gate Card, Method Directive, Business, Moat, CapAlloc, Scenarios, Edge/Cruxes, Risk, and any selected-method valuation/scenario artifact that replaces DCF valuation.

3. Fail closed per route.
   - If a DCF-required source or item is missing, consolidation fails.
   - If a non-DCF-required source or item is missing, consolidation fails.
   - Non-DCF should not fail because DCF-only `valuation_range.json` or `expectations_line.json` are absent.
   - DCF should not pass if its DCF-specific route contract is weakened.

4. Move ratification out of the DCF branch.
   - `ratify_review_package()` must run once for every GO path after method-specific artifact construction.
   - The independence check inside `ratify_review_package()` must be exercised on DCF and non-DCF paths.
   - Persist and return `senior_review_package` and `senior_decision_package` on both path types.

5. Make resolver output explicit.
   - Include the selected method directive.
   - Include which route manifest was used.
   - Include Senior ratification summary/rate on non-DCF paths.

## Implementation Notes

- Keep path construction centralized; the current `analyze()` flow has many repeated string paths.
- Avoid treating `method_deferred` as success for the target non-DCF route. This slice is allowed to defer a full valuation engine only if it still produces substantive method-specific scenarios, edge, risk, and ratifiable Senior review.
- Do not add live LLM dependence. Offline fixtures remain acceptable, but they must be ticker-specific and evidence-backed.
- If real SEC companyfacts cannot be pulled, stop before implementation unless the user explicitly approves a non-proving synthesized-input exercise.

## Definition Of Done

- `python -m resolver AAPL` still passes.
- `python -m resolver MRNA` or the selected non-DCF ticker reaches the end, files real artifacts through C-6, and produces Senior review and decision packages.
- The non-DCF method directive selects a non-DCF method and does not invoke DCF.
- The non-DCF artifacts are substantive enough that deleting their required evidence or route source fails validation.
- DCF and non-DCF manifests each fail closed for their own missing route requirements.
- The full test suite passes.
