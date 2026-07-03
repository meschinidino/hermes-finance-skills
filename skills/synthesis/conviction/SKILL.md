# SKILL: D-2 Conviction
type: accountant
triggers: [conviction, d2_conviction]
reads: []
knowledge: []
inputs: SynthesisPayload
outputs: ConvictionArtifact
no_llm: true

definition_of_done:
  1_contract: SKILL.md present and complete
  2_deterministic: no LLM used
  3_unit_tests: fixture-backed synthesis payload validates conviction and sizing inputs
  6_resolver_trigger: registered in the resolver after M3.7 ratification
  7_resolver_eval: analyze() routes through build_conviction
  8_check_resolvable: consumes only filed, Senior-decided artifacts
  9_e2e_smoke: participates in analyze("AAPL") and analyze("MRNA")
  10_filing_rules: output carries Header and provenance-complete Number values
