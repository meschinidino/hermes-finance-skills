# SKILL: D-4 Calibration
type: accountant
triggers: [calibration, calibration_review, calibration_report, calibration_performance, route_health]
reads:   [data/pack.db]
knowledge: []
inputs:  FinalHandoff, route manifest, terminal KillMemo route state, local calibration-review payload
outputs: CalibrationCall, CalibrationReview, RoutingCorrectnessReview, EscalationCorrectnessReview, CalibrationAnalytics
no_llm:  true

contract:
  role: accountant
  purpose: >
    Maintain the append-only feedback loop that measures decision quality and route health after
    resolver terminal states. D-4 never creates valuation logic, prompts the Senior, or changes the
    investment call; it records what the already-ratified run did and later accepts human/ops review
    payloads against that call.
  storage: CalibrationStore
  append_only_tables:
    - calibration_calls
    - calibration_reviews
    - routing_correctness_reviews
    - escalation_correctness_reviews
  terminal_behavior:
    final_handoff:
      - append one CalibrationCall keyed by ticker, as_of, and run_id
      - append one RoutingCorrectnessReview
      - append one EscalationCorrectnessReview per observed Senior touchpoint
    halted:
      - append RoutingCorrectnessReview and EscalationCorrectnessReview route health
      - do not append CalibrationCall
  cli:
    calibration-review: validates a review payload and appends a CalibrationReview for an existing call_id
    calibration-report: builds typed CalibrationAnalytics from stored calls, reviews, and health checks

guards:
  - D-4 is deterministic and must not call the injected LLM.
  - D-4 must not call Senior.gate or Senior.ratify.
  - D-4 must not fabricate DCF outputs for non-DCF routes.
  - CalibrationReview ingestion must reject unknown call_id values.
  - Repeated identical appends must be idempotent; same id with different payload must fail closed.
  - Halted paths record route health only, with no CalibrationCall.

definition_of_done:
  1_contract:          SKILL.md present and complete
  2_deterministic:     no LLM used; metrics are derived from persisted typed records
  3_unit_tests:        storage round trips, validation failures, idempotency, analytics, and CLI ingestion are covered
  4_integration_tests: n/a; no live endpoint
  6_resolver_trigger:  resolver.entry present and resolver terminal hooks append D-4 records
  7_resolver_eval:     analyze("AAPL") and analyze("MRNA") append calls plus route health; halted routes append route health only
  8_check_resolvable:  uses CalibrationStore and existing FinalHandoff/KillMemo artifacts; duplicates no M0 storage or primitive definitions
  9_e2e_smoke:         successful DCF, successful non-DCF, and halted paths participate in analyze() end-to-end
  10_filing_rules:     outputs are schema-valid per filing-rules.md and calibration log remains append-only
