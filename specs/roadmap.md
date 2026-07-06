# roadmap.md — Build Order

**Strategy: walking skeleton first.** Get one ticker end-to-end through a thin path before building every employee. Prove the spine, then thicken. Each milestone ships something runnable and demoable. Bias: speed over completeness early.

---

### M0 — Scaffold *(foundations)*
Pack structure as an installable module; `Config` (house conventions §2) loaded + validated; the four injected interfaces defined (`Senior`, `Storage`, `LLM`, `PriceFeed`) with standalone defaults; `Provenance` primitive; `analyze()` entry stub; SQLite `pack.db` + files cache dir wired behind `Storage`.
**Done:** `analyze("AAPL")` runs end-to-end returning a stub, with config loaded and storage writable.
**Spec:** `specs/2026-06-29-scaffold/`
**Status:** M0 complete (pydantic, real-stack validated). Validated with `uv run --no-sync pytest` and `uv run --no-sync python -m resolver AAPL`.

### M1 — Walking skeleton *(the priority — a thin vertical slice)*
Minimal happy path on one ticker: `A-1 EDGAR` → `B-1 Normalize` → `B-2 WACC/ROIC` → a bare `D-1 Handoff`. One audit gate live. Provenance enforced on the path.
**Done:** real ROIC/WACC for a real company, every number sourced, emitted in a schema-valid (if sparse) handoff. **This is the milestone that de-risks everything.**
**Spec:** `specs/2026-06-29-walking-skeleton/`
**Status:** M1 complete (fixture-backed EDGAR → Normalize → Spine → bare Handoff). Validated with `UV_CACHE_DIR=.uv-cache .venv/bin/uv run --no-sync pytest` and `UV_CACHE_DIR=.uv-cache .venv/bin/uv run --no-sync python -m resolver AAPL`.

### M2a — Valuation core
`A-2 Price`, `A-3 CoC`, and `B-3 DCF` (forward and reverse). Golden-fixture tests for each.
**Done:** a real forward valuation and a reverse-DCF Expectations Line for AAPL, fixture-backed.
**Spec:** `specs/2026-06-30-valuation-core/`
**Status:** M2a complete (Price, Cost of Capital, and DCF Accountant bundles). Validated with `UV_CACHE_DIR=.uv-cache .venv/bin/uv run --no-sync pytest` and `UV_CACHE_DIR=.uv-cache .venv/bin/uv run --no-sync python -m resolver AAPL`.

### M2b — Gates & routing
`B-4 Screens` (variant-aware), `B-5 Base-Rate`, and `B-6 Method Router`. Golden-fixture tests for each.
**Done:** a populated Gate Card and a method directive that routes asset class to the right valuation tool, fixture-backed.
**Spec:** `specs/2026-06-30-gates-and-routing/`
**Status:** M2b complete (Screens, Base-Rate, and Method Router Accountant bundles). Validated with `UV_CACHE_DIR=.uv-cache .venv/bin/uv run --no-sync pytest` and `UV_CACHE_DIR=.uv-cache .venv/bin/uv run --no-sync python -m resolver AAPL`.

### M3.1 — Analyst contracts & infrastructure
Typed M3 artifacts, ratifiable collection, Analyst audit checks, deterministic fake `LLM`/`Senior` adapters for offline tests, and bundle validation rules for Analyst skill shape.
**Done:** M3 artifacts can be constructed, audited, stored, and collected into a review package without invoking live LLMs or implementing Analyst bundles.
**Spec:** `specs/2026-06-30-m3-1-contracts-infrastructure/`
**Status:** M3.1 complete (typed M3 contracts, derived-only ratification, Analyst audit checks, ratifiable collection, test-only fake adapters, and bundle-shape validation). Validated with `UV_CACHE_DIR=.uv-cache .venv/bin/uv run --no-sync pytest` and `UV_CACHE_DIR=.uv-cache .venv/bin/uv run --no-sync python -m resolver AAPL`.

### M3.2 — Business + early gate
`C-1 Business` Analyst bundle and the one early GO/NO-GO gate after Business understanding. LLM injected; Senior injected.
**Done:** Business draft is evidence-backed and schema-valid; `Senior.gate` is called exactly once after Business; GO continues and NO-GO halts with a filed stop artifact.
**Spec:** `specs/2026-06-30-m3-2-business-early-gate/`
**Status:** M3.2 complete (fixture-backed C-1 Business Analyst bundle, audit-enforced evidence refs, early gate family-independence check, GO continuation, and NO-GO stop artifact). Validated with `UV_CACHE_DIR=.uv-cache .venv/bin/uv run --no-sync pytest`, `UV_CACHE_DIR=.uv-cache .venv/bin/uv run --no-sync pytest tests/test_m3_2_business_gate.py skills/research/business`, and `UV_CACHE_DIR=.uv-cache .venv/bin/uv run --no-sync python -m resolver AAPL`.

