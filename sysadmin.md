# SysAdmin Operating Model (S1086)

> Bounded SysAdmin runbook for the live operating loop:
> Observe -> Decide -> Act -> Verify -> (Fix | Escalate).
> Source of truth is the S1086 Gate-2 spec plus live backend code; this page is the operator map.

## §A. Header

- **BQ:** `build:bq-sysadmin-operating-model-redesign-s1086` (docs build S1097).
- **Repo / surfaces:** `ai-market-backend` - `app/allai/agents/sysadmin/agent.py`,
  `app/allai/agents/sysadmin/singleton.py`, `app/agents/sysadmin/skills/{railway_ops,infisical_ops,shell_ops}.py`,
  `app/api/v1/endpoints/agent_health.py`, `app/main.py`.
- **Authoritative design:** `specs/BQ-SYSADMIN-OPERATING-MODEL-REDESIGN-S1086-GATE2.md`.
  This runbook summarizes live operation; the spec and code win on implementation detail.
- **Operating state:** process-local SysAdmin singleton owns probing, compliance reporting, and
  health-contract scheduling. AgentHost owns event dispatch only.
- **Status (S1097):** verified live 2026-07-02 - `HEALTHY`, `compliant=true`, 10/10 checks,
  0 disabled capabilities, 6/6 contracts fresh and ok at backend commit `8ac99a03`.

## §B. Capability Matrix

| Capability | State | Where |
|---|---|---|
| `railway_read_status` | VERIFIED read | `railway_ops.py`, contract `railway_status` |
| `railway_env_set_redeploy` | VERIFIED bounded write, dry-run first | `railway_ops.py`, contract `railway_status` |
| `infisical_read_metadata` | VERIFIED metadata-only read | `infisical_ops.py`, contract `infisical_metadata` |
| `resend_domain_status` | VERIFIED provider read | `app/services/sysadmin_resend.py`, contract `resend_domain_status` |
| `host_inspect` | VERIFIED read-only checkout inspection | `shell_ops.py`, contract `host_inspection` |
| `titan1_health` | VERIFIED Titan-1/MCP health read | `agent.py`, contract `titan1_health` |
| `mcp_server_restart` | VERIFIED dry-run/runbook-owned restart proposal | `railway_ops.py`, contract `titan1_health` |
| `escalation_test` | VERIFIED escalation route self-test | `agent.py`, contract `escalation_route` |

Advertised, bound, and verified names must be identical. Missing callable, probe, owner, sanitizer,
or health contract is a compliance failure.

## §C. Architecture & Interactions

SysAdmin is a small loop: Observe typed evidence, Decide failure class and allowed action, Act only
through a verified capability, Verify by rerunning the contract, then Fix or Escalate.

Bind probes are fail-loud typed checks. A bind failure never crash-loops SysAdmin because SysAdmin is
on the escalation path. Instead it enters LOUD-DEGRADED: `DEGRADED` for non-core failure,
`UNAVAILABLE` for core escalation/health or router failure. Failed capabilities are hard-disabled
and reported with `probe_errors`.

The process-local singleton from `singleton.py` is the one probing, compliance-reporting, and
contract-scheduling instance. App lifespan starts one scheduler task, shutdown cancels it, and the
scheduler records cadence-honoring terminal evidence.

AgentHost also registers `SysAdminAgent`, but that event instance starts with `probe_on_startup=False`
to stay inside the 5s host startup budget. It must never run probes. `/agent-compliance` always
reports singleton state regardless of AgentHost registry state.

Known limitation: singleton state is process-local; multi-worker consistency is out of scope.

## §D. Agent Capability Map

SysAdmin singleton owns probes, disablement, scheduler, `/agent-health`, `/agent-compliance`, and
`get_system_status`. AgentHost SysAdmin is an event-bus participant only. Railway owns project-scoped
status and env proposal/execution/redeploy verification; Infisical owns metadata-only reads; host
inspection owns read-only checkout commands; escalation owns the self-tested SysAdmin -> allAI ->
Telegram route.

## §E. Operate

### §E.1 Compliance endpoint

Call `/api/v1/internal/agent-compliance` with `X-Internal-API-Key: <INTERNAL_API_KEY>`.
`INTERNAL_API_KEY` lives in Infisical project `ai-market-backend`, env `prod`, and gates this endpoint.

Read the SysAdmin row first. `compliant` is true only when all 10 checks pass.
`checks.scheduler_evidence_fresh` means every typed contract completed within
`2 * cadence + jitter + timeout` and the last result is ok. `probe_errors` and
`dispatch_probe_errors` are exact degraded-state evidence.

### §E.2 Health contracts

| Contract | Cadence | Capability dependency | Purpose |
|---|---:|---|---|
| `railway_status` | 300s | `railway_read_status`, `railway_env_set_redeploy` | Railway project service/deploy evidence |
| `infisical_metadata` | 900s | `infisical_read_metadata` | Secret metadata access without plaintext |
| `resend_domain_status` | 900s | `resend_domain_status` | Resend domain status evidence |
| `host_inspection` | 300s | `host_inspect` | Canonical checkout and host metadata evidence |
| `titan1_health` | 300s | `titan1_health`, `mcp_server_restart` | `https://mcp.ai.market/health/titan1` evidence |
| `escalation_route` | 300s | `escalation_test` | SysAdmin -> allAI -> Telegram route evidence |

### §E.3 Credentials and Railway token recovery

