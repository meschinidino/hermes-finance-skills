# Agent Guide

## Product Shape

This repo is a portable fundamental-analysis skill pack for Hermes and standalone runs. It turns a US-listed ticker into an auditable, decision-ready handoff. The Senior is the only signer; deterministic Accountants compute and fail closed; LLM-driven Analysts only draft, flag, and attach evidence.

Read these first before planning changes:
- `specs/mission.md`
- `specs/tech-stack.md`
- `specs/filing-rules.md`
- `specs/roadmap.md`

## Current Build State

M0 is complete: scaffold, pydantic primitives/config, injected interfaces, local storage, and stub resolver.

For the current implementation slice, defer to `specs/roadmap.md`; do not rely on stale milestone notes in this file.

## Repository Layout

- `/skills` is the canonical home for skill code.
- `/knowledge` is the canonical home for analyst references, runbooks, and reusable domain knowledge.
- `/specs` is the constitution and roadmap.
- `/config/conventions.yaml` is the M0/M1 conventions source.
- `/data` is runtime state and must stay ignored.

Each skill is a folder bundle:

```text
skills/<dept>/<skill>/
├── SKILL.md
├── <skill>.py
├── test_<skill>.py
├── test_integration.py
└── resolver.entry
```

Analyst skills additionally include `prompt.md` and `eval/`. Accountant skills must not include prompt/eval surfaces unless the role changes.

Every new skill from M1 onward must fill `specs/SKILL-template.md`.

## Validation

Use the project-local virtualenv and uv cache:

```text
UV_CACHE_DIR=.uv-cache .venv/bin/uv run --no-sync pytest
UV_CACHE_DIR=.uv-cache .venv/bin/uv run --no-sync python -m resolver AAPL
```

The `--no-sync` flag is intentional for local validation after dependencies are installed; it prevents unexpected PyPI access in restricted environments.

## Engineering Rules

- Pydantic v2 owns M0 primitives and config contracts.
- Do not duplicate M0 primitive/config/storage definitions in M1 specs or skills.
- No bare numeric values may cross skill boundaries. Use `Number` with `Provenance`.
- `Number` must reject missing provenance.
- Non-fact `Number` values must carry `derivation`.
- Accountants fail closed and never impute missing concepts.
- Runtime artifacts go under `/data`, not git.
- Keep dependencies small and consistent with `specs/tech-stack.md`.
