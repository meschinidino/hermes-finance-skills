# Changelog

## [0.1.2.0] - 2026-07-08

### Added

- Added the `uber_realized` DCF calibration: UBER is anchored to its own realized EDGAR financials (FY2025 NOPAT margin ~8%, ex-goodwill capital turnover ~2.3, trailing revenue growth faded from ~18%) instead of an industry median, fixing the `price_at_or_below_bear` report flag. Sourced raw facts live in `config/sources/uber-realized-2026-01.json`; the growth fade and ex-goodwill choice are documented house judgments in `config/sector_brackets.yaml`.
- Added an algebraic coherence guardrail to `skills/provisioning` (`nopat_margin > revenue_growth / sales_to_capital` per scenario, ordered bear<base<bull; not override-able) that rejects an incoherent anchor at `provision-sectors check`, before it can halt `analyze()` on the C-4 ordering audit.
- Added a documented guardrail-override system (firm-count and thin-margin) so a single-company realized anchor (n=1 by construction) and a genuinely thin margin activate with written rationale, surfaced in `provision-sectors check`.
- Added the M4.5 Phase 3 spec (plan, requirements, validation, advisor finding) recording why the industry-median path was abandoned.

### Notes

- No `analyze()` runtime change: UBER still reads `conventions.yaml`. UBER now renders a positive, monotonic range (bear 5.55 / base 16.42 / bull 38.81 vs price 74.43); `price_at_or_below_bear` is cleared and replaced by the legitimate `price_at_or_above_bull`. AAPL/MRNA/CRM unchanged; the SaaS block regenerates byte-for-byte.
- The first Phase 3 attempt (anchoring UBER to the Damodaran `Software (Internet)` industry median) was abandoned: the median's growth and margin are independent cross-sectional statistics, jointly incoherent for a single-company DCF (negative, non-monotonic values).
- The flat 24% global bear-margin default (the broader root cause for thin-margin names) is deferred as a `TODOS.md` Valuation item.

## [0.1.1.0] - 2026-07-07

### Added

- Added deterministic, offline sector base-rate provisioning: a committed Damodaran source snapshot (`config/sources/damodaran-2026-01.json`) plus a house-judgment bracket layer (`config/sector_brackets.yaml`) that assemble into the `config.dcf.sector_scenarios` blocks.
- Added the `skills/provisioning` tool and `provision-sectors` resolver command (`check`/`emit`) that regenerate the committed SaaS block field-for-field from source, flag drift and unprovisioned sectors, and fail closed on missing sourced drivers.
- Added the M4.5 Phase 2 spec, plan, and validation covering the two-layer split, refresh flow, and fail-closed guarantees.

### Notes

- No `analyze()` runtime change: sector base rates are still read from `conventions.yaml`; provisioning verifies and regenerates that committed source from the snapshot plus house brackets.
- Captured `Software (Internet)` in the snapshot for provenance but did not activate it as a sector (thin 29-firm sample, 4.59% after-tax operating margin); a clean-economics second sector is deferred to Phase 3.

## [0.1.0.0] - 2026-07-06

### Added

- Added sector-aware DCF assumptions for SaaS companies using sourced Damodaran Software (System & Application) base rates.
- Added deterministic `calibration_sector` routing so sector calibration stays separate from method `asset_class`.
- Added CRM as the first SaaS fixture, including EDGAR companyfacts, price, analyst evidence, and resolver smoke coverage.
- Added tests proving SaaS routing, Damodaran base-rate provenance, and sector DCF values that differ from the global fallback.
