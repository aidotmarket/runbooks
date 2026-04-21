# ai.market Runbooks

This repository is the source of truth for every system-level runbook in ai.market.
Every runbook conforms to the standard defined in `specs/BQ-RUNBOOK-STANDARD.md`.

## Adoption status

| System | Runbook | Status | Gate | Linter | Harness | Owner |
|---|---|---|---|---|---|---|
| _(No systems yet conformant — Chunk 2 will add Infisical + AIM Node)_ | — | NOT_STARTED | — | — | — | — |

## Status values

- `NOT_STARTED` — adoption planned, no BQ filed
- `GATE_1_IN_PROGRESS` — runbook BQ open at Gate 1
- `GATE_1_APPROVED` — Gate 1 passed, Gate 2 not yet open
- `GATE_2_IN_PROGRESS` — Gate 2 authoring and build
- `GATE_3_IN_PROGRESS` — code audit underway
- `GATE_4_IN_PROGRESS` — production verification
- `CONFORMANT` — all four gates passed, lint + harness passing
- `RETROFIT_CANDIDATE` — pre-existing runbook needs structural rework (content stays valid)
- `LEGACY_NOT_UNDER_STANDARD` — predates the standard, not on adoption roadmap
- `DEPRECATED` — system is being retired; runbook kept for history

## Working on a runbook

- Create a new runbook: `runbook-new <system-name>`
- Validate a runbook: `runbook-lint <path>`
- Run the harness locally: `runbook-harness --runbook <path>`

## Tooling

This repository ships `runbook-tools`, a Python package providing:
- `runbook-lint` — validates runbooks against the standard (20 checks per §K.1 of the spec)
- `runbook-new` — generates a scaffold runbook
- `runbook-harness` — runs the stateless-agent legibility harness nightly

Installation: `pip install -e .` (Python 3.11+).

Design contract: `specs/BQ-RUNBOOK-STANDARD-GATE-2-CHUNK-1.md`.

