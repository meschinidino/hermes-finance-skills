# SKILL: D-3 Review Packager
type: accountant
triggers: [review_packager, final_handoff, d3_review_packager]
reads: []
knowledge: []
inputs: SynthesisPayload, ConvictionArtifact
outputs: FinalHandoff
no_llm: true

definition_of_done:
  1_contract: SKILL.md present and complete
  2_deterministic: no LLM used
  3_unit_tests: final handoff validates and files from fixture-backed synthesis payload
  6_resolver_trigger: registered in the resolver after D-2
  7_resolver_eval: analyze() routes through build_review_package
  8_check_resolvable: refuses missing D-2 artifact and unresolved Senior decisions
  9_e2e_smoke: participates in analyze("AAPL") and analyze("MRNA")
  10_filing_rules: final output has Header, signed lean, sizing inputs, cruxes, risks, and provenance-complete numbers
