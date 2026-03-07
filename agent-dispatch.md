# Agent Dispatch

## What it does

Routes tasks to the Council of Models (AG, MP, XAI) and Claude Code for builds.

## Agents

| Agent | Model | Tool | Default behavior |
|-------|-------|------|------------------|
| AG | Gemini 3 Pro | `call_ag` | Defaults to ACTION — treats every task as build order. Add "READ-ONLY" for non-build tasks |
| MP | GPT-5.4 Pro | `call_mp` | Analysis and review. Has MCP tools. |
| XAI | Grok 4.1 | `call_xai` | Architecture review, challenging assumptions |
| CC | Claude Opus 4.6 | `call_claude_code` | Full filesystem builds, multi-file refactors |

## call_mp routing (as of S223)

```
call_mp dispatched
  → Try Codex CLI first (gpt-5.4-pro-2026-03-05)
  → Codex CLI fails (ChatGPT account doesn't support gpt-5.4-pro)
  → Falls back to MPClient API (Responses API with OpenAI API key)
  → MPClient succeeds with gpt-5.4-pro-2026-03-05
```

**Known issue:** Recovery cache stale enforcement (30 call limit) can block MP's MCP tool calls when MP uses tools heavily. This caused the S223 audit to route to CC instead.

## Council gates

| Gate | When | Who reviews |
|------|------|------------|
| Gate 1 (Design) | Before build | All 4 voters |
| Gate 2 (Spec) | Before build | All 4 voters |
| Gate 3 (Audit) | After build | Min 2 reviewers |

- 3/4 majority for standard items
- 4/4 unanimous for security, auth, payments, money flows

## AG safety

- AG defaults to action — every task treated as build order
- Non-build requests MUST include: "READ-ONLY — DO NOT modify any files"
- Always `git diff --stat` after AG tasks
- 2-Strike rule: stop after 2 fails, consult

## CC builds

- Auto-push to main after tests pass
- Use `dispatch_build` for background, `call_claude_code` for foreground
- `run_background` does NOT inherit PATH — always prefix with `export PATH="/opt/homebrew/bin:$PATH"`

