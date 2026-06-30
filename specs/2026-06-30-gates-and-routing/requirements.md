# M2b Gates And Routing — Requirements

## Functional Requirements

1. `analyze(ticker)` must run through the completed M1/M2a path and then consult M2b gates and routing before valuation.
2. `B-4 Screens` must emit a `GateCard` artifact matching `specs/filing-rules.md` §4.
3. `B-4 Screens` must compute Altman Z with the correct variant auto-selected from industry classification.
4. `B-4 Screens` must support the manufacturer Altman Z variant.
5. `B-4 Screens` must support the Altman Z-double-prime non-manufacturer variant.
6. `B-4 Screens` must support the emerging-market Z-double-prime plus 3.25 variant when the company is classified as emerging-market.
7. `B-4 Screens` must record the selected Altman variant in the `GateCard`.
8. `B-4 Screens` must compute Beneish M-Score.
9. `B-4 Screens` must compute Piotroski F-Score.
10. `B-4 Screens` must compute the smoke checks required by `GateCard.smoke`: restatement, auditor change, NI/CFO gap widening, DSO trend, and inventory trend.
11. All screen inputs must be sourced and provenance-complete.
12. All computed screen outputs must be `Number` values with derivations.
13. A lit screen, including `Beneish M-Score > -1.78`, must produce a flag or `dig_items`, not an automatic halt.
14. A lit screen must route to scrutiny; it must not by itself produce a `KILL` verdict.
15. `GateCard.verdict` may remain a ratifiable draft placeholder until M3, but the M2b artifact must clearly state that screen flags are not Senior-signed verdicts.
16. `B-5 Base-Rate` must accept forecast `metric`, `rate`, `horizon`, and `company_size_decile`.
17. `B-5 Base-Rate` must return the matching Mauboussin reference-class probability.
18. `B-5 Base-Rate` must return `low_probability_bucket` as a boolean.
19. `B-5 Base-Rate` must cite the reference class used for the match.
20. `B-5 Base-Rate` must be callable without invoking an LLM or Analyst flow.
21. `B-6 Method Router` must classify the asset as one of: `cash-generator`, `cyclical`, `financial`, `optionality`, or `asset-NAV`.
22. `B-6 Method Router` must emit a method directive.
23. The method directive must select one of the filing-rule valuation frames or methods: `DCF`, `normalized_mid_cycle`, `financial_model`, `rNPV`, `SOTP`, or `NAV`.
24. The method directive must include a plain-language routing reason and the sourced indicators used for classification.
25. The resolver must consult `B-6 Method Router` before invoking any valuation method.
26. The resolver must invoke `B-3 DCF` only when the method directive selects `DCF`.
27. The existing unconditional DCF path in `resolver.py` must become the router's default-for-cash-generators branch.
28. Optionality or pre-revenue names must be routed away from plain DCF.
29. Optionality or pre-revenue names must receive an `rNPV`, `SOTP`, or `NAV` directive rather than a DCF invocation.
30. `B-6 Method Router` must not be implemented as a standalone skill that no resolver path calls.
31. Each M2b skill must be a completed Accountant folder bundle following `specs/SKILL-template.md`.

## Non-Functional Requirements

- M2b must stay portable and standalone.
- Runtime state must stay under `/data`.
- Skill code must live under `/skills`.
- Frozen CI fixtures must live under `tests/fixtures/`.
- CI must run offline from frozen fixtures.
- Live calls may run only in separate integration smoke tests.
- Accountants must fail closed and never impute missing concepts.
- The dependency tree must stay small and consistent with `specs/tech-stack.md`.
- M2b must not add Analysts, prompts, evals, Senior gates, or Senior ratification.
- M2b must not change the DCF engine except to make DCF invocation conditional on the router.

## Content And Data Requirements

### Screens Inputs

`B-4 Screens` must use EDGAR-derived or computed, provenance-complete inputs sufficient to compute:
- Altman working capital, retained earnings, EBIT, market value or book value of equity as required by variant, total liabilities, sales, and total assets;
- Beneish DSRI, GMI, AQI, SGI, DEPI, SGAI, LVGI, and TATA inputs;
- Piotroski profitability, leverage/liquidity/source-of-funds, and operating-efficiency signals;
- smoke-check inputs for restatements, auditor changes, accrual quality, receivables trend, and inventory trend.

If a required concept is missing, the Accountant must fail closed with an unresolved concept or insufficient history error. It must not impute a screen input to satisfy the formula.

### Altman Variant Selection

The implementation must map industry classification to Altman variant before computation:
- manufacturer or industrial operating company → manufacturer Altman Z;
- non-manufacturer operating company → Z-double-prime non-manufacturer;
- emerging-market operating company → emerging-market Z-double-prime plus 3.25.

The selected variant must be recorded in `GateCard.altman.variant`, and the formula derivation must name that variant.

### Screen Flags

