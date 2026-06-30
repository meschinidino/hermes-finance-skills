# SKILL: C-1 Business
type: analyst
triggers: [business_understanding, early_gate_context]
reads: [schema_version]
knowledge: [/knowledge/Equity_Analysis_Runbook_v3.md §14]
inputs: EdgarFacts, filed run artifact paths, frozen business evidence fixture
outputs: BusinessArtifact containing needs_ratification AnalystDraft fields
output_contract: BusinessArtifact with AnalystDraft needs_ratification drafts
implementation: business.py
no_llm: false
llm_dependency: true

definition_of_done:
  1_contract: SKILL.md present and complete
  2_deterministic: M3.2 uses deterministic fixture-backed drafting only
  5_llm_evals: prompt and eval surface present for Analyst bundle shape
  6_resolver_trigger: registered in resolver.entry
  7_resolver_eval: analyze() routes through C-1 before early gate
  8_check_resolvable: Business drafts are audit-enforced with resolvable EvidenceRef targets
  9_e2e_smoke: participates in analyze("AAPL") offline
  10_filing_rules: outputs are schema-valid and evidence-backed
