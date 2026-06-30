# Equity Analysis Runbook (v3 — Implementable Spec)
### For a programming-capable analyst or an agent pipeline. Free data sources only.

This version is written to be *executed*, by a person who can code or by an agent pipeline. Each phase is a typed contract: defined inputs → deterministic procedure → a structured output artifact → a machine-checkable validation gate. Judgment that can't be mechanized is isolated, drafted by the executor, and flagged for a single human review at the end.

Read sections in order: **Operating Model** (who decides what, and when) → **House Conventions** (the config that makes "mechanical" actually reproducible) → **Data Layer** (where the free numbers come from) → **Phases 0–7** → **Handoff / Review / Conviction / Calibration** schemas.

---

## 1. Operating model

**Division of labour.** The executor (junior/agent) runs the whole pipeline and produces a complete package. The senior makes the call. The executor's deliverable is not a recommendation to rubber-stamp — it is a decision-ready package where every mechanical number is reproducible and every judgment is explicitly flagged with its evidence.

**Resolving "is the senior only needed at the end?"** Almost. The model is **draft-then-ratify**, not interleaved approval:

- Every judgment point in the pipeline (moat call, normalization choices, discount rate, scenario probabilities, edge validity) is **drafted by the executor** with evidence attached and tagged `needs_ratification: true`. The pipeline **does not stall** waiting for the senior — it proceeds to the end on its own tentative calls.
- The senior reviews **once**, at the end, via the consolidated **Senior Review Checklist** (§12), overturning drafted judgments where needed. This keeps senior judgment where it matters without making the senior a blocking dependency at N checkpoints × M names.
- **One exception — an early go/no-go gate after Phase 1.** A ~10-minute human (or rule-based) check: in-universe? gates clean? did the executor actually understand the business? If the business model is misread, every downstream phase is wasted, so this is the one cheap place to fail fast. In a fully automated pipeline this gate is a hard assertion set that halts and escalates on failure.

**Phase dependency graph (what can run in parallel).**

```
                 ┌─► P0 Gates ─────────────────────────┐
   filings ──────┤                                      │
   (EDGAR)       └─► P2 Financials ──┬─► P1 Business ────┤   [GO/NO-GO gate after P1]
                                     │   (needs ROIC)    │
                                     ├─► P3 Priced-in ───┼─► P5 Edge ──┐
                                     └─► P4 Scenarios ───┼─► P6 Risk ──┼─► P7 Sizing ─► HANDOFF
                                                         │             │
                                                         └─────────────┘
```

- **Critical path:** filings → P2 → P4 → P6 → P7 → handoff. Adding executors past ~2 does not shorten it.
- **Parallelizable:** the three P0 screens are mutually independent; P2 and the *factual* parts of P1 read the same filings concurrently; once P2 lands, P3 and P4 run in parallel; once P4 lands, P5 and P6 run in parallel.
- **One name = one owner** for the judgment spine (P1, P4, P5, P6) — understanding doesn't transfer across a handoff. Across *different* names, executors are fully independent; the shared bottleneck is the senior's review bandwidth, and the shared asset to centralize is **sector context** (comp set, sector betas, industry map) so it isn't rebuilt per name.
- **Tool the mechanical phases.** P0 screens, the P2 panel, the P3 reverse-DCF, and the P4 base-rate lookups are deterministic functions over EDGAR data — build them once as code/agent tools and the executor's scarce cycles go only to the flagged judgment work.

**One model, two modes.** Phase 3 (reverse-DCF: solve for implied expectations given price) and Phase 4 (forward DCF: solve for value given assumptions) are **the same DCF engine** run in two directions. Build one; do not build two.

---

## 2. House conventions (the config block)

This is the section that turns "mechanical" into "reproducible." Without fixed conventions, two executors compute different WACCs, different ROICs, and different valuations from the same filings — and the senior rejects all three. **These are the defaults. Override per-mandate by editing this block; everything downstream reads from it.** Time-sensitive values are marked `↻ refresh from source`.

