# Local SecOps Assistant (Titan-1)

> **Built**: S1115 (2026-07-04)
> **Host**: Titan-1 / `Koskadeux.local` (Mac Studio, M3 Ultra / 256GB)
> **Location on disk**: `/Users/max/local-secops/`
> **Purpose**: Rotate / update / expire / generate credentials with a fully-local model, so secret values never leave Titan-1 and no human has to type them.
> **Owner**: Vulcan/Mars (operator-invoked); registered in Living State at `infra:local-secops`.

---

## §A. Header

The Local SecOps assistant is a supervised, local-only helper for credential operations against our self-hosted Infisical (`secrets.ai.market`). It runs a local LLM (no network egress of secret material) to draft an exact command plan, and a separate guardrailed executor to carry an approved plan out under a hard allow-list. It is deliberately two programs: a **proposer** that can only think, and an **executor** that can only act within vetted templates.

It exists because secret rotation/movement was previously a manual, error-prone, type-the-value-by-hand process. It removes the human from touching secret values while keeping the human (Max/Vulcan) in the approval loop.

**Deployed state at build:** proposer and executor both present and verified; write/get/delete proven end-to-end on the `koskadeux-mcp` Infisical project (see §K). Write on the `ai-market-backend` project is now exercised (S1125: reconciled 4 keys, round-trip verified). The Infisical→Railway native sync is LIVE.

---

## §B. Capability Matrix

| Capability | Supported | Notes |
|---|---|---|
| Draft a credential-op plan from a natural-language task | Yes | `secops_propose.py`; propose-only, never executes |
| Rotate/update a secret we own | Yes | `set` upsert; value self-generated (`secrets.token_urlsafe(48)`) |
| Copy an EXISTING value Railway → Infisical (reconcile) | Yes | `reconcile-from-railway`; host-side, value never printed/never on disk; round-trip hash-verify. Use to fix Infisical when Railway drifted ahead |
| Read/verify a secret | Yes | `get`; value not printed to chat, only round-trip proof |
| Expire/delete a secret | Yes | `delete` via raw REST API (curl `-K` stdin), because CLI delete is unreliable under this machine identity |
| Restart a dependent LOCAL service after rotation | Yes | `launchctl kickstart -k` of 3 known labels only |
| Rotate a THIRD-PARTY key (Stripe, DeepSeek, etc.) | No (partial) | Provider-issued value must arrive via a secure channel; **not wired**. The model must never invent a third-party value |
| Push a backend secret to prod | No (automatic) | The native Infisical→Railway sync (LIVE since S1125) mirrors Infisical→Railway on its own; this tool writes the Infisical catalog only |
| Autonomous/scheduled rotation | No | Operator/Vulcan-invoked only; no timer, no daemon |
| Run arbitrary shell | No | Executor rebuilds argv from vetted templates; raw model string is never run |

---

## §C. Architecture & Interactions

**Runtime.** Ollama, installed via Homebrew, running as LaunchAgent `homebrew.mxcl.ollama` (auto-starts at login), serving the API at `http://127.0.0.1:11434`. Model: `llama3.3:70b` (chosen for dependability over speed; fits the M3 Ultra / 256GB).

**Files** (all in `/Users/max/local-secops/`):
- `PLAYBOOK.md` — the authoritative command conventions the proposer is grounded on (Infisical flag shapes, project IDs, the local-vs-Railway service distinction, the secret→service restart map). This is what keeps the model from inventing flags.
- `secops_propose.py` — grounds `llama3.3:70b` on `PLAYBOOK.md` and emits a JSON plan (`intent`, `steps[]`, `destructive`, `rollback`, `notes`). **PROPOSE-ONLY.** Never executes. Uses the literal placeholder `<VALUE_FROM_OPERATOR>` for any secret value; the model is instructed never to print a real value.
- `secops_execute.py` — the guardrailed executor. Takes an approved plan JSON (or `--selftest`), DRY-RUN by default, `--execute` to act.
- `approved_plan.json` — an example approved plan (DEEPSEEK_API_KEY rotation + service restart).
- `audit.log` — append-only JSONL; every action and every refusal, values redacted.
- `HALT` — presence of this file is a hard stop (created on demand; not present in steady state).

