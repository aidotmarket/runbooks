# RTK Token Optimization

CLI proxy that reduces LLM token consumption by 60-90% on common dev commands. Intercepts shell commands from Council agents (CC, AG, MP) and compresses output before it hits their context windows.

**Repo:** https://github.com/rtk-ai/rtk
**Last verified:** 2026-07-15 (S1227)

## Host Observations

| Host | S1227 observation | Codex global configuration | Telemetry configuration |
|---|---|---|---|
| maxbookpro | Verified RTK v0.43.0, installed via Homebrew | `~/.codex/AGENTS.md` contains the RTK rule inline; `~/.codex/RTK.md` is the canonical global reference | Disabled in `~/Library/Application Support/rtk/config.toml`; no `~/.zshrc` override |
| Titan-1 | Observed RTK v0.34.3 by the S1227 builder | `~/.codex/AGENTS.md` still uses the legacy `@RTK.md` include | A `~/.zshrc` telemetry override exists |

These paths are host-local. For Codex configuration on either host, inspect
that host's home directory; do not look for the global `AGENTS.md` or `RTK.md`
in the current project repository.

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
- maxbookpro: `~/.codex/AGENTS.md` contains the RTK instructions directly;
  `~/.codex/RTK.md` is the canonical global reference copy.
- Titan-1: `~/.codex/AGENTS.md` still uses `@RTK.md`. This legacy include is
  known configuration debt and is not changed by this docs-only fold.
- These are home-directory global configuration paths on each host. Inspect
  the active host's home directory, not the current project repository.
- Note: Codex integration is instruction-based (not hook-based). MP reads AGENTS.md and prefixes commands with `rtk` when appropriate. Less reliable than CC/AG hooks.

### Vulcan — Path-dependent
- Direct Codex Desktop shell commands use RTK through the global Codex
  instructions.
- ai.market `shell_request` output comes through the MCP gateway as JSON, so
  RTK does not intercept that path.

## Configuration

### Telemetry

On maxbookpro, telemetry is disabled in RTK config:

```toml
# ~/Library/Application Support/rtk/config.toml
[telemetry]
enabled = false
```

No separate `~/.zshrc` override is used on maxbookpro. Titan-1 has a
`~/.zshrc` telemetry override; inspect it on Titan-1 when troubleshooting that
host.

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
MP's integration is instruction-based via the host's global AGENTS.md. Always
inspect the active host's home directory, not the current project repository.

#### maxbookpro

1. Check `~/.codex/AGENTS.md` contains the RTK rule inline, including the
   instruction to prefix shell commands with `rtk`.
2. Check the canonical global reference at `~/.codex/RTK.md` agrees with the
   inline rule.
3. Check telemetry is disabled in
   `~/Library/Application Support/rtk/config.toml` and that no `~/.zshrc`
   override has been introduced.
4. Restart Codex after correcting the global configuration.

#### Titan-1

1. Check `~/.codex/AGENTS.md` and its legacy `@RTK.md` include from Titan-1's
   home directory. Do not search for the include in the project repository.
2. Check the existing `~/.zshrc` telemetry override alongside Titan-1's RTK
   config.
3. Treat the legacy include as remaining configuration debt; this docs-only
   fold does not authorize changing Titan-1 configuration.
4. Restart Codex only after a separately authorized configuration correction.

On both hosts, MP compliance depends on the model following instructions and
is not guaranteed.

## Decision Log

- **S1227 (2026-07-15):** Verified RTK v0.43.0 on maxbookpro. Replaced the
  Codex `@RTK.md` include with the inline rule in the home-directory global
  `~/.codex/AGENTS.md`; retained `~/.codex/RTK.md` as the canonical global
  reference copy. Verification covered `rtk --version`, `rtk git status`, the
  global reference file, and `rtk gain --history`. Confirmed telemetry is
  disabled in RTK config without a separate zshrc override. The S1227 builder
  also observed RTK v0.34.3 on Titan-1, where `~/.codex/AGENTS.md` still uses
  `@RTK.md` and a `~/.zshrc` telemetry override exists. Titan-1's legacy include
  remains configuration debt; this docs-only fold did not change Titan-1.
- **S388 (original Titan-1 rollout):** Recorded RTK v0.34.3 on
  Titan-1, enabled for CC, AG, and MP, with telemetry disabled and tee enabled
  for failure output recovery. Rationale: 60-90% token savings on agent shell
  commands, especially pytest and git operations during AIM-NODE-CORE builds.
