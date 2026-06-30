# SKILL: <id> <name>
type: accountant | analyst        # decides which bundle items + DoD items apply
triggers: [ ... ]                 # what routes here; must be registered in the resolver
reads:   [ conventions.yaml keys this skill depends on ]
knowledge: [ /knowledge/runbook.md §... ]   # Analysts: the section the rubric is built from
inputs:  <typed inputs>
outputs: <typed artifact, per filing-rules.md>
no_llm:  true | false             # Accountants true; Analysts false

definition_of_done:               # scoped per role type; N/A items omitted
  1_contract:          SKILL.md present and complete
  2_deterministic:     no LLM used for anything code can do
  3_unit_tests:        accountant → golden-fixture match | analyst → n/a
  4_integration_tests: live-endpoint smoke if the skill calls one
  5_llm_evals:         analyst → rubric conformance + ratification rate + red-team | accountant → n/a
  6_resolver_trigger:  registered in the resolver (resolver.entry)
  7_resolver_eval:     the trigger actually routes to this skill
  8_check_resolvable:  contract is satisfiable + DRY (does not duplicate another skill)
  9_e2e_smoke:         participates correctly in analyze() end-to-end
  10_filing_rules:     outputs are schema-valid and provenance-complete per filing-rules.md
