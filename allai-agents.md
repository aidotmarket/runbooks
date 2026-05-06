# allAI — Agent Intelligence Layer

## What it is

The intelligence layer inside ai-market-backend. Runs all autonomous agents (Brain, SysAdmin, CRM Steward, Matchmaker, etc.), the service bus for inter-agent communication, and the agent host that manages lifecycle, events, and subscriptions.

**Location:** `app/allai/` inside [aidotmarket/ai-market-backend](https://github.com/aidotmarket/ai-market-backend)
**Runtime:** Starts with the backend — agents boot when the FastAPI app starts
**Dashboard:** `ops.ai.market/agents` (unified fleet view)

## Architecture

```
AgentHost (agent_host.py)
  ├── registers agent classes on startup
  ├── instantiates agents with DB/Redis/Qdrant clients
  ├── manages event subscriptions
  └── routes tasks to agents via service bus

ServiceBus (service_bus.py)
  ├── permission matrix (who can call whom)
  ├── delegation modes (direct, broadcast, tier-routing)
  ├── audit trail (every inter-agent call logged)
  └── idempotency store (prevents duplicate processing)
```

## Agents

| Agent | File | Key skills | Purpose |
|-------|------|-----------|--------|
| allAI:Brain | `agents/allai_brain.py` | triage_request, council_dispatch, report_incident | Central routing brain — triages incoming requests to the right agent |
| SysAdmin | `agents/sysadmin/agent.py` | health checks, backups, deploy monitoring | Infrastructure guardian — backups, alerts, cartography |
| CRM Steward | `agents/crm_steward.py` | contact upsert, interaction logging | CRM management — contacts, organizations, pipeline |
| Matchmaker | `agents/matchmaker.py` | match scoring, buyer-seller matching | Connects data buyers with relevant sellers |
| ListingEnricher | `agents/listing_enricher.py` | metadata enrichment, quality scoring | Enhances listing metadata for better searchability |
| MarketingOps | `agents/marketing_ops.py` | campaign management, draft generation | Marketing automation and content generation |
| AgentLog | `agents/agent_log.py` | log writes, audit trail | Records all agent activity for accountability |
| Ralph | `agents/ralph/agent.py` | sandbox, security, observability | Learning and experimentation agent |
| Finance | `agents/finance/agent.py` | revenue tracking, transaction monitoring | Financial operations agent |

## Agent host lifecycle

1. **Registration:** Agent classes registered in `app/allai/__init__.py` via `agent_host.register(AgentClass)`
2. **Startup:** `agent_host.start()` called from FastAPI lifespan — instantiates all registered agents
3. **Subscriptions:** Each agent declares event subscriptions in its manifest. The host wires these to the service bus.
4. **Event processing:** When an event fires, the host routes it to subscribed agents. Agents process via their `handle_event()` method.
5. **Shutdown:** `agent_host.stop()` called on app shutdown — graceful agent cleanup.

## Agent registration pattern

Every agent extends `BaseAgent` and declares:
- `name` — display name
- `agent_key` — unique identifier (used in CP, health, Living State)
- `interaction_modes` — how it can be invoked (rest_api, event, scheduled)
- `@skill` decorated methods — capabilities exposed to the control plane
- `monitoring_policy` — health metrics, validation rules, escalation rules

## Key files

| File | Purpose |
|------|--------|
| `app/allai/agent_host.py` | AgentHost class — lifecycle, routing, event dispatch |
| `app/allai/service_bus.py` | Permission matrix, delegation, audit |
| `app/allai/agent_manifest.py` | Manifest schema — skills, subscriptions, policies |
| `app/allai/agent_registry.py` | Runtime registry of active agents |
| `app/allai/agent_router_registry.py` | Maps agent keys to FastAPI routers |
| `app/allai/action_guard.py` | Permission enforcement for agent actions |
| `app/allai/trace_context.py` | Request tracing across agent calls |
| `app/allai/agents/manifests.py` | Compiled manifests for all agents |

## State architecture — build-queue lifecycle ownership

Living State entities (`build:bq-*`, `config:*`, `infra:*`) are persisted in the ai-market-backend Postgres `StateEntity` table. The backend owns build-queue lifecycle alongside the data: status transition rules, gate progression, build-body invariants, and the `config:core-pillars` enum check are evaluated in-process by `app/services/bq_lifecycle_service.py` (`BuildQueueLifecycleService`), which delegates persistence to `StateService.atomic_write`. The dedicated lifecycle endpoint group `/api/v1/allai/build-queue/*` is the canonical write path for status changes; generic state CRUD via `/api/v1/allai/state/*` is for non-lifecycle entity access.

The Mac-side `koskadeux-mcp/tools/state.py` `bq_*` handlers (Titan-1) retain their own validation logic for now and continue calling `/api/v1/allai/state/atomic_write` directly — this is a transitional state. A subsequent BQ migrates the Mac-side handlers to call the new backend lifecycle endpoints, retiring the duplicate validators on Titan-1; until then, both paths must remain bug-for-bug compatible (gated by the golden parity test suite in ai-market-backend at `tests/integration/test_bq_lifecycle_parity.py`).

**Implication for agents:** any agent that needs to move a BQ between `planned/in_progress/completed/failed/blocked/cut/approved/done` should prefer the backend lifecycle endpoint. Direct `kind='build'` writes through generic state CRUD bypass the lifecycle validator and are tracked as a follow-up audit item.

## Monitoring

Agent health visible at `ops.ai.market/agents`. Three data sources merged:

| Source | Endpoint | Data |
|--------|----------|------|
| Control Plane | `GET /api/v1/cp/agents/` | Registry status, versions, heartbeats |
| allAI Host | `GET /api/v1/allai/agents/status` | Runtime: subscriptions, event counts |
| Health | `GET /api/v1/internal/agent-health` | Metrics, validation failures, policies |

## Troubleshooting

| Problem | Diagnosis | Fix |
|---------|-----------|-----|
| Agent shows REGISTERED but not ONLINE | No heartbeat — agent registered but not started | Check `agent_host.start()` in app lifespan, check logs for startup errors |
| Agent not responding to events | Subscription not wired | Check manifest `subscriptions` list, verify event type matches |
| 500 on agent details endpoint | Pydantic validation error | Check Railway logs — usually schema mismatch (skills as dict vs list, datetime issues) |
| Agent health all "critical" | Metrics all stale — no readings being written | Agent monitoring policy present but no metric collection running |
| Inter-agent call permission denied | Service bus permission matrix | Check `permission_matrix` in `service_bus.py` |
| Agent events accumulating but not processing | Event handler error or slow processing | Check agent `handle_event()` logs, look for exceptions |

## Adding a new agent

1. Create agent file in `app/allai/agents/`
2. Extend `BaseAgent`, set `name`, `agent_key`, `interaction_modes`
3. Add `@skill` methods for capabilities
4. Add `monitoring_policy` for health tracking
5. Register in `app/allai/__init__.py`
6. Run migration if new DB tables needed
7. Push to main — Railway deploys, agent starts automatically

---

*Created: S363 (2026-04-01)*