For this agent, `RAILWAY_API_TOKEN` is project-scoped for project `ai-market`
(`e81dd66f-808c-412e-b32c-f6d910f0ac5d`) and env `production`
(`23e322c3-b195-45d8-9151-c4c27a998c33`). It authenticates only with
`Project-Access-Token`; `Authorization: Bearer <project token>` returns Not Authorized.

The token lives in Infisical project `ai-market-backend`
(`bd272d48-c5a1-4b52-9d24-12066ae4403c`), env `prod`, and as a Railway service variable on
`ai-market-backend`.

Re-mint without dashboard access:
1. On Titan-1, `source ~/bin/railway-env.sh` to load the account token from `titan-1.md` Railway auth.
2. POST to `https://backboard.railway.app/graphql/v2` with
   `Authorization: Bearer <account token>`.
3. Run `projectTokenCreate(input:{projectId, environmentId, name})` for the ai-market project and
   production environment IDs above.
4. Store it in Infisical, set the Railway service variable, and redeploy.

## §F. Isolate

Start with `/agent-compliance`. If degraded, identify the failed capability from `disabled_capabilities`,
`probe_errors`, and `contracts.<id>.last_result`.

Scope by contract: `railway_status` means project token, deploy state, or env-set/redeploy path;
`infisical_metadata` means project token, allowed env, or metadata endpoint; `resend_domain_status`
means provider key/domain state; `host_inspection` means checkout, `RAILWAY_GIT_COMMIT_SHA`, or
allowlisted command; `titan1_health` means `mcp.ai.market` or Titan-1; `escalation_route` means
Telegram settings or allAI escalation plumbing.

Do not use AgentHost registry presence as proof of SysAdmin health.

## §G. Repair

Capability disabled means the bind or dispatch probe failed. Read `probe_errors` and fix the
systemic cause: credential, skill, provider API, runbook router, model pin, or scheduler evidence.
Never re-enable a capability by hand.

Railway token failures usually present as authorization errors in `railway_status`. Confirm the token
is project-scoped and `railway_ops.py` uses `Project-Access-Token`; otherwise follow §E.3 and redeploy.

For skill defects, repair the skill and rerun bind/dispatch probes. Do not bypass the registry or use
`break_glass`.

Contract failures dedupe by normalized fingerprint. Repeated identical failures escalate once with
grouped evidence; use the fingerprint to connect later sightings.

Auto-remediation is allowlisted only, dry-run first, budgeted, and verified by the named contract.
Off-allowlist, low-confidence, exhausted, or failed verification paths escalate.

## §H. Evolve

### §H.1 Invariants
- Operating loop remains Observe -> Decide -> Act -> Verify -> (Fix | Escalate).
- Advertised == bound == verified for every SysAdmin capability.
- Runtime init probes exercise real dependency paths, not static metadata.
- LOUD-DEGRADED is visible through `/agent-health`, `/agent-compliance`, and `get_system_status`.
- The singleton is the only probing, compliance-reporting, and scheduling instance.
- AgentHost SysAdmin starts with `probe_on_startup=False` and never probes.
- Scheduler freshness means every contract completed within `2 * cadence + jitter + timeout` and ok.
- Secret values are sanitized from logs, audit payloads, compliance responses, exceptions, prompts, and returns.

### §H.2 Do NOT
- Do not reimplement inline probes. Every bind probe delegates to the real skill via
  `agent.py:_probe_capability`; the S1097 Railway Bearer-vs-Project-Access-Token incident is the
  cautionary example.
- Do not bypass compliance with `break_glass`.
- Do not place account-scoped Railway tokens on public-facing services (S916).
- Do not let AgentHost or class-definition fallback report SysAdmin compliance.
- Do not return plaintext Infisical or Railway secret values to handlers, logs, LLMs, or endpoints.
- Do not add broad shell write, git commit/push, GCP local-config query, CRM workflow, support-ticket,
  or cartographer surfaces without a future verified contract.

## §I. Acceptance Criteria

- `/agent-compliance` reports SysAdmin from the singleton regardless of AgentHost registry state.
- 10/10 SysAdmin checks pass, including parity, no disabled capabilities, scheduler freshness,
  executable policy, current model pin, and escalation path.
- Six typed contracts are fresh and ok: `railway_status`, `infisical_metadata`, `resend_domain_status`,
  `host_inspection`, `titan1_health`, `escalation_route`.
- A failed non-core bind probe produces `DEGRADED`; failed core escalation/health or router state
  produces `UNAVAILABLE`; neither state crash-loops the app.
- Railway operations use `Project-Access-Token`, dry-run/proposal, approval for execution, fingerprint
  plus deploy verification, and value sanitization.
- Infisical reads metadata only; Resend, host, Titan-1, and escalation route are real probed paths.

## §J. Lifecycle

Gate 2 design S1086 specified the verified capability registry, LOUD-DEGRADED init, typed contracts,
remediation budgets, runbook router, and compliance endpoint behavior. Implementation reduced
SysAdmin to the bounded set, added the singleton, moved compliance to live evidence, and wired
lifespan scheduling with cancel-on-shutdown.

S1097 docs build adds this runbook and router entry. Do not merge this branch automatically.

## §K. Conformance

- Last verified: **2026-07-02 S1097** - live backend `8ac99a03` reported `HEALTHY`,
  `compliant=true`, 10/10 checks, 0 disabled capabilities, and all 6 contracts fresh and ok.
- Source validated against S1086 Gate-2 spec and live code paths:
  `agent.py`, `singleton.py`, `railway_ops.py`, `infisical_ops.py`, `shell_ops.py`,
  `agent_health.py`, `main.py`, and `agent_host.py`.
- Known limitation remains: process-local singleton state. Multi-worker consistency is not claimed.
