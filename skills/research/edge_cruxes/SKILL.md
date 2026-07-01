# SKILL: C-5 Edge & Cruxes
type: analyst
triggers: [edge_cruxes, variant_view, falsifiable_cruxes]
reads: [schema_version]
knowledge: [/knowledge/Equity_Analysis_Runbook_v3.md §P5]
inputs: filed BusinessArtifact, MoatArtifact, CapAllocArtifact, ScenarioSetArtifact, GateCard, MethodDirective, ValuationRange, ExpectationsLine, Spine
outputs: EdgeCruxesArtifact containing needs_ratification AnalystDraft fields
output_contract: EdgeCruxesArtifact with nested AnalystDraft needs_ratification drafts
implementation: edge_cruxes.py
no_llm: false
llm_dependency: true

definition_of_done:
  1_contract: SKILL.md present and complete
  2_deterministic: M3.5 uses deterministic fixture-backed drafting only
  5_llm_evals: prompt and eval surface present for Analyst bundle shape
  6_resolver_trigger: registered in resolver.entry
  7_resolver_eval: analyze() routes through C-5 after Scenarios on GO
  8_check_resolvable: Edge and crux drafts resolve filed source artifacts
  9_e2e_smoke: participates in analyze("AAPL") offline
  10_filing_rules: outputs are schema-valid, evidence-backed, and exactly three field-falsifiable cruxes
