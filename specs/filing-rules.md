# filing-rules.md — Provenance Contract & Artifact Schemas

The company's filing system: every fact in a known place, in a known format, so the org is **auditable**. This turns the constitution's "schema or rejected" from a principle into an enforceable contract — the **audit layer (check-resolvable) runs the rejection rules in §5** before any artifact is filed or passed downstream.

Schemas are expressed in pydantic-v2-transcribable notation. They are the contract; the coding agent implements them as pydantic models.

---

## 1. The one rule
**No number is created, filed, passed between skills, or shown without provenance.** A bare `float` never crosses a skill boundary. Everything below exists to enforce that.

---

## 2. Primitives (every artifact is built from these)

```python
class Provenance:
    tag: str                  # resolving concept, e.g. "us-gaap:Revenues"; "computed"; "external"
    form: Literal["10-K","10-Q","DEF 14A","Form 4","computed","external"]
    period: str               # "FY2025" | "Q1-2026" | "instant:2026-03-31"
    accession: str | None     # SEC accession; None for computed/external
    source_name: str | None   # "EDGAR" | "FRED:DGS10" | "Damodaran" | "Finnhub" | ...
    retrieved_at: datetime

class Number:                 # the atomic unit — never a naked float
    value: float
    unit: Literal["USD_millions","ratio","percent","shares","USD_per_share","years","x"]
    kind: Literal["fact","estimate","judgment"]     # the Fact/Estimate/Judgment invariant, made concrete
    provenance: Provenance
    derivation: str | None    # REQUIRED when kind != "fact": formula + refs to input Numbers

class Ratifiable[T]:          # any judgment the Senior must sign
    draft: T
    evidence: list[str]       # REQUIRED, non-empty — no naked drafts
    needs_ratification: bool = True
    decision: Literal["ratified","overturned"] | None = None
    decided_by: str | None    # the injected Senior identity, set on decision
    final: T | None           # set on ratify (=draft) or overturn (=Senior's value)
```

**Derivation rule.** A computed `Number` (`kind="estimate"`, `provenance.form="computed"`) records its formula and references the input Numbers it was built from, so an audit can walk the chain back to source `fact`s. ROIC traces to NOPAT and invested capital, which trace to EDGAR line items. No computed value is a dead end.

**Artifact header.** Every artifact carries:
```python
class Header:
    schema_version: str       # for evolving the contract without breaking old runs
    produced_by: str          # skill id, e.g. "B-2"
    produced_at: datetime
```

---

## 3. Where things live (filing locations — see tech-stack layout)

| Artifact | Location | Format |
|---|---|---|
| Per-run artifacts (Gate Card → Handoff) | `data/runs/{ticker}/{as_of}/{artifact}.json` | JSON |
| Source cache (EDGAR / Damodaran / FRED) | `data/cache/{source}/{key}.json` (+ refresh metadata) | JSON |
| Calibration log | `data/pack.db` | SQLite, append-only |

---

## 4. Artifact schemas