**Vault auth.** The executor reads the SysAdmin machine-identity token from `~/.config/infisical/sysadmin-token` and passes it to the child process via ENV (for `set`/`get`) or curl stdin config (for `delete` via raw API). The token is never placed on the command line / argv.

**Infisical target.** Domain `https://secrets.ai.market`. Env slugs are allow-listed PER PROJECT (S1176 unanimous widening: MP+AG+DS+GLM all approve; Living State event on `build:bq-e2e-prod-arming-s1174`): koskadeux-mcp is `prod` only; ai-market-backend is `prod` or `staging` — `staging` is the Infisical E2E test space (Stripe TEST keys + `E2E_SYNTHETIC_*` pool secrets) per BQ-E2E-PROD-ARMING-S1174 spec §4. Never "production", never any other slug. Allow-listed projects only:
- `koskadeux-mcp` = `0943f641-faee-4324-b337-0d50c276e4a9`
- `ai-market-backend` = `bd272d48-c5a1-4b52-9d24-12066ae4403c`

**Boundary with the rest of the system.** This tool writes the catalog (Infisical). It does **not** push to Railway. Backend production picks up a changed backend secret via the native Infisical→Railway sync, which is now LIVE (S1125) and mirrors Infisical→Railway automatically (see `infisical-secrets.md`). Local Council/agent services pick up a rotated key via `launchctl kickstart`.

---

## §D. Agent Capability Map

| Actor | May do | May NOT do |
|---|---|---|
| Proposer (`llama3.3:70b`) | Draft a plan grounded on PLAYBOOK.md | Execute anything; print a real secret value; invent flags/subcommands |
| Executor (`secops_execute.py`) | Run the allow-listed actions on approved plans | Run any off-list command, touch a non-allow-listed project, run a shell |
| Vulcan/Mars (operator) | Review a proposed plan; invoke the executor; provide provider-issued third-party values through a secure channel | Bypass review; paste secret values into chat |
| Max | Approve/authorize a rotation; supply third-party provider values | — |

**Allow-listed actions (only these):**
1. `infisical secrets set NAME=VALUE` (upsert; value self-generated when placeholder + `--gen-value`)
2. `infisical secrets get NAME` (verify; `--plain`)
3. `infisical secrets delete NAME` (via raw REST API)
4. `launchctl kickstart -k gui/<uid>/<LABEL>` where LABEL ∈ {`com.koskadeux.deepseek_server`, `com.koskadeux.ag_server`, `com.koskadeux.mcp`}
5. `reconcile-from-railway NAME` — copy NAME's CURRENT value from the fixed Railway `ai-market-backend`/`production` service into the Infisical backend project. Host-side; value never printed / never on disk; round-trip hash-verify. Source service/env and target project are HARDCODED, not operator-selectable. (Write goes via the Infisical CLI — `INFISICAL_TOKEN` in env, off argv — because the raw REST write returns 403 for this identity; value is passed `NAME=VALUE` on argv, single-host posture.)

Secret NAME must match `^[A-Z0-9_]{2,64}$`. `env` must be in the per-project allow-list (`ALLOWED_ENVS`: koskadeux-mcp -> prod only; ai-market-backend -> prod or staging). `domain` must be `secrets.ai.market`. `projectId` must be allow-listed. Any shell metacharacter → refuse.

---

## §E. Operate — Serving Customers

**Standard rotation of a secret we own (e.g., an internal API key / HMAC key):**

1. Propose (nothing runs):
   ```bash
   cd /Users/max/local-secops
   ./secops_propose.py "rotate INTERNAL_API_KEY on ai-market-backend and note it reaches prod via a Railway redeploy"
   ```
2. Vulcan reviews the emitted JSON: confirm `intent`, each `command`, `reversible`/`risk` flags, and that no step prints a value. Save the vetted plan to a file (e.g. `approved_plan.json`).
3. Dry-run the executor (previews only):
   ```bash
   ./secops_execute.py approved_plan.json
   ```
