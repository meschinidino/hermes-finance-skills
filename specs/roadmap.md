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
**Spec:** pending
**Status:** Not started.

### M3 — The Analysts + ratify wiring
Research dept: `C-1 Business`, `C-2 Moat`, `C-3 CapAlloc`, `C-4 Scenarios`, `C-5 Edge & Cruxes`, `C-6 Risk`. Each emits `needs_ratification` drafts with evidence. Wire the draft → collect → `Senior.ratify` flow + the early GO/NO-GO gate. LLM injected.
**Done:** a full draft package with every judgment flagged, ratifiable in one pass; the biotech-DCF guard and the steelman/counterparty brakes verified by red-team prompts.

### M4 — Synthesis + the resolver
`D-2 Conviction`, `D-3 Review Packager`; complete `resolver.md` behavior — routing table, escalation matrix, parallelism, KILL halt, the two Senior touchpoints. Full Handoff schema with revisit triggers.
**Done:** `analyze()` produces a complete, senior-signed Handoff or a kill memo, routed and escalated correctly.

### M5 — Calibration + performance reviews
`D-4 Calibration` analytics (hit-rate by conviction band, directional bias, leak-by-phase) + the routing-correctness and escalation-correctness checks.
**Done:** the org measures its own outcome quality and health over time.

### M6 — Hardening + extensions *(later)*
Worked-example exemplar on a real ticker (highest-ROI learning aid); containerize for Hermes/Azure deploy; then the v4 non-US extension (per-country tax, country-risk premium, currency).

---

**Critical path through the build:** M0 → M1 → **M2a** → M2b → M3 → M4. M5/M6 thicken a proven system. If time is short, a credible end-to-end demo exists at the end of M4; everything after improves trust and reach, not core function.
