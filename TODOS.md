# TODOS

## Calibration

### Hermes outcome ingestion

**What:** Add a host-injected ingestion path so Hermes can submit completed calibration outcomes directly.

**Why:** Local M5 review ingestion proves the schema, but Hermes will eventually need a direct integration instead of shelling out to the standalone CLI.

**Context:** M5 intentionally keeps outcome ingestion local and deterministic. After D-4 call/review schemas and analytics are stable, design a Hermes adapter that submits the same `CalibrationReview` payloads through the portable storage seam without coupling this repo to Hermes internals.

**Effort:** M
**Priority:** P3
**Depends on:** M5 D-4 local calibration review ingestion

### Automatic return calculation

**What:** Add optional review-date price lookback and automatic realized-return calculation for calibration reviews.

**Why:** Manual outcome reviews are enough for M5, but return calculations would make future hit-rate and directional-bias analytics less subjective.

**Context:** M5 excludes live price lookback to avoid source, timing, and data-policy questions. After manual reviews are working, design how to fetch review-date prices, handle missing market days, record price provenance, and keep the calculation deterministic.

**Effort:** M
**Priority:** P3
**Depends on:** M5 D-4 local calibration review ingestion

## Valuation

### Business-model-aware global DCF bear margin

**What:** Make the global DCF bear-scenario margin default business-model-aware (or lower it) instead of a flat 24% NOPAT margin applied to every company.

**Why:** The global bear scenario assumes a 24% NOPAT margin (`config/conventions.yaml:45`), which over-values any structurally thin-margin business even in its pessimistic case. This is the root cause behind UBER's `price_at_or_below_bear` flag. M4.5 Phase 3 patches it per-sector (an `internet_platform` anchor for UBER), but the next thin-margin ticker with no sector will hit the same flag. Fixing the default reduces the need for per-sector rescue.

**Pros:** Fewer one-off sectors; more honest bear cases by default across all tickers.
**Cons:** Touches global defaults — broad blast radius across every ticker (AAPL/MRNA/CRM/UBER and any future name); needs its own calibration and review.

**Context:** Surfaced during M4.5 Phase 3 (`specs/2026-07-07-m4-5-phase-3-internet-platform-sector/`) while fixing UBER. Phase 3 deliberately kept scope sector-local (planning option C was considered and deferred). Start from `config/conventions.yaml:42-54` (global `dcf.scenarios`) and `skills/valuation/dcf/dcf.py:63` (`resolve_dcf_scenario_source`). Best done after Phase 3 proves the sector path works end to end.

**Effort:** M
**Priority:** P3
**Depends on:** M4.5 Phase 3 (internet_platform sector) landing first

## Completed
