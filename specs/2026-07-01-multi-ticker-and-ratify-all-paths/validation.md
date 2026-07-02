# validation.md — Multi-Ticker Enablement + Ratify All Paths

## Required Commands

Run the full suite:

```text
UV_CACHE_DIR=.uv-cache .venv/bin/uv run --no-sync pytest
```

Run every target ticker:

```text
UV_CACHE_DIR=.uv-cache .venv/bin/uv run --no-sync python -m resolver AAPL
UV_CACHE_DIR=.uv-cache .venv/bin/uv run --no-sync python -m resolver MRNA
```

If a second ordinary DCF ticker is added:

```text
UV_CACHE_DIR=.uv-cache .venv/bin/uv run --no-sync python -m resolver <SECOND_DCF_TICKER>
```

## Workstream A Validation

1. AAPL regression:
   - `method_directive.method == "DCF"`.
   - `valuation_range.json` exists and audits.
   - `expectations_line.json` exists and audits.
   - Business, Gate Card, Moat, CapAlloc, Scenarios, Edge/Cruxes, Risk, Senior Review Package, and Senior Decision Package are all filed.

2. Non-DCF route:
   - The chosen non-DCF ticker resolves through EDGAR fixture data.
   - The EDGAR companyfacts fixture is documented as real SEC-derived frozen data, with real CIK, accessions, fiscal periods, forms, and reported values.
   - `_industry_classification()` resolves through config rather than raising.
   - `method_directive.method != "DCF"`.
   - `method_directive.implemented` reflects the route truthfully.
   - `valuation_range.json` and `expectations_line.json` are not filed as DCF substitutes.
   - `build_dcf_artifacts()` is not called.

3. Non-DCF substantive artifacts:
   - Business artifact exists and has ticker-specific evidence.
   - Gate Card exists and audits.
   - Moat artifact exists and has ticker-specific evidence.
   - CapAlloc artifact exists and has ticker-specific evidence.
   - Scenarios artifact exists and contains method-appropriate drivers rather than DCF-only drivers.
   - Scenarios contain evidence-backed Senior-owned probability drafts or equivalent method-specific probability drafts.
   - Edge/Cruxes exists, uses the non-DCF route context, and contains non-placeholder steelman, counterparty, variant view, catalysts, and cruxes/falsifiers.
   - Risk exists and contains non-placeholder pre-mortem, bear/short case, modellable risks, tail risks, kill metric, risk completeness, and route-appropriate downside anchor.

4. Fixture honesty:
   - If live EDGAR is not used, validation notes must state whether the fixture is real SEC-derived frozen data.
   - If real SEC data could not be pulled, validation must stop and report the blocker unless a synthesized-input exercise was explicitly approved.
   - Any synthesized-fixture exercise must be labeled exactly as "pipeline executes on non-AAPL-shaped input" and explicitly not as evidence that the audits generalize.
   - No validation language may claim true live-EDGAR generalization unless the run actually used live SEC data.
   - Analyst evidence fixtures must list real public-information anchors, and validation must flag them as the weakest link in the generalization proof because they are authored.

## Workstream B Validation

5. Ratify on all GO paths:
   - AAPL DCF path calls `Senior.ratify` exactly once.
   - Non-DCF path calls `Senior.ratify` exactly once.
   - Non-DCF payload includes `senior_review_package`.
   - Non-DCF payload includes `senior_decision_package`.
   - Non-DCF `senior_decision_package.ratification_summary.required_count > 0`.
   - Non-DCF ratification rate is present and equals the required outcome counts.

6. Independence assertion:
   - DCF path fails before Senior decision package when analyst and Senior families match.
   - Non-DCF path fails before Senior decision package when analyst and Senior families match.
   - Both failures identify the ratify independence violation, not an unrelated route error.

7. Method-aware manifest passes:
   - DCF manifest passes with the complete DCF route required set.
   - Non-DCF manifest passes with the complete selected-method required set.
   - Non-DCF manifest does not require DCF-only valuation artifacts.
   - DCF manifest still requires DCF-specific route completeness where applicable.

8. Method-aware manifest fails closed:
   - DCF consolidation fails if any DCF route required source is omitted.
   - DCF consolidation fails if any DCF route required source has summary but no review item.
   - Non-DCF consolidation fails if any non-DCF route required source is omitted.
   - Non-DCF consolidation fails if any non-DCF route required source has summary but no review item.
   - Non-DCF consolidation fails if Risk review package is missing.
   - Non-DCF consolidation fails if Method Directive route evidence is missing from the manifest-required route context.

9. Route-specific regression tests:
   - A test monkeypatches `build_dcf_artifacts()` to fail and confirms the non-DCF route still passes without invoking it.
   - A test removes one non-DCF analyst evidence fixture and confirms the run fails closed with the ticker-specific missing fixture error.
   - A test removes or omits one non-DCF required manifest source and confirms consolidation fails closed.
   - A test removes or omits one DCF required manifest source and confirms DCF consolidation still fails closed.

## Acceptance Report Template

The validation report must include:

```text
Ticker: AAPL
Method selected:
Completed:
Artifacts filed:
Ratified:
Ratification required_count / rate:

Ticker: MRNA
Method selected:
Completed:
Artifacts filed:
Ratified:
Ratification required_count / rate:
DCF invoked:
Live EDGAR or fixture-backed:
EDGAR fixture provenance:
Analyst fixture provenance:

Manifest checks:
DCF pass:
DCF missing-source fail:
Non-DCF pass:
Non-DCF missing-source fail:
```
