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

## Completed
