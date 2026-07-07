# M4.5 Phase 1 Sector-Aware DCF Base Rates - Plan

## Objective

Add a narrow, auditable path for sector-aware DCF assumptions, beginning with SaaS, while preserving the existing global DCF defaults as the fallback path.

This phase is intentionally smaller than live calibration. It fixes the current placeholder problem where profitable DCF-routed companies inherit the same bear/base/bull growth, margin, and reinvestment assumptions regardless of business model. It does not add advisor feedback, live benchmarking, or a new valuation engine.

## Scope

In scope:

- Add `config.dcf.sector_scenarios` as a sector-keyed config surface beside the existing `config.dcf.scenarios`.
- Keep the existing global DCF scenarios unchanged.
- Define the sourced SaaS revenue-growth, NOPAT-margin, and sales-to-capital assumptions in the spec.
- Use Aswath Damodaran's January 2026 `Software (System & Application)` industry data as the SaaS source pack.
- Route DCF assumption selection through a single assumption-source resolver.
- Add `calibration_sector="saas"` as a separate routing field from `asset_class`.
- Manually tag one SaaS ticker into the sector for M4.5 Phase 1.
- Preserve global fallback behavior for non-sector-matched tickers.
- Add source-aware `base_rate_check` text for sector-sourced assumptions.
- Add one fixture-backed SaaS ticker during implementation.
- Prove the SaaS route uses sector assumptions and produces a valuation range distinct from the global default for the same company.

Not in scope:

- Full live calibration with the finance advisor partner.
- New Analyst scenario drafting behavior.
- LLM-based sector detection.
- Changing AAPL, MRNA, or UBER fixture behavior.
- Recalibrating global DCF defaults.
- Adding a new valuation method.
- Adding dependencies or infrastructure.

## Current State

The active config has one DCF scenario table:

```text
config.dcf.scenarios
  bear: revenue_growth=0.02, nopat_margin=0.24, sales_to_capital=2.25
  base: revenue_growth=0.04, nopat_margin=0.28, sales_to_capital=2.75
  bull: revenue_growth=0.06, nopat_margin=0.31, sales_to_capital=3.25
```

B-3 DCF reads that table directly in `build_forward_valuation()` and `build_reverse_expectations()`. The assumption `Number` derivations also hardcode global config paths such as `config.dcf.scenarios.base.nopat_margin`.

B-6 Method Router currently returns these asset classes:

```text
cash-generator | cyclical | financial | optionality | asset-NAV
```

There is no valid `asset_class="saas"` today. Profitable software or automation labels currently route as `cash-generator` and `DCF`.

That means this prompt contains one implementation-sensitive ambiguity: "route by asset_class" cannot literally route SaaS today unless the schema is widened. The safer design is to keep method-routing asset class separate from calibration sector:

```text
asset_class = cash-generator
method = DCF
calibration_sector = saas
```

This avoids confusing "which valuation method?" with "which sector base-rate table should DCF use?"

## Source Pack

SaaS defaults are sourced from Aswath Damodaran, NYU Stern, data as of January 2026:

- `Margins and ROC by Sector`: `https://pages.stern.nyu.edu/~adamodar/New_Home_Page/datafile/mgnroc.html`
- `Historical Growth Rates by Sector`: `https://pages.stern.nyu.edu/~adamodar/New_Home_Page/datafile/histgr.html`

Industry category: `Software (System & Application)`, 309 firms.

Base values:

- Expected revenue growth, next 5 years: `12.33%`, used as `0.123`.
- After-tax operating margin: `32.62%`, used as `0.326`.
- Sales/invested capital: `1.54x`, used as `1.54`.

House scenario values:

```text
bear: revenue_growth=0.06,  nopat_margin=0.22,  sales_to_capital=1.20
base: revenue_growth=0.123, nopat_margin=0.326, sales_to_capital=1.54
bull: revenue_growth=0.20,  nopat_margin=0.38,  sales_to_capital=2.00
```

## Proposed Data Flow

```text
EDGAR facts
    |
    v
Normalize -> B-6 Method Router
                |
                | asset_class="cash-generator"
                | method="DCF"
                | calibration_sector="saas"
                v
        B-3 DCF assumption source resolver
                |
                +-- sector match and active complete block
                |       -> config.dcf.sector_scenarios.saas
                |
                +-- no match
                        -> config.dcf.scenarios
```

The DCF engine remains the same. The change is the source of the driver assumptions and the text/provenance attached to those assumptions.

## Config Shape Plan

Preferred shape:

