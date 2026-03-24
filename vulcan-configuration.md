# Vulcan Configuration — Context Hydration & Memory Architecture

## Overview
Vulcan (Claude Opus) operates in Claude.ai with a Koskadeux MCP server connection. Context is hydrated through multiple layers at different stages. This runbook defines **what goes where** to prevent memory bloat and duplication.

## The Principle
> Memory edits = behavioral rules and hard-won traps ONLY.
> Specific details (env vars, commit SHAs, format specs, access methods) belong in Living State, runbooks, or HANDOFF.md.

This was established in a Council session (S64, Jan 2026) and enforced through audits in S201, S208, S268, and S342.

## Context Layers (in injection order)

### Layer 0 — Memory Edits (Anthropic cloud, always injected)
- **Max slots:** 30 (500 chars each)
- **Target:** ≤5 entries
- **What belongs here:** Behavioral rules that Vulcan repeatedly forgets. Hard-won traps. Pointers to WHERE to find information, not the information itself.
- **What does NOT belong:** Specific config values, commit SHAs, env vars, file formats, access methods, model version numbers, tool-specific syntax.
- **Managed via:** `memory_user_edits` tool (view/add/remove/replace)
- **Audit cadence:** Every ~50 sessions or when slots exceed 8

### Layer 1 — Claude.ai Project Instructions (always injected)
- **Location:** Claude.ai project settings (manually edited by Max)
- **What belongs here:** MCP tool definitions, available skills, network config, filesystem config
- **Not editable by Vulcan** — Max maintains this

### Layer 2 — Session Boot (injected by kd_session_open)
- **CORE.md** — Agent constitution, enforcement rules, Council protocol, current priorities
- **HANDOFF.md** — Previous session context, pending items, key decisions, commits, bugs
- **BQ Status** — Dashboard of all build queue items from Living State
- **Service Health** — MCP, allAI, AG, XAI status checks
- **Location:** CORE.md in `ai-market-backend/docs/core/`, HANDOFF at `/var/tmp/koskadeux/HANDOFF.md`

### Layer 3 — Living State (on-demand via state_get)
- **Infrastructure details:** `infra:council-comms`, `infra:railway`, `infra:titan-1`, `infra:github`, `infra:briefing`
- **Build status:** `build:bq-*` entities with gate status, notes, design decisions
- **Config:** `config:resource-registry` for file/service/tool locations
- **What belongs here:** All operational details — env vars, access methods, model versions, service configs, agent quirks. This is where details removed from memory edits should live.

### Layer 4 — allAI (Qdrant, on-demand via allai_search)
- **Session logs, decisions, architecture knowledge**
- **Probabilistic retrieval** — good for "why did we do X?" not for "what is the current state of X?"
- **Key limitation:** Returns semantically similar results, not necessarily current truth. Living State is SSOT.

### Layer 5 — Runbooks (on-demand, in GitHub)
- **Location:** `aidotmarket/runbooks` repo
- **What belongs here:** Operational procedures, diagnostic checklists, recovery steps, integration docs
- **How to find:** `github:get_file_contents` on the runbooks repo, or search via `github:search_code`

### Layer 6 — On-demand docs (read when needed)
- `docs/core/BUSINESS-CONTEXT.md` — Gate 1 reviews, product decisions
- `docs/core/PROTOCOLS.md` — Build workflow, CCP mechanics, cross-review rules
- `docs/core/INFRASTRUCTURE.md` — Deploy tasks, service configs

## Decision Tree: Where Does This Go?

```
Is it a behavioral rule Vulcan keeps forgetting?
  YES → Memory edit (Layer 0)
  NO ↓

Is it a current operational fact (env var, model version, access method)?
  YES → Living State infra entity (Layer 3)
  NO ↓

Is it a procedure or diagnostic checklist?
  YES → Runbook in GitHub (Layer 5)
  NO ↓

Is it a design decision or specification?
  YES → BQ entity in Living State (Layer 3) or spec file in backend repo
  NO ↓

Is it context for the next session?
  YES → HANDOFF.md (Layer 2)
  NO ↓

Is it historical context ("why did we do X")?
  YES → allAI will have it from session logs (Layer 4)
  NO → Probably doesn't need to be stored
```

## Anti-Patterns (Things That Keep Happening)

1. **Cramming details into memory edits** — Vulcan adds env vars, commit SHAs, format specs to memory slots. These fill up fast and duplicate Living State. FIX: Memory edits point to where info lives, never contain the info.

2. **Storing tool syntax in memory** — Specific API calls, CLI commands, SQL queries. These belong in runbooks or Living State. Memory should say "check infra:railway for DB access methods" not list the 3 methods.

3. **Not updating Living State when fixing things** — Vulcan fixes an agent issue but only records it in HANDOFF.md or memory edits. FIX: Always `state_patch` the relevant infra entity with new operational facts.

4. **Redundancy between memory and userMemories** — The auto-generated userMemories blob already contains extensive project context. Memory edits that duplicate it waste slots.

## Current Memory Edits (as of S342)

| # | Category | Content |
|---|----------|---------|
| 1 | Council dispatch | MP default builder, git pull rule, points to infra:council-comms |
| 2 | Gate trap | APPROVED_WITH_MANDATES → must patch gate1 before dispatch |
| 3 | Philosophy | Fix agents systemically, never work around |
| 4 | Execution | 18 calls per interaction, execute the plan, don't pause |
| 5 | Resource discovery | Check Living State → SysAdmin → grep → update registry |

## Audit History

- **S64** (Jan 28) — Three-Layer Memory architecture designed with Council
- **S93** — 7 entries
- **S201** — Hit 30/30, trimmed to 28
- **S208** — Further consolidation, SysAdmin cartographer pattern established
- **S268** — AG + MP full audit, trimmed 12 → 8 → 2 lean entries
- **S325** — Rebuilt to 3 after conversation history cleared
- **S342** — Bloated back to 10 with details, cleaned to 5 with this runbook created

## Related
- `infra:council-comms` — Council agent details, models, quirks, env requirements
- `infra:titan-1` — Local services, LaunchAgents, CLI tools
- `infra:railway` — Railway services, deploy config, DB access methods
- `config:resource-registry` — File paths, tool names, ports, domains
- This runbook: `aidotmarket/runbooks/vulcan-configuration.md`