### 2.1 Cost of capital (WACC)
| Input | Convention | Source | Current default |
|---|---|---|---|
| Risk-free rate | 10-yr US Treasury constant maturity | FRED series `DGS10` | ~4.18% ↻ |
| Equity risk premium | Damodaran **implied** ERP (US, mature market) | Damodaran datacurrent | 4.23% ↻ |
| Beta | Damodaran **industry unlevered beta**, relevered at the company's market D/E: `βL = βU × (1 + (1−tax)×D/E)` | Damodaran "Betas by Sector" | by industry ↻ |
| Cost of equity | CAPM: `Rf + βL × ERP` | computed | — |
| Cost of debt | `Rf + credit spread`; spread from synthetic rating (interest-coverage → Damodaran spread table) or actual interest expense / total debt if cleaner | Damodaran "synthetic rating" | — |
| Tax rate | Company's **marginal** rate — driven by the *company's* domicile, **not the analyst's location**. US-listed default: 21% federal + ~4% state ≈ **25%**. For non-US names pull per-country marginal rates from Damodaran (e.g. Argentina ≈ 35%). Use the **same** rate in NOPAT and the relevering formula | Damodaran marginal-tax dataset | 25% (US) ↻ |
| Weights | Market value of equity and debt | computed | — |

> **Why bottom-up beta:** it avoids regressing beta off price history (a flaky free-data dependency) and is more stable. The pipeline then needs a price feed for *only* current market cap — see §3.

### 2.2 Invested capital & ROIC
- **ROIC** = `NOPAT / Invested Capital`. **NOPAT** = `EBIT × (1 − tax rate)`, EBIT taken after the normalization in §2.3.
- **Invested Capital** = `Total Debt + Total Equity − Excess Cash`, equivalently operating assets − operating liabilities. Apply **one** treatment consistently across all years and all peers:
  - **Excess cash** default rule: cash & equivalents above **2% of trailing revenue** is "excess" and removed; below that, operating. (Override if the business clearly needs more/less.)
  - **Operating leases:** include capitalized lease liability in debt (post-ASC 842 it is on the balance sheet — use it).
  - **Goodwill:** report ROIC **both** ways — `ROIC (incl. goodwill)` measures returns on capital *deployed* (acquisition discipline); `ROIC (ex-goodwill)` measures the *operating* business. Flag which drives the thesis.
- **Value-creation test** = `ROIC − WACC` (the spread). Decompose the spread's source into NOPAT margin (differentiation) vs. invested-capital turnover (efficiency).

### 2.3 Normalization defaults
Every adjustment is logged as a line with rationale and a `recurring?` flag. The rule: **if it recurs, it is an operating cost, not an add-back** (and the recurrence is itself a red flag — note the deliberate tension with the P0 "serial one-time charges" smoke check: the executor *lists*, the senior *rules*).
- **Standard add-backs (treat as non-recurring → strip):** one-time litigation settlements, genuinely non-recurring restructuring, asset impairments/write-downs, M&A transaction costs, one-time tax items.
- **Never strip:** stock-based compensation (it is a real expense), "restructuring" that appears in ≥3 of the last 5 years, recurring "one-time" items.

### 2.4 Data hygiene
- **Fiscal years:** align to fiscal-year-end; build TTM by summing the last four quarters when a clean FY isn't current.
- **XBRL tag fallbacks (required):** companies tag differently. For revenue, try `Revenues` → `RevenueFromContractWithCustomerExcludingAssessedTax` → `SalesRevenueNet`. Maintain a fallback list per concept; log which tag resolved.
- **Provenance:** every stored number carries `{value, tag, form, period, accession, retrieved_at}`. No number without provenance.
- **Units:** USD millions internally; preserve per-share in actual units.

---

## 3. Data layer (all free)

EDGAR is the system of record for everything fundamental — which the runbook already requires as primary source. External dependencies reduce to three small, free lookups.

