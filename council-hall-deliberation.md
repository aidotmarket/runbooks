# Council Hall — Multi-Agent Deliberation Process

## Purpose

Council Hall is the structured process for getting independent, unbiased assessments from multiple Council agents (MP, AG, XAI, and DeepSeek when out of read-only eval window) on a topic, then facilitating cross-pollination and consensus. It replaces ad-hoc multi-dispatch patterns where Vulcan pre-assigns roles (e.g., "challenger" vs "designer") which biases outputs.

## Core Principles

1. **No role pre-assignment.** Every agent receives the same neutral prompt. Do not frame one agent as "challenger" and another as "constructive." Each agent arrives at their own perspective independently.
2. **Independent first.** All agents submit before any agent sees another's response. This prevents anchoring bias.
3. **Cross-pollination second.** After all independent assessments are collected, each agent receives the full set and responds to specific points of agreement or disagreement.
4. **Structured verdicts.** Each response includes structured fields (verdict, confidence, key claims, objections) alongside free-text analysis. This makes consensus computable rather than relying on prompt parsing.
5. **All agents included.** MP, AG, XAI, and DeepSeek all participate unless explicitly excluded. No agent is "default excluded" from strategy discussions. **DeepSeek caveat (S516):** during the active evaluation window (`infra:council-comms.deepseek.evaluation.active=true`), DeepSeek is `read_only=true` and dispatched via direct API (not yet via `deepseek_server.py` — that ships under `BQ-COUNCIL-DEEPSEEK-SERVER-PARITY` Gate 2). Frontier model is `deepseek-v4-pro` only; `deepseek-v4-flash` is BANNED for Council use per Max S516 directive.

## Phases

### Phase 1: Independent Assessment

Vulcan dispatches the same prompt to all agents simultaneously. The prompt must be:
- **Neutral** — no role labels, no "your job is to challenge"
- **Complete** — full context embedded (agents don't share memory)
- **Structured** — asks for specific deliverables, not open-ended "thoughts"

Example prompt structure:
```
[TOPIC] ASSESSMENT — {Title}

Context: {Background information}

The proposal: {What's being considered}

Assess this. Consider:
- {Specific dimension 1}
- {Specific dimension 2}
- {Specific dimension N}

Be specific and actionable.
```

Notes on agent dispatch:
- **MP**: `council_request agent=mp allowed_tools=[]` (read-only)
- **AG**: `council_request agent=ag cwd=<relevant_repo>` with "READ-ONLY" in prompt
- **XAI**: `council_request agent=xai` — embed full context in prompt (no reliable file access)
- **DeepSeek** (when participating): `council_request agent=deepseek mode=review` — direct API today, `read_only=true` enforced during eval window. Open-ended question authoring will fail strict review schema; use `mode=open_response` after `BQ-COUNCIL-DISPATCH-WRAPPER-RELAXED-MODE` Gate 2 ships, OR file separate BQ for direct-API bypass with rationale (S514 pattern)

### Phase 2: Collection & Synthesis

Vulcan collects all responses and presents them to Max as a synthesis:
1. **Where all agents agree** — convergent findings
2. **Each agent's key differentiator** — unique insights per agent
3. **Key disagreements** — formatted as a comparison table
4. **Vulcan's assessment** — which positions are strongest and why

Do NOT editorialize heavily. Present the agents' positions faithfully.

### Phase 3: Cross-Pollination (Optional)

If Max wants consensus or if disagreements are significant:
1. Vulcan builds a cross-pollination bundle containing all independent assessments
2. Each agent receives: the original prompt + all assessments + instruction to respond to specific points
3. Agents submit final positions with explicit agreement/disagreement flags

Cross-poll prompt structure:
```
CROSS-POLLINATION — {Title}

You previously assessed this topic. Here are all independent assessments:

## MP Assessment
{mp_content}

## AG Assessment
{ag_content}

## XAI Assessment
{xai_content}

Review the other assessments. Respond with:
1. Points you agree with (cite which agent)
2. Points you disagree with (cite which agent, explain why)
3. Your revised position (if changed)
4. Remaining disagreements that cannot be resolved
```

### Phase 4: Consensus or Decision Record

Vulcan synthesizes final positions into one of:
- **Consensus** — all agents converge on the same recommendation
- **Majority + Dissent** — 2/3 agree, one dissents (record the dissent)
- **No Consensus** — fundamental disagreement, escalate to Max for decision

Record the outcome in Living State as a `decision:` entity.

## Tool: `council_hall`

The `council_hall` MCP tool automates state tracking for deliberation sessions.

### Actions

| Action | Purpose |
|--------|---------|
| `start` | Create a new deliberation session |
| `status` | Check current phase and who has responded |
| `record_response` | Store an agent's assessment for any phase |
| `get_cross_poll_bundle` | Build the cross-pollination prompt after Phase 1 |
| `summarize` | Compute consensus after Phase 3 |

### Typical Flow

```
1. council_hall action=start topic="..." prompt="..." agents=["mp","ag","xai"]
   → Returns deliberation_id

2. council_request agent=mp task="..." (same prompt)
   council_request agent=ag task="..." (same prompt)  
   council_request agent=xai task="..." (same prompt)

3. [Collect responses]
   council_hall action=record_response deliberation_id=X agent=mp content="..."
   council_hall action=record_response deliberation_id=X agent=ag content="..."
   council_hall action=record_response deliberation_id=X agent=xai content="..."

4. [Present synthesis to Max]

5. [If cross-poll requested]
   council_hall action=get_cross_poll_bundle deliberation_id=X
   → Use bundle in new dispatch to each agent

6. council_hall action=summarize deliberation_id=X
```

### State Storage

Deliberation state is stored in Living State at `council:hall:{deliberation_id}`:
- `topic`: The deliberation question
- `prompt`: The original prompt sent to all agents
- `agents`: List of participating agents
- `phase`: Current phase (independent → cross_poll_ready → cross_poll → consensus_pending → complete)
- `responses.independent.{agent}`: Each agent's Phase 1 response
- `responses.cross_poll.{agent}`: Each agent's Phase 3 response
- `consensus`: Final outcome (consensus/majority/no_consensus)
- `session_id`: KD session that initiated the deliberation

## When to Use Council Hall

| Scenario | Use Council Hall? |
|----------|-------------------|
| Strategy/GTM decisions | ✅ Yes |
| Architecture design choices | ✅ Yes |
| Gate reviews (Gate 1-3) | ❌ No — use existing gate process |
| Code audits | ❌ No — MP mandatory, others optional |
| Quick factual questions | ❌ No — single agent sufficient |
| Threat modeling | ✅ Yes |
| Naming/branding decisions | ✅ Yes |
| Process/policy design | ✅ Yes |

## Anti-Patterns

- **Pre-assigning roles** ("MP, you're the builder; XAI, you're the challenger") — biases output
- **Excluding agents without reason** — all three should participate in strategy discussions
- **Skipping independent phase** — showing one agent's answer to another before they've formed their own view
- **Over-editorializing synthesis** — Vulcan should present faithfully, not rewrite positions
- **Using Council Hall for code reviews** — existing gate process is better suited

## Future: Redis Streams Upgrade

When local Redis is available on Titan-1 (or Railway Redis is exposed), the transport layer can be upgraded:
- `council:dispatch` stream for task distribution
- `council:responses` stream for agent submissions  
- `council:cross-poll` stream for Phase 3
- Consumer groups per agent for durable delivery
- This eliminates manual Vulcan polling and enables true async deliberation

For now, Vulcan orchestrates manually via `council_request` dispatches + Living State for state tracking.
