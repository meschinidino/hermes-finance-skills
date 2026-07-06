# SKILL: D-4 Calibration
type: accountant
triggers: [calibration, calibration_review, calibration_performance]
reads:   []
knowledge: []
inputs:  terminal handoff or local review payload
outputs: CalibrationCall, CalibrationReview, RoutingCorrectnessReview, EscalationCorrectnessReview
no_llm:  true

definition_of_done:
  1_contract:          SKILL.md present and complete
  2_deterministic:     no LLM used
  3_unit_tests:        focused calibration persistence and review-ingestion tests
  6_resolver_trigger:  registered in the resolver
  7_resolver_eval:     calibration-review CLI routes to record_calibration_review
  8_check_resolvable:  uses the typed calibration store capability
  9_e2e_smoke:         review ingestion appends to the local calibration store
  10_filing_rules:     outputs are schema-valid per filing-rules.md
