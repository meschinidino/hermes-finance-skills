# tech-stack.md — Stack Decisions

**Optimize for: speed of build + lightweight footprint + portability.** Small dependency tree, embedded everything, the resolver is the only orchestrator. Opinionated defaults below; each is a default, not a religion.

---

## Repository layout
Constitution (`specs/`) is read by the coding agent at build time; the repository itself is the portable unit the analyst runs with Hermes or any agent. The resolver sits at the project root — *above* skills, not inside it.

```
project-root/
├── specs/                     # constitution — the coding agent reads these
│   ├── mission.md
│   ├── roadmap.md
│   ├── tech-stack.md
│   └── filing-rules.md        # (to come) provenance + artifact schemas
├── resolver.py                 # conductor + entry point; NOT a skill
├── skills/                     # self-contained skill bundles, by department
│   ├── data/
│   ├── valuation/
│   ├── research/
│   └── synthesis/
├── knowledge/                  # supporting analyst references, runbooks, and reusable domain knowledge
├── config/
│   └── conventions.yaml        # house conventions (§2) — policy, versioned, refresh-dated
└── data/                       # gitignored runtime state
    ├── pack.db                 # SQLite calibration log
    ├── cache/                  # EDGAR / Damodaran / FRED JSON cache
    └── runs/                   # per-run artifacts: runs/{ticker}/{as_of}/
```
> The unit of portability is the **repo**, not `skills/` alone — skills need the root resolver, `config/`, `knowledge/`, and runtime storage conventions.

Each skill is a folder bundle, not a flat implementation file:

```text
skills/<dept>/<skill>/
├── SKILL.md             # the contract + per-skill definition-of-done
├── <skill>.py           # implementation
├── test_<skill>.py      # unit tests (frozen fixture)        — Accountants
├── test_integration.py  # live-endpoint smoke (if external)  — optional per skill
├── prompt.md            # rubric, built FROM /knowledge/runbook.md  — Analysts only
├── eval/                # rubric conformance + red-team + ratification — Analysts only
│   ├── cases.jsonl
│   └── eval_<skill>.py
└── resolver.entry       # the routing trigger registered with the resolver
```

Bundle contents are determined by role type:
- **Accountant** (`no_llm: true`): `SKILL.md`, `<skill>.py`, unit tests, optional live integration test, and `resolver.entry`. No `prompt.md`; no `eval/`.
- **Analyst** (`no_llm: false`): `SKILL.md`, thin `<skill>.py` that assembles context, calls the injected LLM, and shapes a `Ratifiable`; `prompt.md` built from the relevant `/knowledge/runbook.md` section; `eval/`; and `resolver.entry`. Unit tests stay minimal because `eval/` is the validation surface.

---

## Language & runtime
- **Python 3.12+** — chosen for **correctness and iteration speed, not runtime speed.** A run is dominated by network I/O (EDGAR/FRED/price) and LLM latency; the real compute is a few hundred float ops, so Go's 10–50× compute edge applies to ~0.1% of wall-clock and buys nothing here. What *does* matter: XBRL is a swamp (inconsistent tags, misaligned fiscal years, restatements) and Python's libraries have already absorbed those edge cases — hand-rolling them risks a **wrong number in a financial model, which the constitution forbids**. Plus the typed-schema/numerics ecosystem and M1 velocity. **Decision rule:** one-name-deep analysis → Python; if this ever becomes a thousand-name-wide concurrent screener, that's the trigger to reconsider Go.
- **`uv`** for env + packaging (fast, lockfile, reproducible). Single `pyproject.toml`; ship the pack as an installable module with `analyze()` as the entry point.
- **`asyncio`** for the resolver's parallel dispatch (P0 screens; Spine ∥ business; P3∥P4; P5∥P6). No external task framework.

## Core dependencies (keep this list short)
| Concern | Choice | Why |
|---|---|---|
| HTTP | **httpx** | async-capable; EDGAR/FRED/price calls |
| Schemas + validation | **pydantic v2** | the typed artifact contracts (Gate Card → Handoff) and `Config`; "schema or rejected" is enforced here; Rust-backed, fast |
| Numerics (DCF goal-seek) | **stdlib bisection/Newton** (scipy optional) | reverse-DCF root-find is ~15 lines; avoid a heavy dep for trivial work |
| Tabular | **plain dicts/lists** core; **pandas** only for calibration analytics | one company × 10 yrs is tiny — no dataframe needed on the hot path |
| LLM (Analysts) | **injected client** (Protocol) | pack must not hardcode a provider; Hermes supplies its model (e.g. GPT-5.4) |
| Tests | **pytest** + golden fixtures (Accountants); rubric/format + recorded ratification (Analysts) | the two test regimes from the constitution |

> Everything else is stdlib. If a dependency isn't on this list, justify it against "lightweight" before adding.

## Storage (the DB question, answered)
**One embedded SQLite file + flat JSON. No server.** Three kinds of state, three homes:
- **Cache** (EDGAR statements, Damodaran/FRED) → **JSON files**, keyed, with refresh metadata. Regenerable; not in the DB.
- **Run artifacts** (Gate Card → Handoff, per run) → **JSON files** in `runs/{ticker}/{as_of}/`. Inspectable and agent-debuggable.
- **Calibration log** → **SQLite** (`pack.db`, stdlib `sqlite3`). The *only* state that is append-only, long-lived, and queried analytically (hit-rate by band, bias, leak-by-phase). Mirrors Hermes's existing atomic-SQLite pattern.

All of it sits behind a **`Storage` Protocol** (`get/put` for files, `append/query` for the log) so the host can later swap in GBrain/Postgres without touching skill code. **Do not reuse Hermes's DB directly** — that kills standalone portability, which M1–M3 depend on.

## Injection points (the portability seams)
Four Protocols, each with a standalone default; the host (Hermes) overrides:
- **`Senior`** — `gate(early)`, `ratify(package)`. Default: CLI human-in-the-loop. Hermes: its own escalation target.
- **`Storage`** — files + SQLite by default; swappable.
- **`LLM`** — must be injected; no default (forces explicit provider choice).
- **`PriceFeed`** — Finnhub → yfinance fallback by default.

## Config
House conventions (§2: WACC inputs, excess-cash rule, tax rate, normalization defaults, tag-fallback lists) as a **versioned YAML/TOML** loaded into a pydantic model. Time-sensitive values (risk-free, ERP) carry refresh dates; Damodaran/FRED refreshed on a schedule, not per run.

## Deployment
- **Standalone:** `pip/uv install` the module, call `analyze()`. No server, no container required.
- **In Hermes:** invoked as a skill pack; the parent resolver adds one route ("fundamental-analysis job → `analyze`"). Containerize for the Azure VM at M6.

## Explicitly OUT (to protect "lightweight")
No Postgres/MySQL or any server DB · no Kafka/Redis/message queue · no Airflow/Prefect/Dagster (the resolver orchestrates) · no web framework · no vector DB (provenance is exact lookup, not similarity) · no container requirement for standalone use. Each of these is a "later, only if a concrete need appears" — not a default.
