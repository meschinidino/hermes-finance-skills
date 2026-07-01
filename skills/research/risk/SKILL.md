# SKILL: C-6 Risk
type: analyst
triggers: [risk, kill_metric, bear_case, premortem]
reads: [schema_version]
knowledge: [/knowledge/Equity_Analysis_Runbook_v3.md §P6]
inputs: filed BusinessArtifact, MoatArtifact, CapAllocArtifact, ScenarioSetArtifact, EdgeCruxesArtifact, GateCard, MethodDirective, ValuationRange, ExpectationsLine, Spine
outputs: RiskArtifact containing needs_ratification AnalystDraft fields
output_contract: RiskArtifact with nested AnalystDraft needs_ratification drafts
implementation: risk.py
no_llm: false
llm_dependency: true

definition_of_done:
  1_contract: SKILL.md present and complete
  2_deterministic: M3.6 uses deterministic fixture-backed drafting only
  5_llm_evals: prompt and eval surface present for Analyst bundle shape
  6_resolver_trigger: registered in resolver.entry
  7_resolver_eval: analyze() routes through C-6 after Edge & Cruxes on GO
  8_check_resolvable: Risk drafts resolve filed source artifacts
  9_e2e_smoke: participates in analyze("AAPL") offline
  10_filing_rules: outputs are schema-valid, evidence-backed, and keep tail risks separate from modellable risks
