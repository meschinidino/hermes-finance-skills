# M1 Walking Skeleton — Plan

## Objective

Build the thinnest end-to-end path that turns `analyze("AAPL")` into a real, sourced financial spine and a schema-valid bare handoff. This milestone proves the load-bearing pipe: fetch, normalize, compute, audit, and file.

## Scope

In scope:
- Thin slices of `A-1 EDGAR`, `A-2 Price`, and `A-3 Cost of Capital`.
- `B-1 Normalize` as a near-identity adapter.
- `B-2 WACC/ROIC` as the first real compute path.
- `D-1 Handoff` as a sparse but valid envelope.
- M1 skill bundles under `/skills`.
- The M1 linear resolver route using the M0 entry point and injected interfaces.

Out of scope:
- M0 scaffold contracts: `Provenance`, `Number`, `Header`, `Ratifiable`, `Storage`, interface protocols, and `Config`.
- Screens, method routing, DCF, Analyst skills, Senior gates, resolver escalation, calibration, and full Handoff rejection rules.
- Full normalization add-backs and operating lease capitalization.
- Damodaran spreadsheet parsing; M1 reads ERP, beta, tax, excess cash, and credit spread from config.

## Prerequisite

M1 depends on `specs/2026-06-29-scaffold/` for primitives, config loading, storage, injected interfaces, runtime layout, and the resolver entry shape. M1 must reuse those M0 contracts and only add the EDGAR → Normalize → Spine → bare Handoff path.

## Proposed Architecture

The portable unit stays lightweight and host-agnostic:

```text
project-root/
├── specs/
├── skills/
│   ├── data/
│   ├── valuation/
│   ├── research/
│   └── synthesis/
├── knowledge/
├── config/
│   └── conventions.yaml
├── data/
│   ├── cache/
│   ├── runs/
│   └── pack.db
└── resolver.py
```

M1 runs as a straight-line resolver sequence:

```text
analyze("AAPL")
   ├─ A-1 EDGAR
   ├─ A-2 Price
   └─ A-3 Cost of Capital
        ↓
      B-1 Normalize
        ↓
      B-2 WACC/ROIC
        ↓
      D-1 Handoff
        ↓
      Storage + audit gate
```

The resolver is the orchestrator. No queue, server, web framework, or provider-specific host integration is introduced in M1.

## Skill Bundles Created In M1

All M1 skills are Accountants (`no_llm: true`), so each bundle includes `SKILL.md`, implementation, unit tests, optional live integration smoke when external, and `resolver.entry`. They do not include `prompt.md` or `eval/`.

```text
skills/data/edgar/
├── SKILL.md
├── edgar.py
├── test_edgar.py
├── test_integration.py
└── resolver.entry

skills/data/price/
├── SKILL.md
├── price.py
├── test_price.py
├── test_integration.py
└── resolver.entry

skills/data/cost_of_capital/
├── SKILL.md
├── cost_of_capital.py
├── test_cost_of_capital.py
├── test_integration.py
└── resolver.entry

skills/valuation/normalize/
├── SKILL.md
├── normalize.py
├── test_normalize.py
└── resolver.entry

skills/valuation/spine/
├── SKILL.md
├── spine.py
├── test_spine.py
└── resolver.entry

skills/synthesis/handoff/
├── SKILL.md
├── handoff.py
├── test_handoff.py
└── resolver.entry
```

## Implementation Steps

1. Fill each M1 bundle's `SKILL.md` from `specs/SKILL-template.md`.
2. Build `A-1 EDGAR`:
   - resolve ticker to CIK
   - fetch or load company facts
   - extract the required annual 10-K facts with tag fallbacks
   - provenance-wrap every fact
3. Add frozen AAPL fixtures:
   - `company_tickers.json`
   - `aapl_companyfacts.json`
   - frozen price and risk-free inputs
4. Build `B-1 Normalize` as a typed pass-through with an empty normalization log.
5. Build minimal `A-2 Price` and `A-3 Cost of Capital` adapters with fallbacks.
6. Build `B-2 WACC/ROIC`:
   - NOPAT
   - invested capital including and excluding goodwill
   - ROIC
   - WACC
   - spread
   - margin and turnover decomposition
7. Build bare `D-1 Handoff` envelope.
8. Add the M1 audit gate:
   - provenance present
   - facts trace to accepted filing forms
   - estimates carry derivations
   - numeric sanity checks pass
   - storage round-trip succeeds
9. Wire `analyze("AAPL")` end to end.

## Risks And Decisions

- XBRL tag selection is the main risk. M1 must fail closed on unresolved concepts and log which fallback tag resolved.
- Price feed failure must not block ROIC. WACC falls back to book-equity weights and flags `price_unavailable`.
- FRED failure must not block M1. Use `risk_free_fallback` from config and flag the substitution.
- Goodwill absence is allowed only as an explicit zero with a flag.
- M1 has no Analyst or Senior judgment. Any ratified placeholder in the handoff must be visibly marked as M1 skeleton output.

## Expected Result

Running `analyze("AAPL")` produces:
- CIK `0000320193`
- at least five fiscal years of sourced annual facts
- a populated Spine artifact with real, sane ROIC and WACC values
- a sparse handoff written under `data/runs/AAPL/{as_of}/`
- an audit gate pass on the happy path and failures on injected provenance or sanity faults
