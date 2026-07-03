# Resolver Route And Escalation Matrix

M4c makes the resolver path explicit and auditable. The resolver remains the only orchestrator; this document is the canonical route contract and `skills.control_flow.audit_route_events` enforces the ordered step manifest used by `resolver.py`.

## Routing Table

| Step | Role | Required Inputs | Produced Outputs | Audit Before Consumption | Halt Behavior | Senior Touchpoint | Escalation Owner |
|---|---|---|---|---|---|---|---|
| A-1 EDGAR | Accountant | ticker | EDGAR facts | schema/provenance checks downstream | unknown ticker rejects | none | resolver |
| A-2 Price | Accountant | ticker, EDGAR facts | price result | Number provenance audit downstream | source failure rejects | none | resolver |
| A-3 Cost of Capital | Accountant | config, price, EDGAR facts | CoC inputs | Number provenance audit downstream | source/config failure rejects | none | resolver |
| B-1 Normalize | Accountant | EDGAR facts | normalized financials | downstream accountant audits | missing concepts reject | none | resolver |
| B-2 Spine | Accountant | normalized financials, CoC, price | `spine.json` | `audit_artifact` / M1 handoff audit | audit failure | none | resolver |
| D-1 Bare Handoff | Accountant | spine, price | `handoff.json` | `audit_m1_handoff` | audit failure | none | resolver |
| C-1 Business | Analyst | EDGAR facts, filed run dir | `business.json` | `audit_analyst_artifact` | audit failure | none | resolver |
| Business Early Gate | Senior | `business.json` | `business_early_gate.json` | identity independence before call | `business_no_go` KillMemo | early gate | Senior |
| B-4 Screens | Accountant | EDGAR facts, price, industry | `gate_card.json` | `audit_artifact` | `gate_kill` KillMemo if verdict is KILL | none | Senior for verdict later |
| B-6 Method Router | Accountant | normalized financials, EDGAR, config | `method_directive.json` | `audit_artifact` | unsupported route rejects or defers | none | resolver |
| B-3 DCF | Accountant | DCF-routed method, normalized, price, CoC | `valuation_range.json`, `expectations_line.json` | `audit_artifact` | audit failure | none | resolver |
| B-5 Base-Rate | Accountant | DCF scenario revenue-growth drivers | `base_rate_*_revenue_growth.json` | `audit_artifact` | route audit failure if missing on DCF route | none | resolver |
| C-4 Scenarios | Analyst | method directive, valuation artifacts or route deferral, B-5 anchors on DCF | `scenarios.json` | `audit_scenario_set` | audit failure | none | Senior ratifies probabilities later |
| C-5 Edge/Cruxes | Analyst | filed C-1/C-4, gate, route, spine | `edge_cruxes.json` | `audit_edge_cruxes` | audit failure | none | Senior ratifies later |
| C-6 Risk | Analyst | filed C-1/C-5, route, scenarios | `risk.json` | `audit_risk_artifact` | audit failure | none | Senior ratifies later |
| M3.7 Consolidated Ratification | Senior | all B-4 and C-1..C-6 review packages | `senior_review_package.json`, `senior_decision_package.json` | identity independence and `audit_senior_decision_package` | identity violation KillMemo | consolidated ratification | Senior |
| D-2 Conviction | Accountant/Synthesis | synthesis payload, Senior decisions | `conviction.json` | D-2 model validation | audit failure | none | resolver |
| Final Lean Ratification | Senior | `conviction.json` final lean review | `final_lean_review_package.json`, `final_lean_decision_package.json` | identity independence and decision package audit | overturn without replacement KillMemo | final lean ratification | Senior |
| D-3 Review Packager | Synthesis | synthesis payload, D-2, final lean decision | `final_handoff.json` | `FinalHandoff` validation | not run on halted paths | none | resolver |

## Route Behavior

AAPL follows the DCF route: B-6 selects `DCF`, B-3 files valuation artifacts, B-5 files one base-rate anchor per DCF revenue-growth scenario, and C-4 consumes those anchors before Senior ratification.

MRNA follows the non-DCF `rNPV` route: B-6 selects `rNPV`, B-3 and B-5 are not fabricated, and C-4 uses route-specific optionality scenario values with `valuation_deferred` context.

Parallelism is deferred in M4c. The current slice is governance and correctness work; parallel execution would require a separate proof that no shared artifact writes, Senior touchpoints, or audit dependencies are reordered.

## Escalation Matrix

| Condition | Resolver Behavior | Terminal Artifact |
|---|---|---|
| Audit failure | fail closed with the raised audit error unless it is a route/halt branch | none unless converted to KillMemo |
| Missing source artifact | fail closed before downstream consumption | none |
| KILL gate | stop immediately | `kill_memo.json` with `halt_kind=gate_kill` |
| Business NO-GO | stop immediately after early gate | `kill_memo.json` with `halt_kind=business_no_go` |
| Unsupported valuation method | route-specific deferral only when B-6 marks it deferred; no DCF fabrication | final handoff may carry deferred valuation |
| Senior identity conflict | reject before Senior call or return an identity halt | `kill_memo.json` when caught in resolver branch |
| Senior overturn without replacement | stop before D-3 | `kill_memo.json` with `halt_kind=senior_overturn_without_replacement` |
| Live Senior API failure | fail closed; no offline fallback | no fallback artifact unless caller catches and files |
| Route-table mismatch | stop before D-3 | `kill_memo.json` with `halt_kind=route_audit_violation` |

## Manifest Audit Requirements

The route manifest records ordered step ids, produced artifacts, audits, Senior touchpoint class, and halt status. Enforcement checks that documented steps are present in order, Senior touchpoints occur only at early gate, M3.7, and final lean ratification, DCF routes contain B-3 and B-5, non-DCF routes omit DCF-only artifacts, and D-3 never runs on halted paths.
