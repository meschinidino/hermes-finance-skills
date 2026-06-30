# SKILL: B-2 WACC/ROIC Spine
type: accountant
triggers: [wacc_roic_spine, m1_spine]
reads: [tax, invested_capital, cost_of_capital, betas]
knowledge: []
inputs: NormalizedFinancials, CostOfCapitalInputs, PriceResult, excess_cash_pct
outputs: Spine
no_llm: true

definition_of_done:
  1_contract: SKILL.md present and complete
  2_deterministic: no LLM used
  3_unit_tests: formulas and audit faults covered with fixture values
  6_resolver_trigger: resolver.entry present
  7_resolver_eval: analyze() routes through build_spine
  8_check_resolvable: reuses M0 Number and Provenance
  9_e2e_smoke: participates in analyze("AAPL")
  10_filing_rules: estimates have derivations and computed provenance