```yaml
dcf:
  forecast_years: 5
  terminal_growth: 0.025
  reverse_growth_low: -0.05
  reverse_growth_high: 0.32
  scenarios:
    bear: ...
    base: ...
    bull: ...
  sector_scenarios:
    saas:
      status: "active"
      source_name: "Aswath Damodaran, NYU Stern"
      source_date: "2026-01"
      industry_category: "Software (System & Application)"
      firm_count: 309
      source_urls:
        margins_and_roc: "https://pages.stern.nyu.edu/~adamodar/New_Home_Page/datafile/mgnroc.html"
        historical_growth: "https://pages.stern.nyu.edu/~adamodar/New_Home_Page/datafile/histgr.html"
      tickers: ["<SAAS_TICKER>"]
      rationale: "SaaS revenue, margin, and reinvestment economics differ materially from global DCF defaults."
      scenarios:
        bear:
          revenue_growth: 0.06
          nopat_margin: 0.22
          sales_to_capital: 1.20
        base:
          revenue_growth: 0.123
          nopat_margin: 0.326
          sales_to_capital: 1.54
        bull:
          revenue_growth: 0.20
          nopat_margin: 0.38
          sales_to_capital: 2.00
```

Manual ticker assignment lives directly under the sector block as shown above. B-6 sets `calibration_sector` by checking the routed ticker against active `config.dcf.sector_scenarios.<sector>.tickers` coverage. No automatic sector classification is part of M4.5 Phase 1.

## Routing Plan

Recommended implementation:

- Keep `asset_class` method-focused.
- Add `calibration_sector: str | None` to `MethodDirective`.
- Set `calibration_sector="saas"` only through deterministic manual ticker coverage in config.
- Keep `asset_class="cash-generator"` and `method="DCF"` for profitable SaaS names.
- Update B-3 DCF to accept the method directive or a small `DcfAssumptionContext`.

Alternative:

- Add `saas` to `MethodDirective.asset_class`.
- This expands filing rules, model literals, audits, route manifests, and downstream readers.
- It is heavier and less precise because SaaS is not a separate valuation method in this phase.

Recommendation: use `calibration_sector`, not `asset_class="saas"`.

## Assumption Source Resolver

Add a small internal resolver in B-3 DCF, conceptually:

```python
resolve_dcf_scenario_source(config, *, method_directive=None, calibration_sector=None) -> DcfScenarioSource
```

It returns:

- source kind: `global` or `sector`
- sector key when applicable
- source config path
- source metadata
- three scenarios

B-3 forward and reverse DCF both call this once and use the returned source. Direct reads of `config.dcf.scenarios[name]` should be collapsed behind this function.

## Provenance and Base-Rate Text

Global fallback text can remain generic where the global table is actually used.

Sector-sourced DCF assumptions must have specific text:

```text
SaaS sector base rate - Aswath Damodaran, NYU Stern, Software (System & Application) industry averages, data as of January 2026 - see config.dcf.sector_scenarios.saas
```

Derivations should point to driver-specific config paths:

```text
inputs: config.dcf.sector_scenarios.saas.scenarios.base.revenue_growth;
source: Aswath Damodaran, NYU Stern, Software (System & Application), data as of January 2026
```

## Fixture Plan

Pick one SaaS fixture only after a quick EDGAR extraction trial. Candidate order:

1. `CRM` Salesforce: mature SaaS, well-known, subscription revenue, long 10-K history.
2. `NOW` ServiceNow: cleaner enterprise SaaS profile, but may require new concept fallback checks.
3. `ADBE` Adobe: subscription-heavy but mixed software/media economics.
4. `DDOG` Datadog: SaaS profile, but shorter profitability history may complicate DCF.
5. `SNOW` Snowflake: clear SaaS/data-cloud profile, but profitability may route away from DCF depending on EBIT.

The fixture must be chosen based on clean extraction, not brand preference.

## Implementation Steps After Approval

1. Add pydantic config models for sector scenario metadata.
2. Add `calibration_sector` to `MethodDirective` and related audits/serialization.
3. Add deterministic SaaS sector matching through manually configured ticker coverage.
4. Add the DCF assumption-source resolver.
5. Thread method directive or DCF context from resolver into B-3.
6. Update forward DCF assumption construction and `base_rate_check` text.
7. Update reverse DCF base-scenario assumption selection and derivations.
8. Add the SaaS fixture ticker and any narrowly required EDGAR concept fallback tests.
9. Add focused tests proving global fallback remains unchanged.
10. Add focused tests proving SaaS sector selection and valuation difference.
11. Run full offline validation.

## Risks and Mitigations

Risk: Overloading `asset_class` muddies B-6 method routing.
Mitigation: add `calibration_sector` so method choice and sector calibration remain separate concerns.

Risk: source labels become marketing text instead of audit evidence.
Mitigation: require source metadata in config and assert it in tests.

Risk: fixture extraction expands EDGAR fallback logic too broadly.
Mitigation: choose the first clean SaaS fixture and add only concept-specific tests for any fallback additions.