```python
# P0
class GateCard:
    header: Header; ticker: str; cik: str
    altman:    {variant: str, z: Number, zone: Literal["safe","grey","distress"]}
    beneish:   {m: Number, flag: bool}
    piotroski: {f: Number}
    smoke:     {restatement: bool, auditor_change: bool, ni_cfo_gap_widening: bool,
                dso_trend: str, inventory_trend: str}
    investability: {adv_usd: Number, float_shares: Number, share_class_risk: str, related_party: str}
    verdict: Ratifiable[Literal["PASS","DIG","KILL"]]
    dig_items: list[str]
    kill_reason: str | None

# P0.5 — the Spine (all lists indexed by `years`)
class Spine:
    header: Header; years: list[str]
    wacc: list[Number]; nopat: list[Number]
    invested_capital_incl_gw: list[Number]; invested_capital_ex_gw: list[Number]
    roic_incl_gw: list[Number]; roic_ex_gw: list[Number]
    spread: list[Number]                         # ROIC − WACC per year
    nopat_margin: list[Number]; capital_turnover: list[Number]   # spread decomposition

# P2
class NormalizationLine:
    item: str; amount: Number; rationale: str
    recurring: Ratifiable[bool]                   # the recurring? call is judgment

class FinancialPanel:
    header: Header; years: list[str]
    revenue: list[Number]; revenue_cagr_5y: Number
    gross_margin: list[Number]; operating_margin: list[Number]
    roic: list[Number]; spread: list[Number]      # carried from Spine
    fcf: list[Number]; fcf_conversion: list[Number]
    net_debt_ebitda: list[Number]; maturity_wall: list[{year: str, amount: Number}]
    diluted_shares: list[Number]; sbc: list[Number]
    working_capital_intensity: list[Number]
    normalization_log: list[NormalizationLine]

# P3
class ExpectationsLine:
    header: Header
    implied: {revenue_growth: Number, years: Number, margin: Number, terminal_roic: Number}
    wacc_band: {low: Number, high: Number}
    frame: Literal["DCF","NAV","SOTP","rNPV"]
    frame_justification: str

# P4
class Scenario:
    name: Literal["bear","base","bull"]
    assumptions: list[{driver: str, value: Number, base_rate_check: str}]
    value: Number
    probability: Ratifiable[float]                # Senior-owned weight

class ValuationRange:
    header: Header
    scenarios: list[Scenario]                     # exactly 3
    method: Literal["DCF","normalized_mid_cycle","financial_model","rNPV","SOTP","NAV"]
    sensitivity: list[{variable: str, low: Number, high: Number, value_impact: Number}]

# P5
class Crux: { claim: str, metric: str, threshold: str }
class EdgeStatement:
    header: Header
    steelman_no_trade: str                        # required
    counterparty: str                             # required
    variant_view: str | None                      # None ⇒ "fairly priced, pass"
    cruxes: list[Crux]                            # exactly 3
    catalysts: list[{event: str, timing: str}]

# P6
class RiskKillSheet:
    header: Header
    premortem: str
    bear_case_narrative: str
    modellable: list[{risk: str, impact: Literal["low","med","high"],
                      likelihood: Literal["low","med","high"]}]
    tail_risks: list[str]                         # separate bucket; non-empty
    bear_case_value: Number
    kill_metric: {metric: str, threshold: str}

# P7
class SizingInputs:
    header: Header
    up_down_ratio: Number
    days_to_build: Number; days_to_exit: Number
    book_overlap: str
    # NO size field — size is the Senior's stamp, never the pack's output

# Final composite
class Handoff:
    header: Header
    ticker: str; price: Number; as_of: date
    lean: Ratifiable[Literal["Buy","Watch","Pass"]]
    conviction: Literal["Low","Med","High"]; conviction_score: int   # 0–10
    horizon: Literal["hold_for_quality","catalyst"]; review_by: date
    thesis: str                                   # 3 sentences
    whats_priced_in: ExpectationsLine
    valuation_range: ValuationRange
    cruxes: list[Crux]                            # exactly 3
    risk: RiskKillSheet
    edge: EdgeStatement
    sizing_inputs: SizingInputs
    confidence_and_gaps: {least_sure_about: str, couldnt_verify: list[str], would_raise_conviction: str}
    revisit_if: list[str]                         # non-empty
    data_room: {gate_card: GateCard, spine: Spine, panel: FinancialPanel,
                sources: list[Provenance]}

# When P0 = KILL — the only artifact a killed name may file
class KillMemo:
    header: Header; ticker: str
    gate: str                                     # which gate tripped
    reason: str                                   # one paragraph; nothing else

# Calibration (SQLite, append-only)
class CalibrationCall:
    id: str; date: date; ticker: str
    lean: str; conviction: str; conviction_score: int
    base_value: float; bear_value: float; review_by: date; kill_metric: str
class CalibrationReview:
    call_id: str; reviewed_at: date
    what_happened: str
    cruxes_held: list[str]; cruxes_broke: list[str]
    right_for_the_reasons: bool
```

---

## 5. Rejection rules (the audit layer enforces these; violation = artifact invalid, progression blocked)

**Provenance & numbers**
- Any `Number` missing `provenance` → reject.
- `kind="fact"` whose `provenance.form ∉ {10-K, 10-Q, DEF 14A, Form 4}` → reject (a fact must trace to a filing).
- `kind != "fact"` missing `derivation` → reject (computed values must be walkable).
- Arithmetic mixing incompatible `unit`s → reject.
- Computed total fails to reconcile to its filing total beyond tolerance (default **0.5%**) → **audit fail** (halt branch).

**Judgment & ratification**
- `Ratifiable.evidence` empty → reject (no naked drafts).
- Any `Ratifiable` reaching `Handoff` with `decision == None` → reject (everything signed before final).

**Structural invariants**
- `ValuationRange.scenarios` count ≠ 3 → reject.
- `EdgeStatement.cruxes` count ≠ 3 → reject.
- `EdgeStatement.counterparty` empty or ∈ {"no one","nobody","they're dumb", trivial variants} → reject → force "pass".
- `RiskKillSheet.tail_risks` empty → reject (the matrix-blind-spot enforcement).
- `Handoff.confidence_and_gaps` empty, or `revisit_if` empty → reject (mandatory sections).

**Kill path**
- Gate verdict = `KILL` ⇒ only a `KillMemo` may be filed for that run; a full `Handoff` under a KILL verdict → reject.

---

## 6. Schema versioning
Every artifact carries `schema_version`. The contract may evolve, but the **calibration log is append-only and long-lived** — old records must remain readable. Bump the version on any breaking field change; never rewrite history in `pack.db`. Migrations are additive (new nullable fields), not destructive.