4. Execute (self-generates the value where the plan uses the placeholder):
   ```bash
   ./secops_execute.py approved_plan.json --execute --gen-value
   ```
5. Propagate: for a LOCAL service, the plan's `launchctl kickstart` step restarts it. For a BACKEND (`ai-market-backend`) secret, trigger a Railway redeploy separately — this tool does not push to Railway.
6. Verify from the consumer's side (service health / endpoint), not just the vault.

**Restart-only (a service needs to re-read an already-rotated key):** a one-step plan with just the `launchctl kickstart` command.

**Reconcile an existing value Railway → Infisical (when Infisical has drifted stale):**

1. Dry-run (reads Railway, writes nothing):
   ```bash
   cd /Users/max/local-secops && ./secops_execute.py --reconcile KEY [KEY ...]
   ```
2. Execute + verify (each key is round-trip hash-verified; MATCH required):
   ```bash
   ./secops_execute.py --reconcile KEY [KEY ...] --execute
   ```
   Use this when the native sync's “prioritize Infisical” would otherwise push a **stale** Infisical value over a good Railway one. S1125 used it to correct `GITHUB_TOKEN`, `GCP_SERVICE_ACCOUNT_JSON`, `CORS_ORIGINS_EXTRA`, `GMAIL_TOPIC_NAME`.

**Secret → dependent-service restart map** (from PLAYBOOK.md):
- `DEEPSEEK_API_KEY` (koskadeux-mcp) → restart `com.koskadeux.deepseek_server`
- `VERTEX_API_KEY` (koskadeux-mcp) → restart `com.koskadeux.ag_server`
- Backend-project secrets → Railway redeploy of `ai-market-backend` (NOT launchctl)

---

## §F. Isolate — Diagnosing Deviations

- **"REFUSED: ..." on execute** — expected guardrail behaviour, not a bug. Read the reason (off-list command, non-allow-listed projectId, bad NAME, shell metacharacter, HALT present, unresolved placeholder). Fix the plan, don't loosen the executor.
- **Proposer returns non-JSON / invents a flag** — check that `PLAYBOOK.md` still matches reality (Infisical flag shapes, project IDs). The proposer is only as correct as its grounding; drift in PLAYBOOK.md is the usual root cause.
- **`get` round-trip fails after a `set` that returned rc=0** — check the Infisical token validity (`~/.config/infisical/sysadmin-token`) and that the project/env are correct.
- **`delete` returns a non-zero rc** — CLI delete is unreliable under this identity; the executor already uses the raw REST API path. A transient non-200 (rc=98/curl error) can occur; re-run and confirm via a follow-up `get` that the key is gone. (audit.log shows historical rc=98 followed by a clean rc=0 delete.)
- **Ollama unreachable (`127.0.0.1:11434`)** — check the LaunchAgent: `brew services list | grep ollama`. If stopped, `brew services start ollama`.
- **Nothing executes at all** — check for a stray `HALT` file in the dir.

Every run and refusal is in `audit.log` (JSONL, values redacted) — read it first when diagnosing.

---

## §G. Repair — Fixing Problems

- **Restart the model runtime:** `brew services restart ollama`.
- **Re-prove the executor end-to-end** (safe, disposable key on koskadeux-mcp, set→get→delete):
  ```bash
  cd /Users/max/local-secops && ./secops_execute.py --selftest --execute
  ```
  A clean run appends three execute records (set rc=0, selftest_get rc=0, delete rc=0) to audit.log and leaves no residue.
- **Token expired / rotated:** replace `~/.config/infisical/sysadmin-token` with a current SysAdmin machine-identity token (see `infisical-secrets.md#machine-identities`). Never commit it.
- **Playbook out of date:** edit `PLAYBOOK.md` to current Infisical/service reality, then re-run a propose to confirm the model tracks it.

---

## §H. Evolve — Extending the System

