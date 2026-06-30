# SKILL: B-3 DCF
type: accountant
triggers: [dcf, m2a_dcf]
reads: [dcf, cost_of_capital.wacc_band_bps, tax]
knowledge: []
inputs: NormalizedFinancials, EdgarFacts, PriceResult, CostOfCapitalInputs, Config
outputs: ValuationRange, ExpectationsLine
no_llm: true

definition_of_done:
  1_contract: SKILL.md present and complete
  2_deterministic: one stdlib DCF core, no LLM or Analyst judgment
  3_unit_tests: forward, reverse convergence at both WACC bounds, and non-convergence are fixture-covered
  4_integration_tests: n/a; pure compute
  6_resolver_trigger: resolver.entry present
  7_resolver_eval: analyze("AAPL") routes through build_dcf_artifacts
  8_check_resolvable: uses shared primitives/config/artifact models and does not duplicate M0/M1 contracts
  9_e2e_smoke: files valuation_range.json and expectations_line.json in the run directory
  10_filing_rules: every output Number is provenance-complete and computed values include derivations
