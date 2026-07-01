# SKILL: C-4 Scenarios
type: analyst
triggers: [scenarios, scenario_probabilities, method_aware_scenarios]
reads: [schema_version]
knowledge: [/knowledge/Equity_Analysis_Runbook_v3.md §P4]
inputs: filed ValuationRange, filed ExpectationsLine, filed MethodDirective, filed BaseRateResult anchors, prior Analyst artifacts
outputs: ScenarioSetArtifact containing needs_ratification AnalystDraft probability fields
output_contract: ScenarioSetArtifact with nested AnalystDraft needs_ratification probability drafts
implementation: scenarios.py
no_llm: false
llm_dependency: true

definition_of_done:
  1_contract: SKILL.md present and complete
  2_deterministic: M3.4 uses deterministic fixture-backed drafting only
  5_llm_evals: prompt and eval surface present for Analyst bundle shape
  6_resolver_trigger: registered in resolver.entry
  7_resolver_eval: analyze() routes through C-4 after Moat and CapAlloc on GO
  8_check_resolvable: Scenario drafts resolve filed valuation, method-router, and base-rate anchors
  9_e2e_smoke: participates in analyze("AAPL") offline
  10_filing_rules: outputs are schema-valid, evidence-backed, and Senior-owned
