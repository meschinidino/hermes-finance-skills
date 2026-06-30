# SKILL: B-1 Normalize
type: accountant
triggers: [normalize_financials, m1_normalize]
reads: []
knowledge: []
inputs: EdgarFacts
outputs: NormalizedFinancials
no_llm: true

definition_of_done:
  1_contract: SKILL.md present and complete
  2_deterministic: near-identity adapter; no LLM
  3_unit_tests: pass-through preserves facts and provenance
  6_resolver_trigger: resolver.entry present
  7_resolver_eval: analyze() routes through normalize_financials
  8_check_resolvable: no duplicate primitive definitions
  9_e2e_smoke: participates in analyze("AAPL")
  10_filing_rules: does not strip provenance

