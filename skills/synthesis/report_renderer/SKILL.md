# SKILL: D-5 Report Renderer
type: accountant
triggers: [report_renderer, render_report, d5_report_renderer]
reads: []
knowledge: []
inputs: completed run directory containing final_handoff.json or kill_memo.json
outputs: report.md
no_llm: true

definition_of_done:
  1_contract: SKILL.md present and complete
  2_deterministic: no LLM, Senior, Analyst, network, or live data used
  3_unit_tests: full Handoff, method-deferred, KillMemo, and failure paths covered
  6_resolver_trigger: registered as a render-report command separate from analyze()
  7_resolver_eval: existing ticker analysis behavior is unchanged
  8_check_resolvable: refuses missing, conflicting, or invalid terminal artifacts
  9_e2e_smoke: renders completed AAPL and MRNA run directories
  10_filing_rules: rendered numbers include units and provenance summary
