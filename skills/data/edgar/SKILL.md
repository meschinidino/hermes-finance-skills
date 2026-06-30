# SKILL: A-1 EDGAR
type: accountant
triggers: [ticker_facts, m1_edgar]
reads: []
knowledge: []
inputs: ticker
outputs: EdgarFacts
no_llm: true

definition_of_done:
  1_contract: SKILL.md present and complete
  2_deterministic: no LLM used
  3_unit_tests: frozen AAPL fixture resolves required concepts
  4_integration_tests: optional live EDGAR smoke only
  6_resolver_trigger: resolver.entry present
  7_resolver_eval: analyze() routes through fetch_edgar_facts
  8_check_resolvable: reuses M0 primitives and M1 artifacts
  9_e2e_smoke: participates in analyze("AAPL")
  10_filing_rules: facts are Number values with EDGAR provenance