Risk: manual ticker tagging becomes a hidden policy table.
Mitigation: keep ticker coverage in versioned config with source metadata and tests proving only the intended fixture routes to SaaS.

## GSTACK REVIEW REPORT

### Step 0 Scope Challenge

Existing code already solves most of the plumbing:

- `Config` owns validated conventions.
- B-6 already produces a typed `MethodDirective`.
- B-3 already builds all DCF assumption `Number`s and valuation values.
- Existing DCF tests already cover global fallback behavior.

Minimum viable change:

```text
Config sector metadata + B-6 calibration key + B-3 assumption resolver + one SaaS fixture test
```

Do not build a standalone sector-classification service, do not add a new Analyst skill, and do not widen valuation methods.

Complexity check: expected implementation touches about 7 areas if done cleanly:

- `config/conventions.yaml`
- `skills/config.py`
- `skills/accountant_artifacts.py`
- `skills/valuation/method_router/method_router.py`
- `skills/valuation/dcf/dcf.py`
- tests for config/router/DCF/resolver
- SaaS fixture files

This is close to the 8-file smell threshold but acceptable because the schema thread is real. If `asset_class="saas"` is chosen, the blast radius expands and should be re-reviewed.

Search check: no new architectural pattern or infrastructure is introduced. This is Layer 1: use existing config, pydantic validation, and typed artifacts.

TODO cross-reference: existing TODOs are about future calibration ingestion and automatic return calculation. They do not block M4.5 Phase 1 and should not be bundled.

Completeness check: the complete version for this phase is not "all sectors"; it is one sector with sourced growth, margin, sales-to-capital, source metadata, manual ticker tagging, and tests.

### Architecture Review

[P1] (confidence: 9/10) `skills/accountant_artifacts.py` / `skills/valuation/method_router/method_router.py` - `asset_class="saas"` does not exist today. Adding it would change the method-routing schema, not just DCF calibration.

Recommendation: add a separate `calibration_sector` field to `MethodDirective` and keep SaaS as `asset_class="cash-generator"` + `method="DCF"`.

Tradeoff: this is one additive schema field, but it avoids reclassifying SaaS as a valuation method category.

[P1] (confidence: 9/10) `skills/valuation/dcf/dcf.py` - B-3 DCF directly indexes `config.dcf.scenarios`, so sector selection needs one resolver seam before adding config.

Recommendation: centralize scenario-source resolution and route both forward and reverse DCF through it.

Tradeoff: a small helper now prevents duplicated selection logic and inconsistent forward/reverse assumptions later.

### Code Quality Review

[P2] (confidence: 8/10) Sector source metadata can become duplicated strings in config, derivations, and `base_rate_check` text.

Recommendation: model the source metadata once in config and generate all assumption labels from that model.

Tradeoff: slightly richer config model, much lower risk of stale text.

[P2] (confidence: 8/10) Ticker-to-sector matching can become ad hoc if spread across router and DCF.

Recommendation: make the router own deterministic sector selection and make DCF consume only the chosen sector key.

Tradeoff: DCF stays pure valuation logic, but B-6 gains one additive responsibility.

[P2] (confidence: 8/10) Manual ticker assignment could drift if implemented as a separate map from the sector source metadata.

Recommendation: store tickers under `config.dcf.sector_scenarios.<sector>.tickers` so assignment, assumptions, and sources are reviewed together.

Tradeoff: sector blocks become slightly larger, but the policy surface stays local and auditable.

### Test Review

Required coverage:

```text
config parse
  -> sector_scenarios accepts sourced active SaaS metadata
  -> rejects active missing source metadata
  -> rejects active missing driver values

router
  -> SaaS fixture emits calibration_sector="saas"
  -> AAPL/UBER unchanged
  -> MRNA optionality unchanged

DCF
  -> global fallback values unchanged for AAPL
  -> SaaS source selected when complete and active
  -> sector base_rate_check text cites source/date/path
  -> sector sales_to_capital uses Damodaran-sourced values
  -> reverse DCF uses same base scenario source as forward DCF

resolver
  -> SaaS fixture end-to-end valuation differs from global default valuation
  -> existing AAPL/MRNA/UBER smokes remain stable
```

Test diagram:

```text
                 +-----------------------+
                 | config sector block   |
                 +-----------+-----------+
                             |
             +---------------+----------------+
             |                                |
             v                                v
   B-6 router sector key             B-3 assumption resolver
             |                                |
             +---------------+----------------+
                             |
                             v
                    DCF valuation artifacts
                             |
             +---------------+----------------+
             |                                |
             v                                v
      base_rate_check text          valuation differs from global
```

### Performance Review

No performance risk expected. The change is config lookup and string generation on a single-ticker path. Fixture size may increase test runtime slightly, but it stays local and deterministic.

### Open Decisions For User

1. Choose fixture ticker after EDGAR cleanliness check, with `CRM` as the first candidate.
