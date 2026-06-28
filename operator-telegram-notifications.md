# Operator Telegram Notifications Runbook

## §A. Header
- **Purpose:** Governs which bot(s) may message the human operator (Max) on Telegram, and what classes of message are allowed.
- **Owners:** Mars / Vulcan (peer-symmetric).
- **Policy source:** Max, S1054 (2026-06-28).
- **One-line policy:** Only `@allai_agent_bot` messages the operator, and only for emergency or human-required notifications. `@koskadeux_bot` is killed outright; the human-required dispatch alerts are re-routed through allai.

## §B. The two senders (as-found, S1054)
| Bot | Process / repo | Token source | Sends | Disposition |
|-----|----------------|--------------|-------|-------------|
| `@allai_agent_bot` | Backend `app/services/telegram_relay.py` (`telegram_service`), Railway | `TELEGRAM_BOT_TOKEN` (Railway, backend env) + admin `chat_id` | HITL/human-in-the-loop requests, operator alerts | **KEEP** (sole operator channel) |
| `@koskadeux_bot` | Titan-1 dispatch/health daemon: `koskadeux-mcp/kd_notifier.py` + `kd_sentinel.py` | `TELEGRAM_BOT_TOKEN` (`826276…`) + `TELEGRAM_CHAT_ID` in `/Users/max/koskadeux-mcp/.env` | CRITICAL dispatch/health alerts: review-ready, blocked, drift, budget-halt, system-health | **KILL** Telegram (keep local macOS notifications) |

Both are distinct bot accounts (verified via `getMe`): the daemon token resolves to `@koskadeux_bot`, the backend to `@allai_agent_bot`.

## §C. Architecture & Interactions
- `@allai_agent_bot` sends via `telegram_service.send_message(text)` → operator admin chat. Internal callers reach it through the backend.
- The daemon currently posts straight to `api.telegram.org/bot<koskadeux_token>/sendMessage`. `kd_notifier._send_telegram` is already gated to `level == CRITICAL`; `kd_sentinel` funnels its criticals through `kd_notifier.notify(BLOCKED)`.
- **Target routing for human-required daemon alerts:** daemon POSTs to backend `POST /api/v1/allai/admin/operator-alert` (internal-key, `X-Internal-API-Key`) → `telegram_service.send_message` → `@allai_agent_bot` → operator chat.

## §D. Agent Capability Map
- Backend allai relay: owns the single operator Telegram channel.
- Dispatch/health daemon: emits to macOS locally; for human-required events it calls the backend operator-alert endpoint instead of its own bot.

## §E. Operate — allowed notification classes
Operator Telegram is reserved for **emergency or human-required** only:
- Human-in-the-loop (HITL) approval/decision requests.
- "Council review ready" (a review needs the operator).
- "Autonomous work blocked / unrecoverable" (dispatch or sentinel).
Everything else (subtask progress, item-started, drift, budget warnings, worker timeouts, daemon start/stop, routine CRM/ops) stays off Telegram — local logs / macOS only.

## §F. Isolate — Diagnosing
- Unexpected operator message: check the sending bot's username. `@koskadeux_bot` ⇒ a daemon path still has Telegram enabled (regression); `@allai_agent_bot` ⇒ a backend caller is over-notifying — audit its call site against §E.

## §G. Repair / Implementation steps (status)
1. **[DONE S1054]** Peer-message ACK escalations no longer DM the operator — gated behind `PEER_MSG_ACK_ESCALATION_TELEGRAM` (default off) in `app/services/reconciliation_job.py`.
2. **[TODO]** Backend: add `POST /api/v1/allai/admin/operator-alert` (internal-key) → `telegram_service.send_message`.
3. **[TODO]** `kd_notifier.py`: remove all `@koskadeux_bot` sends; for `REVIEW_READY`/`BLOCKED` POST the operator-alert endpoint; drop other types from Telegram (keep macOS).
4. **[TODO]** Daemon `.env`: remove `@koskadeux_bot` `TELEGRAM_BOT_TOKEN` + `TELEGRAM_CHAT_ID` (belt-and-braces kill).
5. **[TODO]** Allai-side audit: confirm `@allai_agent_bot` only emits §E classes (keep HITL; review CRM-playbook `notify_channels: [telegram]`).
6. **[TODO]** Coordinated **daemon restart** to activate (peer-coordinated; restart of the dispatch daemon).

## §H. Evolve — Invariants
- Exactly one operator Telegram bot: `@allai_agent_bot`.
- Any new code path that would DM the operator must route through the backend relay and satisfy §E; no new bot tokens.

## §I. Acceptance Criteria
- After activation: zero messages from `@koskadeux_bot`.
- A simulated "review ready" / "blocked" arrives from `@allai_agent_bot`.
- Routine daemon events produce no Telegram, only macOS/log output.

## §J. Lifecycle
- Refresh triggers: any new Telegram sender added; any change to the operator chat id; addition/removal of a human-required alert class.

## §K. Conformance
- Authored to BQ-RUNBOOK-STANDARD §A–§K. Registered in TOPIC-ROUTER.md.
- Related: allai-agents.md, peer-instance-discipline.md, activation-verification.md.
