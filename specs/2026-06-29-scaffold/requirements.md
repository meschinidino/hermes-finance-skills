# M0 Scaffold — Requirements

## Functional Requirements

1. `analyze("AAPL")` must run without network access.
2. `analyze()` must load and validate `config/conventions.yaml`.
3. `analyze()` must initialize writable local storage under `/data`.
4. `analyze()` must write a stub JSON artifact under `data/runs/{ticker}/{as_of}/m0_stub.json`.
5. The stub result must identify itself as M0 scaffold output.
6. The `/skills` package must expose shared primitives and interface protocols for later milestones.
7. Runtime storage must be injectable through the `Storage` protocol.
8. Host integrations must remain injectable through protocols rather than hardcoded.
9. `Provenance`, `Number`, `Ratifiable`, `Header`, and `Config` must be pydantic v2 models.
10. `Provenance.form` must reject any form outside `10-K`, `10-Q`, `DEF 14A`, `Form 4`, `computed`, and `external`.
11. `Number` must reject missing provenance.
12. `Number` must reject missing derivation when `kind != "fact"`.

## Non-Functional Requirements

- No server, queue, container, or external service is required.
- No secrets are read or printed.
- Tests must run offline.
- Runtime output must be gitignored.
- The code must keep the top-level `/skills` and `/knowledge` repository convention.

## Acceptance Criteria

- `uv run --no-sync pytest` passes.
- `uv run --no-sync python -m resolver AAPL` writes a stub artifact.
- `data/pack.db` is created by local storage.
- `config/conventions.yaml` rejects missing required M1 convention fields.
- Git status shows runtime data ignored rather than tracked.
