# RTK Token Optimization

CLI proxy that reduces LLM token consumption by 60-90% on common dev commands. Intercepts shell commands from Council agents (CC, AG, MP) and compresses output before it hits their context windows.

**Repo:** https://github.com/rtk-ai/rtk
**Installed:** v0.34.3 via Homebrew on Titan-1
**Session:** S388

## What It Does

RTK sits between agent shell calls and the OS. When CC runs `git status`, RTK intercepts it and returns a compressed version (~200 tokens instead of ~2,000). Four strategies: smart filtering, grouping, truncation, deduplication.

Biggest wins for our workflow:
- `pytest` output: ~90% reduction (failures-only on passing runs)
- `git push/commit/add`: ~80-92% reduction (verbose git output → "ok main")
- `cat`/file reads: ~70% reduction (smart filtering)
- `git diff`: ~75% reduction (condensed diffs)

## Agent Configuration

### CC (Claude Code) — PreToolUse hook
- Hook: `~/.claude/hooks/rtk-rewrite.sh`
- Config: `~/.claude/RTK.md`, `@RTK.md` ref in `~/.claude/CLAUDE.md`
- Settings: `~/.claude/settings.json` (hook entry)
- Restart CC after any changes

### AG (Gemini CLI) — BeforeTool hook
- Hook: `~/.gemini/hooks/rtk-hook-gemini.sh`
- Config: `~/.gemini/GEMINI.md`
- Restart Gemini CLI after any changes

### MP (Codex CLI) — AGENTS.md instructions
- Config: `~/.codex/RTK.md`, `@RTK.md` ref in `~/.codex/AGENTS.md`
- Note: Codex integration is instruction-based (not hook-based). MP reads AGENTS.md and prefixes commands with `rtk` when appropriate. Less reliable than CC/AG hooks.

### Vulcan — Not applicable
Vulcan operates via MCP tool calls. shell_request output comes through the MCP gateway as JSON. RTK does not intercept this path.

## Configuration

### Telemetry (disabled)
```toml
# ~/Library/Application Support/rtk/config.toml
[telemetry]
enabled = false
```
Also set in `~/.zshrc`: `export RTK_TELEMETRY_DISABLED=1`

### Tee (full output recovery)
```toml
[tee]
enabled = true
mode = "failures"    # save full output only on failures
max_files = 50
```
When a command fails, RTK saves unfiltered output to `~/.local/share/rtk/tee/`. Agents can read the full output file if the compressed version lacks detail.

## Common Operations

### Check savings
```bash
rtk gain              # summary stats
rtk gain --graph      # ASCII graph (last 30 days)
rtk gain --daily      # day-by-day breakdown
```

### Find missed optimization opportunities
```bash
rtk discover          # commands not going through RTK
rtk discover --all --since 7
```

### Verify installation
```bash
rtk --version
rtk init --show       # shows hook status for all agents
```

### Reinstall/update
```bash
brew upgrade rtk
# Hooks survive upgrades — no re-init needed
```

### Uninstall
```bash
rtk init -g --uninstall     # remove CC hooks
rtk init -g --gemini --uninstall  # remove AG hooks (if supported)
brew uninstall rtk
```

### Exclude commands from rewriting
Edit `~/Library/Application Support/rtk/config.toml`:
```toml
[hooks]
exclude_commands = ["curl", "some-other-command"]
```

## Troubleshooting

### Agent not using RTK
1. Verify hook: `rtk init --show`
2. Restart the agent (CC, AG, or Codex)
3. Test: run `git status` from the agent and check if output is compressed

### RTK stripping too much info
1. Check `~/.local/share/rtk/tee/` for full output on failures
2. For a specific command, bypass RTK: run the raw command directly
3. Use `rtk proxy <command>` for passthrough with tracking only

### MP (Codex) not prefixing with rtk
MP's integration is instruction-based via AGENTS.md. If MP isn't using RTK:
1. Check `~/.codex/AGENTS.md` contains `@RTK.md`
2. Check `~/.codex/RTK.md` exists
3. MP compliance depends on the model following instructions — not guaranteed

## Decision Log

- **S388:** Installed RTK v0.34.3 on Titan-1. Enabled for CC, AG, MP. Telemetry disabled. Tee enabled for failure output recovery. Rationale: 60-90% token savings on agent shell commands, especially pytest and git operations during AIM-NODE-CORE builds.
