# Hermes Finance Skills

> A portable, auditable fundamental-analysis pipeline for turning a US-listed ticker into a decision-ready research handoff.

Hermes Finance Skills is a portfolio project about a hard problem in AI-assisted finance: making it obvious which parts of an investment workflow are sourced and reproducible, which are judgment calls, and who is accountable for the final decision.

The pack combines deterministic financial-modeling skills with evidence-backed research drafts. It produces either a signed handoff or a concise kill memo, persists the supporting artifacts locally, and records outcomes for later calibration. It is designed to run standalone or behind a host such as Hermes without hard-coupling the analysis logic to that host.

> **Not investment advice.** This project is decision support for a designated reviewer. It does not execute trades or make position-sizing decisions.

## Why this project is interesting

Most finance demos stop at “an LLM wrote a stock pitch.” This one focuses on the controls that make a workflow reviewable:

- **Provenance is mandatory.** Every number crossing a skill boundary is a typed `Number` with source metadata. Derived numbers also carry a walkable derivation.
- **Computation and judgment have different permissions.** Deterministic *Accountants* calculate and fail closed. LLM-facing *Analysts* may draft, flag, and attach evidence, but cannot silently assert a decision.
- **A Senior signs judgment.** Gate decisions, ratification, and final lean are explicit resolver touchpoints with identity checks.
- **The method follows the asset.** The router selects DCF, rNPV, NAV, SOTP, or another route rather than forcing every company through a generic DCF.
- **The output can be audited later.** JSON run artifacts are inspectable, calibration records are append-only in SQLite, and a deterministic renderer can regenerate a readable Markdown report without calling an LLM.

## What a run does

```text
Ticker
  │
  ├─ A: Source & compute ───────── EDGAR facts · market price · cost of capital
  │
  ├─ B: Deterministic accounting ─ normalization · ROIC/WACC spine · screens
  │                                 method routing · DCF / base-rate anchors
  │
  ├─ C: Evidence-backed research ─ business · moat · capital allocation
  │                                 scenarios · edge/cruxes · risk
  │
  ├─ Senior controls ───────────── early GO/NO-GO · consolidated ratification
  │                                 final-lean sign-off
  │
  └─ D: Synthesis & learning ───── conviction · final handoff · report
                                    calibration call · route/escalation health
```

A path that fails a gate stops with a `KillMemo`; it cannot continue into a full handoff. A completed path includes a valuation range, what the price implies, exactly three falsifiable cruxes, risks, revisit triggers, confidence gaps, and the source trail behind the displayed facts.

## Quick start

