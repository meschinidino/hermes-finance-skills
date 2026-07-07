# M4.5 Phase 1 Sector-Aware DCF Base Rates - Validation

## Spec-Only Validation

Before implementation approval, confirm:

1. The spec explicitly keeps `config.dcf.scenarios` unchanged.
2. The spec explicitly adds `config.dcf.sector_scenarios` as additive config.
3. The spec includes sourced SaaS `sales_to_capital`.
4. The spec explicitly calls out that `asset_class="saas"` does not exist today.
5. The spec recommends `calibration_sector="saas"` rather than widening method-routing `asset_class`.
6. The spec requires source metadata for sector assumptions.
7. The spec requires sector-sourced `base_rate_check` text to include sector, source, source date, and config path.
8. The spec requires zero behavior change for AAPL, MRNA, and UBER.
9. The spec requires a new SaaS fixture ticker and valuation comparison against global defaults.
10. The spec keeps live advisor calibration out of scope.

## Required Commands After Implementation

Run the standard offline suite:

```text
UV_CACHE_DIR=.uv-cache .venv/bin/uv run --no-sync pytest
```

Run focused config and valuation tests:

```text
UV_CACHE_DIR=.uv-cache .venv/bin/uv run --no-sync pytest skills/valuation/dcf skills/valuation/method_router skills/data/edgar
```

Run resolver smokes for unchanged fixtures:

```text
UV_CACHE_DIR=.uv-cache .venv/bin/uv run --no-sync python -m resolver AAPL
UV_CACHE_DIR=.uv-cache .venv/bin/uv run --no-sync python -m resolver MRNA
UV_CACHE_DIR=.uv-cache .venv/bin/uv run --no-sync python -m resolver UBER
```

Run resolver smoke for the new SaaS fixture:

```text
UV_CACHE_DIR=.uv-cache .venv/bin/uv run --no-sync python -m resolver <SAAS_TICKER>
```

## Test Checklist

1. Config loads with existing global DCF scenarios unchanged.
2. Config loads with `dcf.sector_scenarios` present.
3. Config rejects an active sector block with missing source metadata.
4. Config rejects an active sector block missing bear/base/bull scenario keys.
5. Config rejects an active sector block with missing `sales_to_capital`.
6. Config accepts the active SaaS block with sourced revenue growth, NOPAT margin, and sales-to-capital values.
7. Config preserves existing beta lookup behavior.
8. Method Router still routes AAPL to `asset_class="cash-generator"` and `method="DCF"`.
9. Method Router still routes MRNA to `asset_class="optionality"` and `method="rNPV"`.
10. Method Router still routes UBER according to existing approved behavior.
11. Method Router emits SaaS calibration metadata only for the approved SaaS fixture.
12. Method Router sets `calibration_sector` from `config.dcf.sector_scenarios.<sector>.tickers`.
13. Method Router does not infer SaaS from ticker name.
14. Method Router does not call an LLM.
15. Method Router does not call the network.
16. DCF assumption resolver returns global scenarios when no sector context is supplied.
17. DCF assumption resolver returns global scenarios for unknown sector keys.
18. DCF assumption resolver returns sector scenarios only when the sector block is active and complete.
19. DCF assumption resolver fails closed for incomplete active sector drivers.
20. Forward DCF global fallback values match pre-M4.5 AAPL expectations.
21. Reverse DCF global fallback values match pre-M4.5 AAPL expectations.
22. Forward DCF uses SaaS revenue growth values when the SaaS sector block is active and complete.
23. Forward DCF uses SaaS NOPAT margin values when the SaaS sector block is active and complete.
24. Forward DCF uses the approved SaaS `sales_to_capital` values from Damodaran source metadata.
25. Forward DCF does not use global fallback `sales_to_capital` for a SaaS-sector-routed ticker.
26. Reverse DCF uses the same base scenario source as forward DCF.
27. Sector-sourced `revenue_growth` derivation references `config.dcf.sector_scenarios.saas`.
28. Sector-sourced `nopat_margin` derivation references `config.dcf.sector_scenarios.saas`.
29. Sector-sourced `sales_to_capital` derivation references `config.dcf.sector_scenarios.saas`.
30. Sector-sourced `base_rate_check` names SaaS.
31. Sector-sourced `base_rate_check` names Aswath Damodaran, NYU Stern.
32. Sector-sourced `base_rate_check` includes January 2026.
33. Sector-sourced `base_rate_check` includes `config.dcf.sector_scenarios.saas`.
34. Sector source metadata includes the Damodaran margins and ROC URL.
35. Sector source metadata includes the Damodaran historical growth URL.
36. Sector source metadata includes industry category `Software (System & Application)`.
37. Sector source metadata includes firm count `309`.
38. Global fallback `base_rate_check` does not falsely claim SaaS sector sourcing.
39. New SaaS EDGAR fixture resolves CIK.
40. New SaaS EDGAR fixture extracts five years.
41. New SaaS EDGAR fixture has sourced revenue, EBIT, cash, debt, and shares.
42. Any new EDGAR concept fallback has a focused fail-closed test.
43. SaaS fixture normalization succeeds.
44. SaaS fixture cost-of-capital succeeds through existing beta/config conventions.
45. SaaS fixture method directive routes to DCF.
46. SaaS fixture DCF artifacts audit successfully.
47. SaaS fixture scenario artifact audits successfully.
48. SaaS sector valuation range differs from a synthetic global-default valuation for the same fixture.
49. Difference test compares bear/base/bull assumptions and at least one per-share scenario value.
50. AAPL resolver smoke still returns a final Handoff or existing approved terminal payload.
51. MRNA resolver smoke still follows the non-DCF route.
52. UBER resolver smoke is unchanged unless explicitly approved otherwise.
53. No runtime artifacts are committed under `data/`.
54. No new dependency is added.
55. No Analyst prompt or eval surface is added.

## Manual Closure Review

Before closing implementation:

1. Confirm `config.dcf.scenarios` is byte-for-byte unchanged unless a separate approved change says otherwise.
2. Confirm SaaS `sales_to_capital` uses the sourced Damodaran Software (System & Application) values.
3. Confirm `asset_class` semantics remain method-routing semantics.
4. Confirm sector calibration is deterministic and auditable.
5. Confirm all sector-sourced assumptions cite source metadata in artifacts.
6. Confirm AAPL, MRNA, and UBER behavior did not drift.
7. Confirm the new SaaS fixture proves a distinct sector valuation range.
