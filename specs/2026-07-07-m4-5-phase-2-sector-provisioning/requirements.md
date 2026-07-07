# M4.5 Phase 2 Sector Base-Rate Provisioning - Requirements

## Context

Phase 1 introduced sector-aware DCF base rates (SaaS = Damodaran `Software (System
& Application)`) but hand-hardcoded the values directly into `config/conventions.yaml`
with a `source_date` of `2026-01`. Damodaran refreshes those datasets annually, so
every block silently goes stale and the only update path is a human re-typing decimals
from an HTML table. Phase 2 replaces hand-hardcoding with a deterministic provisioning
path, without changing the runtime.

## Functional Requirements

1. The Damodaran-sourced, staleable numbers (base revenue growth, base NOPAT margin,
   base sales-to-capital, firm count, source URLs, source date) must live in a committed
   source snapshot under `config/sources/`, not be hand-typed into `conventions.yaml`.
2. The house-judgment inputs that do not come from Damodaran and do not go stale with the
   dataset (bear/bull brackets, tagged tickers, rationale) must live in a separate house
   layer at `config/sector_brackets.yaml`.
3. A deterministic provisioning tool must assemble a snapshot plus the house layer into the
   `config.dcf.sector_scenarios.<sector>` blocks.
4. Base values must be `round(Damodaran value from snapshot, snapshot.base_value_decimals)`.
5. Bear and bull scenario values must come from the house bracket layer.
6. The tool must reproduce the committed Phase 1 SaaS block exactly, field for field, from the
   `damodaran-2026-01` snapshot plus the house brackets.
7. The provisioning tool must not impute missing sourced drivers; a snapshot missing any driver
   for a provisioned industry must fail closed.
8. The tool must fail closed when a sector's `industry_category` is absent from the snapshot.
9. The tool must fail closed when a required bear/bull bracket edge is missing.
10. Every generated block must be validated against `DcfSectorScenarioConfig` before it can be
    treated as a valid block.
11. A `check` operation must report drift between the generated blocks and the committed
    `conventions.yaml` sector blocks, and must return clean on the committed repository.
12. `check` must flag any committed sector block that is not backed by the provisioning layer
    (`unprovisioned_in_config`), so a hand-edited sector cannot silently diverge from source.
13. An `emit` operation must print the regenerated block for one sector, ready to review and
    paste into `conventions.yaml`.
14. The provisioning tool must be invocable as a resolver command (`provision-sectors`) separate
    from `analyze()`, and also runnable as a module.
15. The runtime must be unchanged: `analyze()` still reads `config/conventions.yaml`, with no new
    read of the snapshot or house layer at analysis time.
16. Existing AAPL, MRNA, UBER, and CRM behavior must be unchanged.
17. No network, LLM, Senior, or Analyst call may be added; provisioning is fully offline and
    deterministic from committed files.
18. No new runtime dependency may be added (PyYAML and pydantic only).
19. The source snapshot must record the January 2026 Damodaran values for `Software (System &
    Application)`: 309 firms, 12.33% revenue growth, 32.62% after-tax operating margin, 1.54
    sales/invested capital.

## Resolved Decisions

1. The second sector (`Software (Internet)`: 29 firms, 4.59% after-tax operating margin) is
   captured in the snapshot for provenance but is NOT activated as a sector in Phase 2. A thin
   29-firm sample and a near-zero margin make it a poor DCF base-rate anchor. A second
   clean-economics sector is deferred to Phase 3.
2. Bear/bull brackets are stored as absolute house-judgment values, not derived from base by a
   formula, because Phase 1's brackets are irregular relative to base and must reproduce exactly.
3. `conventions.yaml` remains the single hand-reviewed runtime source. The tool verifies and
   emits blocks; it does not rewrite `conventions.yaml` in place (which would reorder/reformat the
   hand-maintained file). Updates are emit-review-paste, then `check` confirms clean.

## Non-Goals

- No activation of `Software (Internet)` or any second sector this phase.
- No automatic in-place rewrite of `conventions.yaml`.
- No live web fetch inside the shipped tool; snapshot capture is an authoring-time step.
- No change to global DCF defaults, valuation methods, routing taxonomy, or Senior touchpoints.
- No new valuation behavior; base rates for SaaS are byte-for-byte identical to Phase 1.
