# M4.5 Phase 2 Sector Base-Rate Provisioning - Plan

## Objective

Stop hand-hardcoding Damodaran sector base rates in `conventions.yaml`. Split the sector
data into a refreshable source snapshot and a stable house-judgment layer, and add a
deterministic tool that assembles them into the sector blocks the runtime reads. Prove
correctness by regenerating the Phase 1 SaaS block exactly.

## Two-layer split

- **Source snapshot** (`config/sources/damodaran-2026-01.json`) — the staleable, sourced data:
  per-industry firm count and the three raw Damodaran drivers, plus `source_name`, `source_date`,
  `source_urls`, and `base_value_decimals`. Refreshed annually by re-capturing the datasets.
- **House layer** (`config/sector_brackets.yaml`) — the judgment that does not change with the
  dataset: per-sector `industry_category` (the snapshot key), `tickers`, `rationale`, and the
  absolute bear/bull `brackets` per driver. Names the active `snapshot`.

`conventions.yaml` stays the committed, hand-reviewed runtime source. It is the *generated
artifact*; the two layers above are its *derivation source*.

## Assembly rule

For each sector in the house layer:
- `industry_category` selects the snapshot industry row (fail closed if absent).
- `base` = `round(row.<driver>, snapshot.base_value_decimals)` for each of revenue_growth,
  nopat_margin, sales_to_capital (fail closed if any driver is missing — no imputation).
- `bear` / `bull` = the absolute bracket values from the house layer (fail closed if missing).
- Block metadata (`source_name`, `source_date`, `source_urls`, `firm_count`) comes from the
  snapshot; `tickers` and `rationale` come from the house layer.
- The assembled block is validated against `DcfSectorScenarioConfig` before use.

`round(0.1233, 3) = 0.123`, `round(0.3262, 3) = 0.326`, `round(1.54, 3) = 1.54`, so the SaaS
block reproduces the Phase 1 base values exactly; the irregular Phase 1 brackets
(0.06/0.20, 0.22/0.38, 1.20/2.00) are stored verbatim in the house layer.

## Components

- `skills/provisioning/sector_provisioning.py` — `load_snapshot`, `load_brackets`,
  `build_sector_block`, `generate_sector_blocks`, `check_config`, `emit_sector_block`, and a
  `main` CLI with `check` / `emit <sector>` subcommands.
- `skills/provisioning/{__init__.py, SKILL.md, resolver.entry, test_sector_provisioning.py}`.
- `config/sources/damodaran-2026-01.json` and `config/sector_brackets.yaml`.
- `resolver.py` — a `provision-sectors` dispatch mirroring `render-report`, delegating to the
  tool's `main`. No change to the `analyze()` path.

## Operations

- `check` — build all sector blocks, compare to the committed `conventions.yaml` blocks. Report
  `missing_in_config`, `drift`, or `unprovisioned_in_config`. Exit 1 if any issue.
- `emit <sector>` — print the regenerated block as YAML for review and paste.

## Refresh flow

Drop a new `config/sources/<name>.json`, point `sector_brackets.yaml` `snapshot:` at it, run
`provision-sectors check` (flags drift), `provision-sectors emit <sector>` (prints the new
block), paste into `conventions.yaml`, and re-run `check` until clean.

## Out of scope / deferred

- Activating `Software (Internet)` (thin sample, 4.59% margin) — deferred to Phase 3 pending a
  clean-economics second sector.
- In-place rewrite of `conventions.yaml` (would churn the hand-maintained file); emit-review-paste
  is the update path.
- Snapshot capture automation (the `/scrape` + `/skillify` browser flow stays a local authoring
  aid and does not ship in the pack).
