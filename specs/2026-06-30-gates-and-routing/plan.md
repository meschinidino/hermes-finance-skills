# M2b Gates And Routing — Plan

## Objective

Build the deterministic gates-and-routing layer that turns the M2a valuation path into a properly routed analysis path: financial screens file a provenance-complete Gate Card, base-rate lookup supplies an outside-view probability for forecasts, and the Method Router decides which valuation method the resolver may invoke.

This slice thickens the Accountant path only. It does not add Analysts, Senior gates, new valuation engines, or final investment judgment.

## Scope

In scope:
- `B-4 Screens` as a variant-aware, flags-not-verdicts screen bundle.
- `B-5 Base-Rate` as a callable reference-class lookup for forecast probability.
- `B-6 Method Router` as the required wrapper around the M2a DCF invocation.
- Offline frozen fixtures for screen inputs, industry classification, base-rate tables, and router examples.
- A populated `GateCard` artifact per `specs/filing-rules.md` §4.
- Resolver wiring that consults the router before invoking a valuation method.
- Schema-valid, provenance-complete outputs for every M2b artifact.

Out of scope:
- Analyst skills, prompts, evals, Senior ratification, and Senior gate behavior.
- New valuation engines beyond routing directives for later methods.
- DCF engine changes beyond making its invocation conditional on the router.
- EDGAR, WACC, price, and DCF provider work already completed in M1/M2a.
- Auto-kill behavior from lit screens.
- Live endpoints except integration smokes for any implementation that adds one.

## Prerequisite

M2b depends on the completed M1 and M2a paths:
- M1 supplies EDGAR facts, Normalize, Spine, primitives, storage, and audit enforcement.
- M2a supplies Price, Cost of Capital, and `B-3 DCF` forward/reverse valuation artifacts.

M2b must reuse existing `Provenance`, `Number`, `Header`, `Ratifiable`, `Storage`, config, and filing schemas. It must not duplicate M0/M1 contracts in the new skill code or specs.

## Proposed Architecture

After M2b, the resolver must route valuation before invoking any valuation method:

```text
analyze(ticker)
   ├─ A-1 EDGAR
   ├─ B-1 Normalize
   ├─ B-2 Spine
   ├─ A-2 Price
   ├─ A-3 Cost of Capital
   ├─ B-4 Screens
   │    └─ GateCard → Storage + audit gate
   ├─ B-6 Method Router
   │    └─ method directive
   └─ valuation step
        ├─ if directive.method == "DCF" → B-3 DCF
        ├─ if directive.method == "normalized_mid_cycle" → defer method, file directive
        ├─ if directive.method == "financial_model" → defer method, file directive
        ├─ if directive.method == "rNPV" → defer method, file directive
        ├─ if directive.method == "SOTP" → defer method, file directive
        └─ if directive.method == "NAV" → defer method, file directive
```

`B-6 Method Router` wraps the M2a DCF engine. It is not a standalone skill that merely files an opinion. The existing unconditional DCF path in `resolver.py` becomes the router's default-for-cash-generators branch. After M2b, DCF fires only when the router selects it.

## Skill Bundles Created In M2b

All M2b bundles are Accountants (`no_llm: true`). Each must fill `specs/SKILL-template.md` and include no `prompt.md` or `eval/`.

```text
skills/valuation/screens/
├── SKILL.md
├── screens.py
├── test_screens.py
└── resolver.entry

skills/valuation/base_rate/
├── SKILL.md
├── base_rate.py
├── test_base_rate.py
└── resolver.entry

skills/valuation/method_router/
├── SKILL.md
├── method_router.py
├── test_method_router.py
└── resolver.entry
```

`test_integration.py` is required only if a bundle implementation hits a live endpoint. The intended M2b implementation is fixture-backed and offline, so no live integration smoke is expected unless the implementation chooses a live source.

## Implementation Steps

1. Fill the three M2b `SKILL.md` files from `specs/SKILL-template.md`.
2. Freeze CI fixtures under `tests/fixtures/`:
   - manufacturer screen inputs;
   - non-manufacturer screen inputs;
   - emerging-market screen inputs for the Z-double-prime plus 3.25 variant;
   - lit Beneish or other screen case;
   - base-rate reference-class table;
   - cash-generator and optionality router cases.
3. Build `B-4 Screens`:
   - source every screen input from EDGAR-derived facts or documented computed values;
   - auto-select the Altman variant from industry classification;
   - compute Altman Z, Beneish M, Piotroski F, and smoke checks;
   - record the selected Altman variant in the `GateCard`;
   - file flags and `dig_items`, never automatic screen-based kills.
4. Build `B-5 Base-Rate`:
   - accept forecast `metric`, `rate`, `horizon`, and `company_size_decile`;
   - return the matching Mauboussin reference-class probability;
   - return `low_probability_bucket`;
   - cite the reference class used.
5. Build `B-6 Method Router`:
   - classify the asset as `cash-generator`, `cyclical`, `financial`, `optionality`, or `asset-NAV`;
   - emit a method directive;
   - route `cash-generator` names to the existing M2a DCF path;
   - route optionality/pre-revenue names away from plain DCF to an `rNPV`, `SOTP`, or `NAV` directive as appropriate;
   - make the resolver consult this directive before valuation.
6. Extend resolver valuation wiring:
   - remove unconditional DCF invocation;
   - call the router before valuation;
   - invoke DCF only for a DCF directive;
   - file the directive when the selected method is deferred to a later milestone.
7. Extend audit checks only as needed to reject M2b outputs with missing provenance, missing derivations, invalid Gate Card shape, or unreachable method directives.

## Risks And Decisions

- Screens are escalation tools, not decisions. A lit Beneish M-Score or distress Altman zone must route to scrutiny and `dig_items`; it must not halt the run by itself.
- Altman Z is variant-sensitive. Using the manufacturer model for a non-manufacturer creates false precision, so variant selection and variant recording are acceptance-critical.
- Base-rate lookup is deliberately simple in M2b. It is a clean callable the M3 Analysts can consult, not an Analyst judgment surface.
- The Method Router is load-bearing. If it is not wired into resolver valuation invocation, M2b is incomplete even if the router skill passes unit tests.
- Optionality/pre-revenue names must not fall through to plain DCF. The router is the biotech-DCF guard required by the mission invariant that method matches asset.
- CI must stay offline and deterministic. Live calls belong only in integration smoke tests.

## Expected Result

Running `analyze("AAPL")` after M2b implementation produces:
- a filed, schema-valid `gate_card.json`;
- Altman, Beneish, Piotroski, and smoke checks with complete provenance;
- flags and `dig_items` for lit screens, not screen-driven halts;
- a method directive classifying AAPL as a cash-generator unless fixture facts indicate otherwise;
- DCF valuation only because the router selected DCF;
- no Analyst drafts, no Senior gates, and no new non-DCF valuation engine.
