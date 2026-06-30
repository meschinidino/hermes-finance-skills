# SKILL: A-3 Cost Of Capital
type: accountant
triggers: [cost_of_capital, m1_cost_of_capital]
reads: [cost_of_capital, tax, betas]
knowledge: []
inputs: ticker, Config
outputs: CostOfCapitalInputs
no_llm: true

definition_of_done:
  1_contract: SKILL.md present and complete
  2_deterministic: no LLM used
  3_unit_tests: config values become provenance-wrapped inputs
  4_integration_tests: optional live FRED smoke only
  6_resolver_trigger: resolver.entry present
  7_resolver_eval: analyze() routes through build_cost_of_capital_inputs
  8_check_resolvable: no external dependency hardcoded
  9_e2e_smoke: participates in analyze("AAPL")
  10_filing_rules: all inputs are estimate Numbers with derivations

