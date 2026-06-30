# mission.md — Fundamental Analysis Skill Pack

## What we're building
A **portable, lightweight skill pack** that turns a US-listed ticker into a **decision-ready handoff**: mechanical numbers that are fully auditable, judgment that is explicitly drafted and flagged, and a single Senior sign-off. It runs **standalone** (for testing and SDD) and **inside Hermes** as a skill, with all host-specific pieces injected.

## The value
Reproducible analysis. Two analysts (or two runs) converge on the same numbers because conventions are fixed and every figure is sourced; and the human/agent making the call can see *exactly* where the work was mechanical versus where it was judgment. The pack does the legwork; **a Senior decides.**

## Non-negotiable invariants (the constitution — never violate)
1. **Provenance or it doesn't exist.** No number is stored, passed between skills, or shown without `{value, tag, form, period, accession, retrieved_at}`.
2. **Two role types, two regimes.** *Accountants* (deterministic) fail closed and never impute; *Analysts* (judgment) only ever **draft + flag + attach evidence** — they never assert and never decide.
3. **The Senior is the only signer.** Analysts recommend up. The Senior is a blocking dependency exactly twice — the early GO/NO-GO gate and the one consolidated ratify pass — and nowhere else. The Senior is an **injected role**, not a hardcoded person.
4. **Free sources; EDGAR is the system of record.** Fundamentals come from EDGAR/XBRL. External deps reduce to three free lookups (FRED risk-free, Damodaran ERP/betas, one price feed).
5. **Portable.** No hard coupling to Hermes. Senior, Storage, LLM, and PriceFeed are injected interfaces with sensible standalone defaults.
6. **Lightweight.** Embedded storage (SQLite + files), no server, no queue, no orchestration framework — the resolver *is* the orchestrator. Small dependency tree.
7. **Method matches asset.** The valuation method is routed by asset class; plain DCF is never applied to optionality/pre-revenue names.

## What success looks like
`analyze(ticker)` returns either a complete Handoff (sourced numbers, a senior-signed valuation range, 3 falsifiable cruxes, two-bucket risk, mandatory confidence-and-gaps, revisit triggers) or a one-paragraph kill memo — and every run feeds the calibration log that, over time, scores the Analysts' conviction and the org's routing/escalation health.

## Out of scope (v1)
- Non-US / non-XBRL names (documented v4 extension: per-country tax, country-risk premium, valuation currency).
- Order execution, portfolio management, position sizing *decisions* (the pack supplies sizing **inputs**; the Senior sizes).
- This is **not investment advice**; it is decision support for a Senior who signs.
