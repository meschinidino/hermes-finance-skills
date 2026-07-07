# Changelog

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
