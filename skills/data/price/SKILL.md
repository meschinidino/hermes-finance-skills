# SKILL: A-2 Price
type: accountant
triggers: [ticker_price, m1_price]
reads: []
knowledge: []
inputs: ticker, shares, injected PriceFeed
outputs: PriceResult
no_llm: true

definition_of_done:
  1_contract: SKILL.md present and complete
  2_deterministic: no LLM used
  3_unit_tests: injected success and failure covered
  4_integration_tests: optional live price smoke only
  6_resolver_trigger: resolver.entry present
  7_resolver_eval: analyze() routes through fetch_price
  8_check_resolvable: host-specific feed remains injected
  9_e2e_smoke: participates in analyze("AAPL")
  10_filing_rules: external price is provenance-wrapped

