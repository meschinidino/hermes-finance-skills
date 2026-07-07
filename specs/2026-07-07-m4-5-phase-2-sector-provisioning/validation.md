# M4.5 Phase 2 Sector Base-Rate Provisioning - Validation

## Automated tests (`skills/provisioning/test_sector_provisioning.py`)

- `test_saas_block_regenerates_from_snapshot_and_brackets` — the committed SaaS block is
  reproduced field-for-field from the snapshot + house brackets. **Headline correctness proof.**
- `test_check_config_reports_no_drift_on_committed_repo` — `check_config()` is clean on the repo.
- `test_base_values_are_damodaran_rounded_to_snapshot_decimals` — base = {0.123, 0.326, 1.54}.
- `test_generated_block_is_schema_valid` — generated block passes `DcfSectorScenarioConfig`.
- `test_committed_config_still_loads` — `conventions.yaml` loads; CRM still maps to `saas`.
- `test_refreshed_snapshot_flows_into_base_values` — a changed snapshot growth flows into base.
- `test_check_detects_drift` — a changed snapshot surfaces a `drift` issue.
- `test_check_detects_unprovisioned_committed_sector` — a hand-added committed sector is flagged
  `unprovisioned_in_config`.
- `test_missing_sourced_driver_fails_closed` — missing driver raises `ProvisioningError`
  (no imputation).
- `test_industry_not_in_snapshot_fails_closed` — unknown industry raises `ProvisioningError`.
- `test_missing_bracket_edge_fails_closed` — missing bear/bull edge raises `ProvisioningError`.
- `test_emit_unknown_sector_fails_closed` — emit of an unknown sector raises `ProvisioningError`.
- `test_cli_check_returns_zero_on_committed_repo` — CLI `check` exits 0 with `{"status":"ok"}`.
- `test_cli_emit_prints_block` — CLI `emit saas` prints the committed block.

## Commands

- Full suite: `UV_CACHE_DIR=.uv-cache .venv/bin/uv run --no-sync pytest` → 296 passed, 3 skipped.
- Focused: `... pytest skills/provisioning` → 14 passed.
- Provisioning check: `... python -m resolver provision-sectors check` → `{"status":"ok","issues":[]}`.
- Emit: `... python -m resolver provision-sectors emit saas` → paste-ready SaaS block.
- Resolver smokes: `... python -m resolver AAPL | MRNA | UBER | CRM` → all succeed unchanged.

## Manual checks

- The runtime does not read the snapshot or house layer: `analyze()` and `load_config` touch only
  `conventions.yaml`.
- `Software (Internet)` is present in the snapshot for provenance and is NOT an active sector.

## Result

Phase 2 complete. Sector base rates are provisioned deterministically from a committed Damodaran
snapshot plus a house bracket layer; the committed SaaS block regenerates exactly; drift,
unprovisioned sectors, and missing sourced data fail closed; and the `analyze()` runtime is
unchanged.