Requires Python 3.12+ and [uv](https://docs.astral.sh/uv/). The repository currently ships reproducible fixtures for `AAPL`, `CRM`, `MRNA`, and `UBER`, so the default demo does not require API credentials.

```bash
git clone https://github.com/meschinidino/hermes-finance-skills.git
cd hermes-finance-skills
uv sync

# Run the complete fixture-backed test suite.
UV_CACHE_DIR=.uv-cache uv run --no-sync pytest

# Produce an offline, deterministic analysis handoff.
UV_CACHE_DIR=.uv-cache uv run --no-sync python -m resolver AAPL
```

The resolver writes runtime state below `data/`, which is intentionally ignored by Git:

```text
data/
├── runs/<TICKER>/<YYYY-MM-DD>/  # auditable JSON artifacts and generated reports
├── cache/                       # regenerable source-cache data
└── pack.db                      # append-only calibration and health records
```

To create a reader-friendly report from a completed run:

```bash
UV_CACHE_DIR=.uv-cache uv run --no-sync python -m resolver \
  render-report --run-dir data/runs/AAPL/<YYYY-MM-DD>
```

## Portfolio-grade implementation details

### Typed, fail-closed artifact contracts

The core contracts use Pydantic v2. A fact without filing provenance is invalid. A non-fact number without a derivation is invalid. Incompatible units, incomplete ratification, missing tail risks, non-monotonic scenario structure, and a full handoff on a kill path are all rejected before downstream use.

This is the project’s central design decision: auditability is enforced in code, not left as a documentation convention.

### A real routing problem, not one valuation formula

The method router classifies a company before valuation. The current fixture set demonstrates both DCF and route-deferred optionality paths:

| Ticker | Demonstrated route | Calibration detail |
| --- | --- | --- |
| AAPL | DCF | Global house conventions |
| CRM | DCF | Damodaran-backed SaaS scenario block |
| MRNA | rNPV / route-deferred valuation | Optionality is not fabricated as a plain DCF |
| UBER | DCF | Realized-financials anchor with coherence guardrails |

Sector provisioning is deliberately deterministic. It combines a committed source snapshot with a separate house-judgment bracket layer, then verifies that the generated configuration has not drifted:

```bash
UV_CACHE_DIR=.uv-cache uv run --no-sync python -m resolver provision-sectors check
```

The provisioning check also catches economically incoherent scenario inputs before they reach a DCF, including a positive and ordered free-cash-flow proxy across bear, base, and bull cases.

### Human/agent boundaries

The pack is portable because its host-facing concerns are injected protocols:

| Interface | Standalone behavior | Host can replace it with |
| --- | --- | --- |
| `Senior` | Deterministic offline reviewer for fixtures | Human or approved model-backed reviewer |
| `Storage` | Local JSON files plus SQLite | Another durable storage implementation |
| `LLM` | Explicitly injected | A host-provided model client |
| `PriceFeed` | Default adapter path | A host-provided price service |

The CLI can select an Azure Foundry Senior adapter with `--senior azure-foundry`. It requires `AZURE_FOUNDRY_ENDPOINT`, `AZURE_FOUNDRY_API_KEY`, and `SENIOR_DEPLOYMENT_NAME`, and rejects incomplete or contradictory identity metadata instead of falling back silently.

### Calibration closes the loop

Every completed handoff can become a later review record. The calibration layer tracks hit rate by conviction band, directional bias, leak-by-phase, route correctness, and escalation correctness. This separates “the call worked” from “the process worked for the right reasons.”

```bash
# Read local calibration analytics.
UV_CACHE_DIR=.uv-cache uv run --no-sync python -m resolver calibration-report

# Record a completed review from a local JSON payload.
UV_CACHE_DIR=.uv-cache uv run --no-sync python -m resolver calibration-review \
  --json-file path/to/review.json
```

## Repository map

```text
resolver.py       # sole orchestrator and CLI entry point
skills/
  data/           # EDGAR, price, and cost-of-capital accountants
  valuation/      # normalize, spine, screens, routing, DCF, base rates
  research/       # evidence-backed analyst artifacts
  synthesis/      # conviction, final handoff, report rendering, calibration
  provisioning/   # deterministic sector-base-rate configuration generation
config/           # versioned house conventions and pinned source snapshots
knowledge/        # analyst runbooks and reusable domain reference
specs/            # mission, contracts, roadmap, and milestone validation
tests/            # golden fixtures and route-level verification
```

Each skill is a self-contained bundle with its contract, implementation, resolver entry, and tests. Analyst bundles also include their prompt and evaluation surfaces; accountant bundles intentionally do not.

## Current scope and next steps

The implemented path is fixture-backed and deterministic for its four demonstration tickers. That is intentional: it makes the core audit, routing, synthesis, and calibration behavior reproducible before live-source and host integration are expanded.

The next planned work is M7 hardening and extensions: a polished worked example, deployment packaging, and eventually non-US analysis support. See [specs/roadmap.md](specs/roadmap.md) for the milestone history and [TODOS.md](TODOS.md) for intentionally deferred work.

## Design constraints

This project intentionally avoids servers, queues, orchestration frameworks, vector databases, and direct trade execution. The resolver is the orchestrator; local files and SQLite are sufficient for a one-name-deep research workflow. Those constraints keep the repository portable, inspectable, and easy to run in a standalone environment.

For the full product rationale, see [specs/mission.md](specs/mission.md), [specs/filing-rules.md](specs/filing-rules.md), and [resolver.md](resolver.md).