**Guardrail-first rule:** any capability that lets the executor do something new (a new command class, a new project, a new service label) is a change to the allow-list in `secops_execute.py` and MUST be reviewed as security-class work (Council per CORE §3). Do not widen the allow-list casually. (Applied S1176: the per-project env-slug widening — ai-market-backend gains `staging`, the E2E test space — was reviewed UNANIMOUSLY by MP + AG + DeepSeek + GLM before first use; verified by prod selftest, staging round-trip on a disposable key, and negative probes. Applied S1125: the `reconcile-from-railway` action was reviewed by DeepSeek + GLM — both APPROVE_WITH_MANDATES — before first prod use; mandates addressed: no secret on disk, verify reads back from explicit project/env.)

Planned/known extension points:
- **Third-party key rotation (Stripe, DeepSeek, etc.):** blocked by design — the provider issues the value, which must reach the executor through a secure channel (never chat). Wiring a secure-channel intake is the main open extension; until then, third-party rotation stays manual per `infisical-secrets.md`.
- **`ai-market-backend` project writes:** exercised S1125 (reconcile of 4 keys, round-trip MATCH). Write goes via the Infisical CLI (raw REST write 403s for this identity).
- **Backend propagation:** this tool stops at the catalog. The native Infisical→Railway sync is now LIVE (S1125, auto-sync on, disable-deletion on), so a backend-secret write in Infisical propagates to Railway automatically. CAUTION: because the sync prioritizes Infisical, never leave a **stale** value in Infisical for a shared key — use `reconcile-from-railway` if Railway is ahead.

---

## §I. Acceptance Criteria (for this runbook)

- A reader who has never seen the tool can rotate an owned secret end-to-end from §E without touching a secret value.
- The four allow-listed command classes and their validation rules are stated exactly (§D).
- Kill switches and the audit trail are discoverable (§J, §F).
- Boundaries (third-party keys, backend propagation, no autonomy) are unambiguous (§B, §H).

## §J. Lifecycle

**Kill switches:**
- Stop the model: `brew services stop ollama`
- Freeze all execution: `touch /Users/max/local-secops/HALT` (remove the file to re-enable)

**Audit:** `audit.log` (append-only JSONL, values redacted). Every action and refusal is recorded with a UTC timestamp, mode (`dry_run`/`execute`/`refuse`), and rc.

**Invocation model:** operator/Vulcan-invoked only. No scheduler, no daemon, no autonomous rotation. The proposer never executes; the executor is DRY-RUN unless `--execute` is passed.

**Dependencies:** Ollama LaunchAgent; SysAdmin machine-identity token at `~/.config/infisical/sysadmin-token`; self-hosted Infisical at `secrets.ai.market`.

## §K. Conformance

- **Proven live (S1115):** disposable-key set→get→delete on `koskadeux-mcp` (`0943f641…`), value self-generated and redacted, no residue (audit.log 2026-07-04T14:21). Refusal paths proven: placeholder-without-gen, off-list command, non-allow-listed projectId, HALT-present.
- **Exercised S1176:** staging-env set/get/delete round-trip on `ai-market-backend` (disposable key, no residue); negative probes REFUSED (staging on koskadeux-mcp; dev on backend); 20 `E2E_SYNTHETIC_*` pool secrets provisioned via propose-review-execute.
- **Exercised S1125:** `reconcile-from-railway` on `ai-market-backend` (`bd272d48…`) for 4 keys, all round-trip MATCH; reviewed DeepSeek + GLM APPROVE_WITH_MANDATES (mandates addressed). **Still unwired:** third-party-key intake.
- **Grounding source of truth:** `PLAYBOOK.md` in the tool directory — keep it in sync with Infisical/service reality.

## §L. Topic router & self-containment

Registered in `TOPIC-ROUTER.md` under Secrets/credentials. Cross-references: `infisical-secrets.md` (the secret store, machine identities, third-party rotation), `titan-1.md` (host, LaunchAgents, Railway token), and BQ-RAILWAY-INFISICAL-SYNC / `infisical-secrets.md` for backend→Railway propagation. This page is self-contained for local-secops operation; you should not need to leave it to rotate an owned secret.
