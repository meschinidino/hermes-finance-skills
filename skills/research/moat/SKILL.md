# SKILL: C-2 Moat
type: analyst
triggers: [moat_analysis, senior_review_moat]
reads: [schema_version]
knowledge: [/knowledge/Equity_Analysis_Runbook_v3.md §15]
inputs: EdgarFacts, Spine, filed run artifact paths, frozen moat evidence fixture
outputs: MoatArtifact containing needs_ratification AnalystDraft fields
output_contract: MoatArtifact with AnalystDraft needs_ratification drafts
implementation: moat.py
no_llm: false
llm_dependency: true

definition_of_done:
  1_contract: SKILL.md present and complete
  2_deterministic: M3.3 uses deterministic fixture-backed drafting only
  5_llm_evals: prompt and eval surface present for Analyst bundle shape
  6_resolver_trigger: registered in resolver.entry
  7_resolver_eval: analyze() routes through C-2 after the C-1 early gate GO path
  8_check_resolvable: Moat drafts are audit-enforced with resolvable and period-consistent EvidenceRef targets
  9_e2e_smoke: participates in analyze("AAPL") offline
  10_filing_rules: outputs are schema-valid, evidence-backed, and Senior-ratifiable only