### M3.3 — Moat + capital allocation
`C-2 Moat` and `C-3 CapAlloc` Analyst bundles. Each emits evidence-backed `needs_ratification` drafts mapped to the Senior checklist.
**Done:** moat and capital-allocation drafts are ratifiable, evidence-backed, and reject unsupported claims such as "historical ROIC spread alone proves a moat."
**Spec:** `specs/2026-06-30-m3-3-moat-capalloc/`
**Status:** M3.3 complete (fixture-backed C-2 Moat and C-3 CapAlloc Analyst bundles, period-consistency audit, metric-only moat rejection, and undecided Senior review package collection). Validated with `UV_CACHE_DIR=.uv-cache .venv/bin/uv run --no-sync pytest`, `UV_CACHE_DIR=.uv-cache .venv/bin/uv run --no-sync pytest skills/research/moat skills/research/capalloc`, and `UV_CACHE_DIR=.uv-cache .venv/bin/uv run --no-sync python -m resolver AAPL`.

### M3.4 — Scenarios
`C-4 Scenarios` Analyst bundle. Builds bear/base/bull draft assumptions from the existing artifacts, checks base rates, and respects the Method Router.
**Done:** scenario assumptions are driver-tied and base-rate checked; probabilities remain Senior-owned ratifiables; optionality/pre-revenue names are not forced into plain DCF.
**Spec:** `specs/2026-06-30-m3-4-scenarios/`
**Status:** M3.4 complete (fixture-backed C-4 Scenarios Analyst bundle, per-scenario probability ratifiables, filed-artifact driver binding, resolved B-5/B-6 audits, and non-DCF method-deferred path). Validated with `UV_CACHE_DIR=.uv-cache .venv/bin/uv run --no-sync pytest`, `UV_CACHE_DIR=.uv-cache .venv/bin/uv run --no-sync pytest skills/research/scenarios`, and `UV_CACHE_DIR=.uv-cache .venv/bin/uv run --no-sync python -m resolver AAPL`.

### M3.5 — Edge & cruxes
`C-5 Edge & Cruxes` Analyst bundle with the steelman, counterparty, structural mispricing, catalysts, and exactly three falsifiable cruxes.
**Done:** edge drafts reject trivial counterparties, include a no-trade steelman, and emit exactly three measurable cruxes.
**Spec:** `specs/2026-07-01-m3-5-edge-cruxes/`
**Status:** M3.5 complete (fixture-backed C-5 Edge & Cruxes Analyst bundle, no-trade steelman, non-trivial counterparty, structural-mispricing and variant-view brakes, concrete catalysts, exactly three field-falsifiable cruxes, and undecided review package collection). Validated with `UV_CACHE_DIR=.uv-cache .venv/bin/uv run --no-sync pytest`, `UV_CACHE_DIR=.uv-cache .venv/bin/uv run --no-sync pytest skills/research/edge_cruxes`, and `UV_CACHE_DIR=.uv-cache .venv/bin/uv run --no-sync python -m resolver AAPL`.

### M3.6 — Risk
`C-6 Risk` Analyst bundle. Produces pre-mortem, short-seller bear case, two-bucket risk register, bear-case value, and kill metric.
**Done:** risk drafts include non-empty tail risks, a falsifiable kill metric, and ratifiable risk completeness.
**Spec:** `specs/2026-07-01-m3-6-risk/`
**Status:** M3.6 complete (fixture-backed C-6 Risk Analyst bundle, pre-mortem and short-seller bear-case brakes, separate modellable and tail-risk buckets, provenance-complete bear-case value reconciled to filed scenarios, typed-field kill metric falsifiability, and undecided review package collection). Validated with `UV_CACHE_DIR=.uv-cache .venv/bin/uv run --no-sync pytest skills/research/risk`, `UV_CACHE_DIR=.uv-cache .venv/bin/uv run --no-sync pytest`, and `UV_CACHE_DIR=.uv-cache .venv/bin/uv run --no-sync python -m resolver AAPL`.