| Need | Source | Endpoint / access | Notes |
|---|---|---|---|
| **All fundamentals** (5–10 yr income/balance/cash) | SEC EDGAR XBRL | `https://data.sec.gov/api/xbrl/companyfacts/CIK{cik10}.json` (all facts) · `.../companyconcept/CIK{cik10}/us-gaap/{TAG}.json` (one series) | Free, **no key**. ≤10 req/s. **Mandatory User-Agent** `"Name email"` or you get 403. XBRL coverage is solid ~2010→. |
| Filing history, Form 4 (insiders) | EDGAR Submissions | `https://data.sec.gov/submissions/CIK{cik10}.json` | Same rate/UA rules. |
| CIK lookup; bulk | EDGAR | `https://www.sec.gov/files/company_tickers.json`; bulk `companyfacts.zip` | Cache; bulk beats per-company calls at scale. |
| Risk-free rate | FRED | series `DGS10` (free API key, or via OpenBB/`fredapi`) | §2.1 |
| ERP, industry betas, synthetic-rating spreads, marginal tax | Damodaran (NYU Stern) | `pages.stern.nyu.edu/~adamodar/New_Home_Page/datacurrent.html` (betas, wacc, ctryprem spreadsheets) | Updated annually, ~first two weeks of January. Cache locally; refresh yearly. |
| **Current price** (for market cap only) | **Default: Finnhub `/quote` (60 req/min free, reachable from anywhere incl. AR).** Fallbacks: yfinance (no key, unofficial — patch breakage) → Tiingo EOD (free, key) | provider SDK | Shares from EDGAR (`dei:EntityCommonStockSharesOutstanding`); market cap = EDGAR shares × price. Only unreliable feed; non-critical with fallbacks. |

> **Reliability note for the executor:** IEX Cloud shut down (Aug 2024); Alpha Vantage free tier is now 25 req/day (too tight for bulk, fine for ad-hoc); yfinance breaks periodically. None of this touches the spine, because the spine is EDGAR.

**Scope flag:** this data layer is US-listed equities (EDGAR/XBRL). Non-US names need a different fundamentals source and Damodaran's country-risk file for ERP — out of scope for v3; declare it on line one if the name isn't US-listed.

---

## 4. Phase 0 — Disqualify (gates)

**Question:** sound, investable, not obviously cooking the books? **Inputs:** EDGAR companyfacts + submissions; price feed; §2 config.

**Procedure (mechanical):**
1. **Circle-of-competence stub:** extract 3 largest revenue lines (segment data) and 3 largest cost lines; one sentence each. If unextractable, that's a finding.
2. **Investability:** avg daily $ volume vs. intended position; free float; share-class/voting from the proxy; related-party transactions (proxy).
3. **Altman Z — pick the variant (wrong variant = meaningless):**
   - Public manufacturer: `Z = 1.2·(WC/TA) + 1.4·(RE/TA) + 3.3·(EBIT/TA) + 0.6·(MV equity/TL) + 1.0·(Sales/TA)` → **>2.99 safe / 1.81–2.99 grey / <1.81 distress**.
   - Non-manufacturer / service / emerging (Z″): `Z″ = 6.56·X1 + 3.26·X2 + 6.72·X3 + 1.05·X4` (X4 = **book** equity/TL; drop Sales/TA) → **>2.6 / 1.1–2.6 / <1.1** (emerging: +3.25). Asset-light/financials: NOTE only.
4. **Beneish M:** `M = −4.84 + 0.92·DSRI + 0.528·GMI + 0.404·AQI + 0.892·SGI + 0.115·DEPI − 0.172·SGAI + 4.679·TATA − 0.327·LVGI` → **M > −1.78 = elevated manipulation likelihood**.
5. **Smoke checks:** restatement in 3 yrs (Y/N); auditor change (Y/N); widening net-income-vs-CFO gap (Y/N); DSO & inventory-days trend vs. revenue.

**Judgment (draft + flag):** is each lit signal a value-trap or an explainable quirk? `M > −1.78` flags **aggressive accounting, not proven fraud** (it lights up on legitimate-but-aggressive names) → route to forensic, don't auto-kill. → `gate_verdict ∈ {PASS, DIG, KILL}` with `needs_ratification` on any DIG/KILL.

**Severity:** KILL = stop now (fraud-for-cause, uninvestable, single-binary-event). DIG = proceed but it becomes a required handoff section. NOTE = record.

