# SKILL: B-6 Method Router
type: accountant
triggers: [method_router, m2b_method_router, valuation_route]
reads: [betas]
knowledge: []
inputs: NormalizedFinancials, EdgarFacts, Config
outputs: MethodDirective
no_llm: true

definition_of_done:
  1_contract: SKILL.md present and complete
  2_deterministic: asset class and method directive use fixed rules, no LLM
  3_unit_tests: cash-generator and optionality/pre-revenue routes are covered
  4_integration_tests: n/a; pure compute
  6_resolver_trigger: resolver.entry present
  7_resolver_eval: resolver consults the directive before valuation
  8_check_resolvable: uses shared primitives/config/artifact models and does not duplicate M0/M1 contracts
  9_e2e_smoke: analyze("AAPL") invokes DCF only through a DCF directive
  10_filing_rules: directive includes sourced indicators and deferred fallback behavior
