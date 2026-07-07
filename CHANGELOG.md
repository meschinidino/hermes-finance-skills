# Changelog

## [0.1.0.0] - 2026-07-06

### Added

- Added sector-aware DCF assumptions for SaaS companies using sourced Damodaran Software (System & Application) base rates.
- Added deterministic `calibration_sector` routing so sector calibration stays separate from method `asset_class`.
- Added CRM as the first SaaS fixture, including EDGAR companyfacts, price, analyst evidence, and resolver smoke coverage.
- Added tests proving SaaS routing, Damodaran base-rate provenance, and sector DCF values that differ from the global fallback.
