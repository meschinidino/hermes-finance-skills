# SKILL: C-3 CapAlloc
type: analyst
triggers: [capital_allocation_analysis, senior_review_capalloc]
reads: [schema_version]
knowledge: [/knowledge/Equity_Analysis_Runbook_v3.md §16]
inputs: EdgarFacts, Spine, filed run artifact paths, frozen capital allocation evidence fixture
outputs: CapAllocArtifact containing needs_ratification AnalystDraft fields
output_contract: CapAllocArtifact with AnalystDraft needs_ratification drafts
implementation: capalloc.py
no_llm: false
llm_dependency: true

definition_of_done:
  1_contract: SKILL.md present and complete
  2_deterministic: M3.3 uses deterministic fixture-backed drafting only
  5_llm_evals: prompt and eval surface present for Analyst bundle shape
  6_resolver_trigger: registered in resolver.entry
  7_resolver_eval: analyze() routes through C-3 after the C-1 early gate GO path
  8_check_resolvable: CapAlloc drafts are audit-enforced with resolvable and period-consistent EvidenceRef targets
  9_e2e_smoke: participates in analyze("AAPL") offline
  10_filing_rules: outputs are schema-valid, evidence-backed, and Senior-ratifiable only