**Output → `Gate Card`:**
```json
{ "ticker": "", "cik": "", "screens": {
    "altman": {"variant":"", "z": 0.0, "zone":""},
    "beneish": {"m": 0.0, "flag": false},
    "smoke": {"restatement": false, "auditor_change": false, "ni_cfo_gap_widening": false}},
  "investability": {"adv_usd": 0, "float": 0, "share_class_risk": "", "related_party": ""},
  "verdict": "PASS|DIG|KILL", "dig_items": [], "kill_reason": null,
  "needs_ratification": true }
```
**Validation gate:** all three screens computed with variant/threshold recorded; every screen input sourced; verdict ∈ enum. KILL ⇒ pipeline emits the one-paragraph kill memo and **halts**.

---

## 5. Phase 0.5 — Build the financial spine *(was the P1↔P2 ordering bug)*

ROIC is needed by Phase 1's moat panel but is computed from Phase 2 data — so compute the spine **first**. **Inputs:** companyfacts; §2.1–2.4. **Procedure:** pull 5–10 yr of income/balance/cash; apply tag fallbacks; compute WACC (§2.1), NOPAT, invested capital (both goodwill treatments), **ROIC and ROIC−WACC spread per year**, and the spread decomposition (margin vs. turnover). **Output → `Spine` (the ROIC/WACC time series + decomposition)**, consumed by P1 and P2. **Gate:** ≥5 yrs present; WACC inputs all sourced from §2.1; ROIC computed both goodwill ways.

---

## 6. Phase 1 — Business & unit economics

**Question:** good business? **Horizon:** long-hold logic. **Inputs:** filings + `Spine`.

**Procedure (mechanical):** revenue decomposition (price × volume × mix from segments); fixed/variable cost split + contribution margin; unit economics (per unit/customer/cohort where disclosed); industry map (named competitors/suppliers/buyers, market size); pull the `Spine` moat-evidence panel (10-yr ROIC−WACC + source decomposition).

**Capital-allocation track *(restored from the original; was missing in v2)*:** assemble management's actual record — buyback prices vs. estimated value (were repurchases counter- or pro-cyclical?), M&A count and post-deal returns/impairments, dividend trajectory, and **incremental ROIC** on reinvested capital (`Δ NOPAT / Δ invested capital` over rolling windows). This is Buffett's central management test and a core part of the case.

