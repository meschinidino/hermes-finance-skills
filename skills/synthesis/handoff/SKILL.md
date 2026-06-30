# SKILL: D-1 Bare Handoff
type: accountant
triggers: [bare_handoff, m1_handoff]
reads: []
knowledge: []
inputs: ticker, cik, Spine, PriceResult
outputs: BareHandoff
no_llm: true

definition_of_done:
  1_contract: SKILL.md present and complete
  2_deterministic: no LLM used
  3_unit_tests: sparse handoff validates and preserves spine
  6_resolver_trigger: resolver.entry present
  7_resolver_eval: analyze() routes through build_handoff
  8_check_resolvable: explicit M1 skeleton, no Senior judgment
  9_e2e_smoke: participates in analyze("AAPL")
  10_filing_rules: embedded spine remains provenance-complete

