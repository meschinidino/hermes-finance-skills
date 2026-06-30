# SKILL: A-2 Price
type: accountant
triggers: [ticker_price, m1_price, m2a_price]
reads: []
knowledge: []
inputs: ticker, EdgarFacts, injected PriceFeed
outputs: PriceResult with current price, market cap, weighting basis, fallback flags
no_llm: true

definition_of_done:
  1_contract: SKILL.md present and complete
  2_deterministic: no LLM used
  3_unit_tests: frozen price fixture, market-cap derivation, and feed-down book-equity fallback covered
  4_integration_tests: live price smoke only in test_integration.py
  6_resolver_trigger: resolver.entry present
  7_resolver_eval: analyze() routes through fetch_price
  8_check_resolvable: host-specific feed remains injected and fallback uses EDGAR book equity
  9_e2e_smoke: participates in analyze("AAPL")
  10_filing_rules: external price and computed market-cap/fallback Numbers are provenance-wrapped