**Judgment (draft + flag):** **does a moat exist and persist?** A positive ROIC−WACC spread is *backward-looking evidence consistent with* a moat — necessary, not sufficient. Weigh forward indicators (pricing power under stress, retention/switching costs, share stability) **and the reinvestment runway** (a high return that can't absorb new capital compounds less than a moderate one that can). Also draft: is capital allocation value-accretive? → `moat ∈ {None, Narrow, Wide}` + reason; `capital_allocation ∈ {Good, Mixed, Poor}` + evidence.

**Output → `Business Brief`:**
```json
{ "how_it_makes_money": "", "unit_economics": "",
  "industry": {"competitors": [], "structure": "", "tam": ""},
  "moat": {"verdict":"None|Narrow|Wide", "evidence":"", "reinvestment_runway":"", "needs_ratification": true},
  "capital_allocation": {"verdict":"Good|Mixed|Poor", "buybacks":"", "ma_returns":"", "incremental_roic":0.0, "needs_ratification": true} }
```
**Gate:** drivers + costs populated from segments; moat verdict cites the `Spine`; capital-allocation has ≥3 quantified data points.

**▶ GO/NO-GO GATE (the one early human/rule check):** in-universe? Gate Card clean? business model coherent and actually understood? If no → halt/escalate before spending P3–P7.

---

## 7. Phase 2 — Normalized financial panel

**Question:** facts. **Inputs:** filings + `Spine`.

**Procedure (mechanical):** assemble the panel, every cell with provenance — revenue growth + durability; gross/operating margin (level + trend); **ROIC and ROIC−WACC** (from `Spine`); FCF (`NOPAT − Δ invested capital`) + FCF conversion (FCF/NI); net debt/EBITDA + maturity wall (debt notes); **diluted share count trend incl. SBC**; working-capital intensity. Maintain the **`Normalization Log`** per §2.3.

**Judgment (draft + flag):** which "one-offs" are recurring-in-disguise (§2.3 rule); is SBC treated as real expense? → per-line `recurring?` flags for senior ratification.

**Output → `Financial Panel` + `Normalization Log`** (facts only; no forecast leaks here).
**Gate:** 8 metrics × ≥5 yrs; every cell sourced; normalization log complete with `recurring?` on each line; computed totals tie to filing totals within tolerance.

---

## 8. Phase 3 — What's priced in (reverse-DCF)

**Question:** mispriced vs. expectations? **Inputs:** `Financial Panel`, current price × EDGAR shares = market cap/EV, WACC. **Procedure:** run the DCF engine in reverse — goal-seek the revenue growth / margin / duration / terminal-ROIC the **current price** implies; repeat across a low/high WACC band.

**Judgment (draft + flag):** the discount rate (and the honest caveat that **reverse-DCF relocates subjectivity into WACC** — a tunable rate moves "what's priced in" almost anywhere, so the band matters more than the point); **whether reverse-DCF even fits** — for NAV/asset plays, financials, and pure optionality (pre-revenue biotech, exploration), use NAV / SOTP / rNPV instead and say so.

**Output → `Expectations Line`:** *"At today's price the market is paying for ~X% growth for ~N yrs at ~Y% margin / terminal ROIC ~Z%"* + the WACC band + the frame used and why it fits.
**Gate:** implied expectations solved at both WACC bounds; frame justified against asset type.

---

## 9. Phase 4 — Forward scenarios (range, not point)

**Question:** what will be revealed vs. priced in? **Inputs:** `Business Brief`, `Financial Panel`, base-rate table. **Procedure:** build **bear/base/bull**, each assumption traceable to a driver; **anchor to base rates** (sales growth has low year-to-year persistence → start from the distribution, deviate only on specific evidence):

| A forecast claiming… | US public base rate (Mauboussin/Credit Suisse, samples to ~1950, incl. dead cos) |
|---|---|
| 3-yr sales CAGR 0–5% | where *most* companies land |
| ≥30% sales CAGR sustained 5 yrs | ~1% of companies |
| ≥30% sales CAGR sustained 10 yrs | ~0.6% |
| ≥45% sales CAGR sustained 10 yrs | ≈0% |
| ≥15% net-income growth repeated two decades | of 200 top-earners in 1990, 14 did it once to 2000; **none** repeated to 2010 |
| still alive to be measured | 76% @5y · 59% @10y · 38% @20y |

If the base case sits in a ~1% bucket, it needs an extraordinary, specifically-evidenced reason or it's cut. Then: **sensitivity table** on the 2–3 swing variables; **valuation by the method that fits the asset** (stable cash → DCF + multiple cross-check; cyclical → normalized mid-cycle; optionality → SOTP/rNPV as an explicit *wide range*).

**Judgment (draft + flag):** the **scenario probabilities are subjective, senior-owned weights** — the executor supplies scenarios + base rates; the senior assigns and signs the probabilities (this is the fake-precision trap, fixed by owning the subjectivity instead of emitting a false point estimate).

**Output → `Valuation Range`:** bear/base/bull values, each with swing assumptions shown and a (draft) probability `needs_ratification`.
**Gate:** three scenarios, each assumption tied to a driver and checked against the base-rate table; method matches asset type; sensitivity table present.

---

## 10. Phase 5 — Edge, catalysts, and cruxes

**Question:** do we have a differentiated view, and why now? **Inputs:** `Expectations Line`, `Valuation Range`.

**Procedure — with a forcing function against motivated reasoning** (a human/agent that has sunk effort will manufacture a bull story for anything):
1. **Steelman the efficient price first** — the strongest case that the stock is *correctly* valued and there is no trade.
2. **Name the counterparty** — who holds the opposite view right now, and why is that rational? "No one / they're dumb" is a failed answer → stop.
3. If a thesis survives, state the **structural reason for the mispricing** (time-horizon, forced/index selling, complexity, misread unit economics — "it's just cheap" is not a reason).
4. **Distill the cruxes** *(this is where the handoff's "3 things that must be true" are produced)*: from `Expectations Line` vs. `Valuation Range`, extract the **3 deltas that decide the outcome**, each tied to a measurable metric and threshold.
5. **Catalysts** with rough timing.

**Judgment (draft + flag):** is the variant view genuinely differentiated or a rationalization that didn't survive the steelman? Is the catalyst path real or hope?

**Output → `Edge Statement`:** steelman; named counterparty; variant thesis (2–3 sentences) **or** "fairly priced — pass"; the **3 cruxes** (metric + threshold each); catalysts + timing.
**Gate:** steelman present; counterparty named; exactly 3 falsifiable cruxes emitted.

---

## 11. Phase 6 — Risk, downside, kill-thesis

**Question:** what's the downside, what proves us wrong? **Inputs:** `Valuation Range`, full package.

**Procedure (mechanical + structured):**
1. **Pre-mortem:** it's 2 yrs out and we lost money — the most likely story for why.
2. **Bear case as a short-seller would write it.**
3. **Risk register — two buckets** *(the matrix fix)*: (a) **modellable** risks ranked impact × likelihood; (b) **Knightian/tail** risks whose probability genuinely can't be estimated (regulatory regime change, fraud, key-person, geopolitical) — **listed separately**, because an impact×likelihood matrix silently discounts exactly the risks that most often kill theses.
4. **Bear-case value** — the valuation if the bear scenario plays out. *This is the real margin of safety:* not the discount to fair value, but **what we own at the bottom and whether we can live with it** (Graham's MoS only protects when value persists — size the loss before the gain).
5. **Kill-thesis line:** the specific metric + threshold that ends the thesis ("gross margin < X% for 2 consecutive quarters → exit").

**Output → `Risk & Kill Sheet`:** pre-mortem; two-bucket register; bear-case value; kill metric.
**Gate:** both risk buckets populated; bear-case value computed; kill metric is specific and falsifiable.

---

## 12. Phase 7 — Position sizing inputs *(senior-owned; executor supplies inputs only)*

**The executor does not propose a size.** It supplies: upside/downside ratio (base/bull vs. bear-case value from P4/P6); liquidity (days-to-build, days-to-exit at intended size, from P0); and book overlap (existing exposures this duplicates — same sector/factor/catalyst). **Output:** `sizing_inputs` appended to the handoff. **Size itself is the senior's stamp**, set against conviction (§14), the survivable-downside test, liquidity, and concentration.

---

## 13. The Handoff (output contract)

One page + appendix, identical shape every time, assembled from the phase artifacts above.
```json
{ "header": {"ticker":"", "price":0, "as_of":"", "lean":"Buy|Watch|Pass",
             "conviction":"Low|Med|High", "horizon":"hold-for-quality|catalyst",
             "review_by":""},
  "thesis_3_sentences": "",
  "whats_priced_in": "",                      // P3 Expectations Line
  "valuation_range": {"bear":0,"base":0,"bull":0,"probabilities":{}},  // P4 (senior-signed)
  "cruxes": [ {"claim":"","metric":"","threshold":""} ],               // exactly 3, from P5
  "risk": {"modellable_top3":[], "tail_risks":[], "bear_case_value":0, "kill_metric":""}, // P6
  "edge": {"steelman":"", "counterparty":"", "variant_view":""},       // P5
  "sizing_inputs": {"up_down_ratio":0, "days_in":0, "days_out":0, "book_overlap":""},     // P7
  "confidence_and_gaps": {"least_sure_about":"", "couldnt_verify":[], "would_raise_conviction":""}, // MANDATORY
  "revisit_if": ["price past bear/bull", "a crux metric prints", "catalyst resolves", "kill metric breached"],
  "data_room": {/* every key number {value,tag,form,period,accession} + Gate Card + Panel + Normalization Log */} }
```
**Rules:** lead with lean + conviction; flag every unsourced number and load-bearing assumption; **`confidence_and_gaps` is mandatory — a handoff with no gaps section is defective and is returned**; if P0 = KILL, the handoff is the one-paragraph kill memo and nothing else.

---

## 14. Senior Review Checklist (the single consolidated pass)

Every `needs_ratification` point, aggregated so review is one structured pass — not a hunt through seven phases. Ratify or overturn each:
1. **Gate verdict** — agree with PASS/DIG/KILL and the read of any lit screen?
2. **Normalization** — any "non-recurring" add-back that actually recurs? SBC treated as real?
3. **Moat** — verdict and reinvestment-runway view; is the spread durable and forward-supported?
4. **Capital allocation** — buyback discipline, M&A returns, incremental ROIC?
5. **Discount rate** — WACC inputs and the implied-expectations band?
6. **Scenario probabilities** — assign/sign the weights (these are yours, not the model's).
7. **Edge** — did the variant view survive the steelman; is the counterparty real?
8. **Risk** — tail bucket complete; is the bear-case downside survivable at contemplated size?
9. **Conviction** — does the §15 score match the evidence?
10. **Size** — your stamp, given 1–9.

---

## 15. Conviction rubric (so the calibration log measures signal, not noise)

Score each 0–2; conviction = banding of the total (0–10). Without this, "High conviction" is undefined and the log is noise.
| Factor | 0 | 1 | 2 |
|---|---|---|---|
| Margin of safety (base vs. bear-case value) | thin | moderate | large |
| Crux strength | weak/speculative | mixed | strong, evidenced |
| Base-rate support for the forecast | in a ~1% bucket | middling | well inside the distribution |
| Variant view | not differentiated | plausible | clearly differentiated + counterparty understood |
| Data completeness | major gaps | minor gaps | fully sourced |
**Banding:** 0–3 Low · 4–7 Med · 8–10 High. (Senior may override, but records the override — that, too, feeds calibration.)

---

## 16. Calibration log (the feedback loop — what makes delegation reliable over time)

Append-only; the loop a runbook alone can't provide. **At the call:** `{date, ticker, lean, conviction, conviction_score, base_value, bear_value, review_by, kill_metric}`. **At each review date:** `{what_happened, cruxes_held: [...], cruxes_broke: [...], right_for_the_reasons: bool}`.

The senior reads off it over time: **hit rate by conviction band** (a "High" that resolves ~50/50 means discount this executor's next "High"); **directional bias** (persistently too bullish / downside underestimated); **where the process leaks** (misses clustering in P1 = didn't understand the business, P4 = forecasts ran hot vs. base rates, P6 = tail risk under-weighted → tighten that phase). Conviction becomes a *measured* quantity, not a self-report. Concurrency note: it's append-only, last-write-wins; negligible contention even with many executors.

---

## 17. Build order (highest leverage first)

1. **EDGAR client** (companyfacts/concept/submissions, CIK lookup, tag fallbacks, provenance, rate-limit + UA) — unlocks Phases 0, 0.5, 2.
2. **Conventions module** (§2 as config) + **WACC/ROIC engine** (FRED + Damodaran loaders).
3. **DCF engine** (one engine, forward + reverse) — Phases 3 & 4.
4. **Screen functions** (Altman variants, Beneish) — Phase 0.
5. **Artifact schemas + validation gates** (§4–13) — wire the phase contracts.
6. **Review checklist + conviction + calibration** (§14–16).
7. **Worked example** on a real ticker — *fast-follow; see note below.*

---

### Resolved defaults (your location barely matters here — see note)
- **Tax rate → 25%** (US-listed: 21% federal + ~4% state). *Driven by the company's domicile, not the analyst's.* Override per-country via Damodaran (Argentina ≈ 35%) only if you point this at non-US names.
- **Excess cash → cash above 2% of TTM revenue** is non-operating. Toggle: treat *all* cash as non-operating (Damodaran convention) for a cleaner operating-ROIC — flip in §2.2.
- **Price feed → Finnhub free** (60 req/min, globally reachable); yfinance no-key fallback.

> **Analyst-location note (Argentina):** the conventions follow the *company*, not you. Valuing a US-listed company is a USD valuation using a US/mature-market ERP (4.23%) and the company's US tax rate — your being in Argentina never enters. It would matter only if you analyze Argentine/LatAm names directly: then swap in that country's marginal tax rate, add Damodaran's country-risk premium to the ERP, and pick the valuation currency. That's a documented v4 extension, not a default.

### Fast-follow
- **Worked example** on a real ticker — the single highest-ROI learning aid (the executor learns the house standard from a filled exemplar faster than from rules). Best pulled live from EDGAR; flagged as next deliverable rather than faked here.
