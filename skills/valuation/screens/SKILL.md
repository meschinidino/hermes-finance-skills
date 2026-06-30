# SKILL: B-4 Screens
type: accountant
triggers: [screens, m2b_screens, gate_card]
reads: []
knowledge: []
inputs: EdgarFacts, PriceResult | ScreenInputSet
outputs: GateCard
no_llm: true

definition_of_done:
  1_contract: SKILL.md present and complete
  2_deterministic: Altman, Beneish, Piotroski, smoke, and dig-item logic use pure Python
  3_unit_tests: manufacturer, non-manufacturer, emerging-market, and lit Beneish fixtures are covered
  4_integration_tests: n/a; fixture-backed and offline
  6_resolver_trigger: resolver.entry present
  7_resolver_eval: analyze("AAPL") routes through build_gate_card
  8_check_resolvable: uses shared primitives/artifact models and does not duplicate M0/M1 contracts
  9_e2e_smoke: files gate_card.json in the run directory
  10_filing_rules: every output Number is provenance-complete and computed values include derivations
