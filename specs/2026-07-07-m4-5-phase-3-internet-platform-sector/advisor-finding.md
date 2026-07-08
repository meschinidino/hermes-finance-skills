# Finding for the finance advisor — UBER sector anchor

**Status: OPEN QUESTION. Do not implement against any answer yet.** This memo brings a raw
finding, not a proposed fix. We paused M4.5 Phase 3 implementation to get your read first.

## What we were trying to do

UBER's rendered report carries a `price_at_or_below_bear` flag: the model's bear-case DCF
value sits *above* the current price, so the model can't produce a pessimistic case below
where the stock trades. We traced it to the global DCF default assuming a **24% NOPAT margin
in every bear case**, which is 4-5x too high for Uber's thin marketplace margins. The plan was
to give Uber a sector calibration anchored to Damodaran's `Software (Internet)` industry
(closest business-model match), so its base rates come from internet-platform economics rather
than the global default.

## The finding

Before writing code, we plugged the raw Damodaran `Software (Internet)` medians into the DCF
for Uber and measured what came out. It does not just fail to help — **it produces negative,
non-monotonic equity values and halts the analysis:**

| Scenario | Per-share value | Revenue growth | NOPAT margin |
|----------|-----------------|----------------|--------------|
| Baseline (current global default) bear | **+80.30** | 0.02 | 0.24 |
| Baseline base / bull | +108.78 / +141.50 | 0.04 / 0.06 | 0.28 / 0.31 |
| — current price — | **74.43** | | |
| Damodaran Software (Internet) bear | **-26.33** | 0.08 | 0.02 |
| Damodaran Software (Internet) base | **-49.18** | 0.177 | 0.046 |
| Damodaran Software (Internet) bull | **+7.62** | 0.25 | 0.12 |

The base case is worth *less* than the bear case (-49.18 vs -26.33), which is non-monotonic, so
the pipeline stops with `scenario value ordering failed: bear must be less than base`.

Damodaran source figures used: `Software (Internet)`, 29 firms, 17.71% forward revenue growth,
4.59% after-tax operating margin, 1.35 sales-to-invested-capital (NYU Stern, data as of
January 2026).

## Why it happens (and why it is not a modelling bug)

To grow revenue 17.7% a year at a sales-to-capital of 1.35, the model reinvests about
`0.177 / 1.35 ≈ 13%` of revenue into capital every year. But NOPAT is only 4.6% of revenue.
So free cash flow is **negative throughout the growth phase** — the company spends 13 cents to
grow for every 4.6 cents it earns. Growth at a return below the cost of capital destroys value,
so the higher-growth base case is worth less than the lower-growth bear case. The DCF is
behaving correctly; the inputs are the problem.

**The root issue is methodological.** Those two numbers are independent cross-sectional
medians: the median internet-company growth (17.7%) and the median internet-company margin
(4.6%). They come from different firms. No single company grows 17.7% while earning a 4.6%
margin — the high-growth internet names and the low-margin internet names are different
populations. A single-company DCF needs an internally-consistent growth/margin/reinvestment
triple, not three independent industry medians stapled together. (This is the same thin-sample
incoherence that made us set `Software (Internet)` aside as an anchor back in Phase 2.)

## The live question for you

We do not want to pick the fix — it is a valuation judgment about Uber, not an engineering
call. The finding forks into two very different stories:

1. **Bespoke, internally-consistent pairing.** Uber needs its *own* forward growth and margin,
   internally consistent with each other (their realized/guided numbers, not industry medians)
   — e.g. a decelerating-growth, margin-expanding path. If so, "anchor to a Damodaran industry
   median" is the wrong tool for Uber and we should calibrate Uber directly.

2. **Margin-inflection / optionality, not steady-state DCF.** The negative values may be the
   model telling us Uber's real story is a margin inflection (thin today, expanding tomorrow)
   or platform optionality that a plain steady-state DCF cannot represent — in which case Uber
   should route to a different valuation method, not a DCF sector at all (planning option C).

Which of these matches how you actually think about Uber? React to the raw numbers first; the
implementation follows your read, not the other way around.

## What is on hold

Nothing has been built. Config and run artifacts are reverted to baseline. The Phase 3 spec
(`plan.md`, `requirements.md`, `validation.md`) is written and eng-reviewed but **blocked**
pending this conversation. We will not implement the bespoke-anchor, method-reroute, or
global-margin paths until you weigh in.