### M3.7 — Ratify aggregation
Collect M2b and M3 ratifiables into one `SeniorReviewPackage`, call `Senior.ratify` once, and persist the Senior decision package for M4 synthesis.
**Done:** every required judgment is present in one consolidated package and every item has a Senior decision before the package can be treated as ratified.
**Spec:** `specs/2026-07-01-m3-7-ratify-aggregation/`
**Status:** M3.7 complete (B-4 Gate Card verdict plus C-2 through C-6 review packages consolidated into one SeniorReviewPackage, injected Senior.ratify called exactly once on the GO/DCF path, complete SeniorDecisionPackage persisted for M4 synthesis, and NO-GO path remains unratified). Validated with `UV_CACHE_DIR=.uv-cache .venv/bin/uv run --no-sync pytest tests/test_m3_7_ratify_aggregation.py`, `UV_CACHE_DIR=.uv-cache .venv/bin/uv run --no-sync pytest`, and `UV_CACHE_DIR=.uv-cache .venv/bin/uv run --no-sync python -m resolver AAPL`.

### M4a — Resolver restructure
Replace the accretion-payload assembly with a real synthesis boundary. Zero new features.
**Done:** `analyze()` produces the same output as today through the new boundary, with all existing M0-M3 tests passing unchanged.
**Spec:** `specs/2026-07-02-m4a-resolver-restructure/`
**Status:** M4a complete (approved after domain review; M4a boundary preserves pre-restructure outputs except volatile timestamps and run identifiers, with full suite passing).

### M4b — Synthesis skills
`D-2 Conviction` and `D-3 Review Packager`, built on top of the stable boundary from M4a.
**Done:** `analyze()` produces a complete, Senior-signed Handoff.
**Spec:** `specs/2026-07-03-m4b-synthesis-skills/`
**Status:** M4b complete (typed SynthesisPayload wrapper, D-2 Conviction, D-3 Review Packager, filed/reloadable conviction and final handoff artifacts, DCF and non-DCF synthesis paths, and M4b fail-closed tests). Validated with `UV_CACHE_DIR=.uv-cache .venv/bin/uv run --no-sync pytest`, `UV_CACHE_DIR=.uv-cache .venv/bin/uv run --no-sync python -m resolver AAPL`, and `UV_CACHE_DIR=.uv-cache .venv/bin/uv run --no-sync python -m resolver MRNA`.

### M4c — Control flow
Routing table, escalation matrix, parallelism, KILL halt, revisit triggers, C-5 `pass_falsifiers` wired into Handoff revisit triggers, and independence checks upgraded from declared labels to actual provider/model identity.
**Done:** a kill memo is produced correctly and escalations route as specified.
**Spec:** `specs/2026-07-03-m4c-control-flow/`
**Status:** M4c complete (identity-backed Senior metadata, Azure Foundry Senior selector, route manifest audit, canonical KillMemo halts, final Handoff signing metadata, canonical `revisit_triggers`, and resolver route/escalation documentation). Validated with `UV_CACHE_DIR=.uv-cache .venv/bin/uv run --no-sync pytest`, `UV_CACHE_DIR=.uv-cache .venv/bin/uv run --no-sync python -m resolver AAPL`, and `UV_CACHE_DIR=.uv-cache .venv/bin/uv run --no-sync python -m resolver MRNA`. Live Azure Foundry validation is pending credentials.

### M5 — Calibration + performance reviews
`D-4 Calibration` analytics (hit-rate by conviction band, directional bias, leak-by-phase) + the routing-correctness and escalation-correctness checks.
**Done:** the org measures its own outcome quality and health over time.
**Spec:** `specs/2026-07-05-m5-calibration-performance/`

### M6 — Report Renderer
`D-5 Report Renderer`, a deterministic presentation skill that renders an already-completed run directory into a human-readable Markdown report.
**Done:** a final Handoff or KillMemo can be rendered on demand into a sourced report without invoking `analyze()`, LLMs, Analysts, or the Senior.
**Spec:** `specs/2026-07-06-m6-report-renderer/`

### M7 — Hardening + extensions *(later)*
Worked-example exemplar on a real ticker (highest-ROI learning aid); containerize for Hermes/Azure deploy; then the v4 non-US extension (per-country tax, country-risk premium, currency).

---

**Critical path through the build:** M0 → M1 → **M2a** → M2b → M3.1 → M3.2 → M3.3 → M3.4 → M3.5 → M3.6 → M3.7 → M4a → M4b → M4c. M5/M6/M7 thicken a proven system. If time is short, a credible end-to-end demo exists at the end of M4c; everything after improves trust and reach, not core function.
