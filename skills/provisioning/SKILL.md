# SKILL: Sector Base-Rate Provisioning
type: tool
triggers: [provision_sectors, sector_provisioning, provision-sectors]
reads: [config/sources, config/sector_brackets.yaml, config/conventions.yaml]
knowledge: []
inputs: a Damodaran source snapshot (config/sources/<name>.json) plus the house bracket layer (config/sector_brackets.yaml)
outputs: config.dcf.sector_scenarios.<sector> blocks (check drift or emit for review)
no_llm: true

definition_of_done:
  1_contract: SKILL.md present and complete
  2_deterministic: no LLM, Senior, Analyst, network, or live data used at runtime; assembles committed snapshot + brackets only
  3_unit_tests: regenerate-matches-committed, drift, unprovisioned-sector, fail-closed (missing driver/industry/bracket), and CLI paths covered
  4_no_impute: missing sourced drivers fail closed rather than being filled in
  6_resolver_trigger: registered as a provision-sectors command separate from analyze()
  7_resolver_eval: analyze() ticker behavior is unchanged; conventions.yaml stays the single runtime source
  9_e2e_smoke: check reports zero drift on the committed repo; emit prints a paste-ready block
  10_filing_rules: generated blocks carry Damodaran source metadata (name, date, firm count, URLs) and pass DcfSectorScenarioConfig

## What it does

The Damodaran-sourced, staleable base rates (revenue growth, NOPAT margin,
sales-to-capital) live in a committed source snapshot. The house-judgment layer
(bear/bull brackets, tagged tickers, rationale) lives in `config/sector_brackets.yaml`.
This tool assembles the two into the `config.dcf.sector_scenarios.<sector>` blocks
that B-3 DCF reads, so refreshing a sector means dropping in a new snapshot and
re-running the tool, not hand-editing decimals.

## Commands

- `python -m resolver provision-sectors check` — verify every committed sector block
  is faithfully reproduced from the snapshot + brackets, and that no committed sector
  is left unprovisioned. Exit 1 on drift.
- `python -m resolver provision-sectors emit <sector>` — print the regenerated block,
  ready to review and paste into `conventions.yaml`.

## Refresh flow

1. Re-capture the Damodaran datasets into a new `config/sources/<name>.json` snapshot.
2. Point `config/sector_brackets.yaml` `snapshot:` at the new file.
3. `provision-sectors check` flags the drift; `provision-sectors emit <sector>` prints
   the updated block; review and paste it into `conventions.yaml`.
4. `provision-sectors check` returns clean once the committed block matches the source.
