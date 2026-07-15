# RTK Token Optimization

CLI proxy that reduces LLM token consumption by 60-90% on common dev commands. Intercepts shell commands from Council agents (CC, AG, MP) and compresses output before it hits their context windows.

**Repo:** https://github.com/rtk-ai/rtk
**Installed:** v0.43.0 via Homebrew on maxbookpro
**Last verified:** 2026-07-15 (S1227)

The Titan-1 v0.34.3 installation recorded in S388 is historical and was not
reverified during S1227.

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
- Inline rule: `~/.codex/AGENTS.md` contains the RTK instructions directly
- Canonical global reference copy: `~/.codex/RTK.md`
- Both files are home-directory global configuration, not repository files.
  Agents must not search for `RTK.md` in the current repository.
- Note: Codex integration is instruction-based (not hook-based). MP reads AGENTS.md and prefixes commands with `rtk` when appropriate. Less reliable than CC/AG hooks.

### Vulcan — Path-dependent
- Direct Codex Desktop shell commands use RTK through the global Codex
  instructions.
- ai.market `shell_request` output comes through the MCP gateway as JSON, so
  RTK does not intercept that path.

## Configuration

### Telemetry (disabled)
```toml
# ~/Library/Application Support/rtk/config.toml
[telemetry]
enabled = false
```
No separate `~/.zshrc` override is used on maxbookpro.

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
rtk gain --history    # recent command savings history
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
MP's integration is instruction-based via the global AGENTS.md. If MP isn't
using RTK:
1. Check `~/.codex/AGENTS.md` contains the RTK rule inline, including the
   instruction to prefix shell commands with `rtk`.
2. Check the canonical global reference copy exists at `~/.codex/RTK.md` and
   agrees with the inline rule.
3. Treat both paths as home-directory global configuration. Do not search for
   `RTK.md` in the current repository and do not rely on an unresolved
   `@RTK.md` include.
4. Restart Codex after correcting the global configuration.
5. MP compliance depends on the model following instructions — not guaranteed.

## Decision Log

- **S1227 (2026-07-15):** Verified RTK v0.43.0 on maxbookpro. Replaced the
  Codex `@RTK.md` include with the inline rule in the home-directory global
  `~/.codex/AGENTS.md`; retained `~/.codex/RTK.md` as the canonical global
  reference copy. Verification covered `rtk --version`, `rtk git status`, the
  global reference file, and `rtk gain --history`. Confirmed telemetry is
  disabled in RTK config without a separate zshrc override.
- **S388 (historical; not reverified in S1227):** Recorded RTK v0.34.3 on
  Titan-1, enabled for CC, AG, and MP, with telemetry disabled and tee enabled
  for failure output recovery. Rationale: 60-90% token savings on agent shell
  commands, especially pytest and git operations during AIM-NODE-CORE builds.
