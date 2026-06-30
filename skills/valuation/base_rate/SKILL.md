# SKILL: B-5 Base-Rate
type: accountant
triggers: [base_rate, m2b_base_rate, outside_view]
reads: []
knowledge: []
inputs: BaseRateForecast
outputs: BaseRateResult
no_llm: true

definition_of_done:
  1_contract: SKILL.md present and complete
  2_deterministic: offline reference-class lookup only
  3_unit_tests: known forecast and low-probability bucket cases are covered
  4_integration_tests: n/a; no live endpoint
  6_resolver_trigger: resolver.entry present
  7_resolver_eval: callable without LLM or Analyst flow
  8_check_resolvable: uses shared primitives/artifact models and does not duplicate M0/M1 contracts
  9_e2e_smoke: available to later Analyst skills as a deterministic lookup
  10_filing_rules: output probability is provenance-complete and source-cited
