# BQ-RUNBOOK-HARNESS-PRODUCTION-WIRING — CI Audit (AC5)

**Parent spec:** `specs/BQ-RUNBOOK-HARNESS-PRODUCTION-WIRING-GATE2.md` (D5, AC5)

**Workflow under audit:** `.github/workflows/runbook-harness.yml`

**Audited at:** 2026-04-24

## 1. Trigger audit

| Trigger | Present | Evidence |
|---|---:|---|
| Nightly `schedule` cron | yes | `.github/workflows/runbook-harness.yml:3-4` (`cron: '0 7 * * *'`) |
| Manual `workflow_dispatch` | yes | `.github/workflows/runbook-harness.yml:5` |
| `pull_request` trigger | **no** | not listed in `on:` block |
| `push` to main trigger | **no** | not listed in `on:` block |

**Verdict:** The workflow runs only nightly and on manual dispatch. It is not a PR-blocking lane. No code-path runs this workflow as a PR status check.

## 2. Mode audit

| Invocation | Mode | Evidence |
|---|---|---|
| `runbook-lint --mode strict --update-lifecycle` | strict normal | `.github/workflows/runbook-harness.yml:18` |
| `runbook-harness --mode conformant --session "CI-$(date -u +%Y%m%d)"` | normal harness | `.github/workflows/runbook-harness.yml:23` |

**External-mode surface check:**

- `--external-scenario-set` — not passed anywhere in the workflow.
- `--external-scenarios-from-state` — not passed anywhere in the workflow.

**Verdict:** CI exercises only the §I-authoritative normal harness path. External mode is reserved for ad-hoc G4-style falsifiability runs per D5, and there is no PR-blocking lane that would invoke it.

## 3. Permissions audit

| Scope | Value | Evidence |
|---|---|---|
| `permissions.contents` | `write` | `.github/workflows/runbook-harness.yml:11` |
| Other scopes | not granted (default `none` at workflow level) | no other entries under `permissions:` |

`contents: write` is required so the "Commit updates" step at `.github/workflows/runbook-harness.yml:24-30` can persist §J grace-clock updates produced by `--update-lifecycle`. No broader write scopes (`actions`, `pull-requests`, `packages`, `id-token`, etc.) are granted.

**Verdict:** permissions are scoped to the minimum needed for the nightly lifecycle-write step.

## 4. Secret audit

| Secret | Used at | Justification |
|---|---|---|
| `KOSKADEUX_MCP_URL` | step env (line 21) | MP dispatch endpoint for harness scenarios |
| `KOSKADEUX_MCP_TOKEN` | step env (line 22) | Bearer auth for the MP dispatch endpoint |

Both secrets are consumed only by the harness step. They are not exposed to the lint step or the commit step.

## 5. PR-blocking lane declaration

- **PR-blocking lanes today:** none in this workflow. PR blocking, if any, is configured outside this file (branch protection, other workflows). This workflow itself does not register as a required status check for PRs.
- **If a PR-blocking lane is added later:** per D5 and AC5, it must run normal harness only. External mode must not be invoked as a required status check.

## 6. Acceptance mapping

- **AC5 ("CI workflow audit is documented; PR-blocking lanes, if any, stay on normal path only")** → this document.
- **D5 ("Audit CI so external mode is not run in a PR-blocking lane")** → confirmed in §2 above.

## 7. Follow-up

None required for Gate 3. If a future workflow change adds a `pull_request` trigger or a required-check registration, re-audit this file and re-assert the "normal mode only" invariant for PR-blocking lanes.