Screen outputs are diagnostic:
- Beneish M-Score above `-1.78` flags earnings-manipulation scrutiny.
- Altman distress or grey zones flag solvency scrutiny.
- Low Piotroski F-Score flags quality/fundamental scrutiny.
- Smoke checks flag filing-quality or accounting-quality scrutiny.

These flags must populate `dig_items` or equivalent scrutiny metadata. They must not automatically halt the resolver and must not auto-file a `KillMemo`.

### Base-Rate Inputs And Output

Required input fields:
- `metric`: the forecasted metric, such as revenue growth, margin expansion, EPS growth, or ROIC improvement;
- `rate`: forecasted rate as a provenance-complete `Number` or an explicitly provenance-bearing structured forecast field;
- `horizon`: forecast horizon as a provenance-complete `Number` or an explicitly provenance-bearing structured horizon field;
- `company_size_decile`: company-size bucket used by the Mauboussin reference class, as a provenance-complete `Number` or an explicitly provenance-bearing structured bucket field.

`rate`, `horizon`, and `company_size_decile` must not cross the Base-Rate skill boundary as bare typed values. They must either be `Number` instances or structured fields that carry provenance, source metadata, and any required derivation, consistent with `specs/filing-rules.md` §1.

Required output fields:
- matched reference-class name;
- probability;
- `low_probability_bucket`;
- citation or source metadata for the reference-class table;
- input echo sufficient for audit.

The base-rate bundle is an outside-view lookup that M3 Analysts will consult. It must not draft a narrative, change a valuation, or make a recommendation.

### Method Router Inputs And Output

Router inputs must include the already available M1/M2a facts needed to classify the asset:
- revenue history and operating profit history;
- cash-flow or NOPAT history;
- sector or industry classification;
- balance-sheet composition;
- pre-revenue indicators when available;
- R&D or pipeline-heavy indicators when available;
- financial-institution indicators when available;
- asset-heavy or NAV-relevant indicators when available.

Required directive fields:
- asset class: `cash-generator`, `cyclical`, `financial`, `optionality`, or `asset-NAV`;
- method: `DCF`, `normalized_mid_cycle`, `financial_model`, `rNPV`, `SOTP`, or `NAV`;
- routing reason;
- sourced indicators used by the classification;
- whether the selected method is implemented in the current milestone;
- fallback behavior when the method is not yet implemented.

For M2b:
- `cash-generator` routes to existing `B-3 DCF`;
- `cyclical` routes to a `normalized_mid_cycle` directive;
- `financial` routes to a `financial_model` directive;
- `optionality` routes to `rNPV` or `SOTP`;
- `asset-NAV` routes to `NAV`.

If the selected method is not implemented yet, the resolver should file the directive and stop the valuation branch cleanly without pretending DCF is a substitute.

## Artifact Requirements

### GateCard

`B-4 Screens` must satisfy the `GateCard` schema in `specs/filing-rules.md`:
- `header.produced_by` identifies `B-4`;
- `ticker` and `cik` are present;
- `altman.variant`, `altman.z`, and `altman.zone` are present;
- `beneish.m` and `beneish.flag` are present;
- `piotroski.f` is present;
- all smoke checks are present;
- investability fields remain populated by existing available data or explicit M2b placeholders only if schema-compatible and provenance-honest;
- `verdict` is not treated as Senior-signed in M2b;
- `dig_items` captures lit screens and smoke flags;
- `kill_reason` remains `None` unless an already existing non-screen audit rule requires otherwise.

### Base-Rate Result

M2b implementation must add the Base-Rate result to `specs/filing-rules.md` as an additive, non-breaking artifact schema per §6. The artifact must include a `Header`, input echo, matched reference class, probability as a `Number`, `low_probability_bucket`, and source citation metadata.

### Method Directive

M2b implementation must add the Method Directive to `specs/filing-rules.md` as an additive, non-breaking artifact schema per §6. The artifact must include a `Header`, asset class, selected method, routing reason, sourced indicators, and implemented/deferred status.

The directive must be filed or otherwise captured in the run artifacts so validation can prove the resolver used it.

## Acceptance Criteria

- `analyze("AAPL")` writes a reloadable, schema-valid `GateCard`.
- Manufacturer and non-manufacturer fixtures select different Altman variants correctly.
- A lit Beneish fixture produces a flagged Gate Card, not a halted run.
- Base-rate lookup returns the expected Mauboussin bucket for a known forecast fixture.
- Resolver valuation invocation changes based on the router directive.
- A cash-generator fixture invokes `B-3 DCF`.
- An optionality/pre-revenue fixture is routed away from `B-3 DCF`.
- DCF is no longer invoked unconditionally by `resolver.py`.
- All M2b outputs are schema-valid and provenance-complete per `specs/filing-rules.md`.
- No M2b Accountant bundle includes `prompt.md` or `eval/`.
