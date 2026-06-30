# M1 Walking Skeleton — Requirements

## Functional Requirements

1. `analyze("AAPL")` must run through a complete M1 path from data fetch or fixture load to filed handoff.
2. The EDGAR adapter must resolve `AAPL` to CIK `0000320193`.
3. The EDGAR adapter must extract at least five annual 10-K periods for:
   - EBIT
   - revenue
   - cash
   - long-term debt, current debt, and short-term borrowings when available
   - equity
   - goodwill
   - shares outstanding
   - interest expense when available
4. Every extracted fact must be wrapped in a `Number` with a complete `Provenance`.
5. Normalization must return a typed structure and an empty M1 normalization log.
6. Cost of capital must provide:
   - risk-free rate from FRED or configured fallback
   - ERP from config
   - unlevered beta from config
   - credit spread from config
   - marginal tax rate from config
7. Price must come from an injected `PriceFeed` and degrade gracefully if unavailable.
8. The Spine computation must emit, per fiscal year:
   - NOPAT
   - invested capital including goodwill
   - invested capital excluding goodwill
   - ROIC including goodwill
   - ROIC excluding goodwill
   - WACC
   - ROIC-WACC spread
   - NOPAT margin
   - capital turnover
9. Computed numbers must use `kind="estimate"` and include a derivation string that points to the source inputs.
10. The bare handoff must include the real Spine and honest skeleton placeholders for fields deferred to later milestones.
11. The storage layer must write and reload `spine.json` and `handoff.json`.
12. The M1 audit gate must block filing when provenance, derivation, sanity, or serialization requirements fail.
13. Each M1 skill must be a folder bundle with a completed `SKILL.md` based on `specs/SKILL-template.md`.

## Non-Functional Requirements

- The implementation must stay portable and standalone.
- Runtime state must stay under `/data`.
- Skill code must live under `/skills`.
- Supporting reusable knowledge must live under `/knowledge`.
- The dependency tree must stay small and consistent with `specs/tech-stack.md`.
- CI tests must use frozen fixtures rather than live EDGAR, live price feeds, or live FRED.
- Accountants must fail closed and never impute missing concepts.
- Analyst judgment and Senior approval are out of scope for M1.
- M1 must reuse the M0 scaffold contracts in `specs/2026-06-29-scaffold/`.

## Content And Data Requirements

### XBRL Tag Fallbacks

Use these tag fallbacks in order:

| Concept | Tags |
| --- | --- |
| EBIT | `us-gaap:OperatingIncomeLoss` |
| Revenue | `RevenueFromContractWithCustomerExcludingAssessedTax`, `Revenues`, `SalesRevenueNet` |
| Cash | `CashAndCashEquivalentsAtCarryingValue` |
| Long-term debt, noncurrent | `LongTermDebtNoncurrent`, `LongTermDebt` |
| Long-term debt, current | `LongTermDebtCurrent` |
| Short-term borrowings | `ShortTermBorrowings`, `DebtCurrent` |
| Equity | `StockholdersEquity`, `StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest` |
| Goodwill | `Goodwill` |
| Shares outstanding | `dei:EntityCommonStockSharesOutstanding` |
| Interest expense | `us-gaap:InterestExpense` |

### Required Formulas

```text
NOPAT = EBIT * (1 - tax_rate)
ExcessCash = max(0, Cash - excess_cash_pct * Revenue)
IC_incl_gw = TotalDebt + Equity - ExcessCash
IC_ex_gw = IC_incl_gw - Goodwill
ROIC_incl = NOPAT / IC_incl_gw
ROIC_ex = NOPAT / IC_ex_gw
margin = NOPAT / Revenue
turnover = Revenue / IC_incl_gw
DE = TotalDebt / MarketCap
betaL = beta_unlevered * (1 + (1 - tax_rate) * DE)
Ke = Rf + betaL * ERP
Kd = Rf + credit_spread
Kd_after_tax = Kd * (1 - tax_rate)
WACC = (E / (E + D)) * Ke + (D / (E + D)) * Kd_after_tax
spread = ROIC_incl - WACC
```

If price is unavailable, use book equity instead of market cap for WACC weights and flag the substitution.

## Acceptance Criteria

- `analyze("AAPL")` returns a filed M1 handoff, not only an in-memory result.
- The happy path emits at least five fiscal years of Spine rows.
- Every fact can be traced to a specific 10-K accession.
- Every estimate includes a derivation.
- `margin * turnover == ROIC_incl` within tolerance for all years.
- AAPL ROIC is positive, invested capital is positive, and WACC is between 0 and 30%.
- Stripping provenance from any required number causes audit rejection.
- Forcing a tag or value that creates out-of-bounds ROIC causes audit rejection.
- Stubbing `PriceFeed` to fail still completes the run with `price_unavailable` flagged.
