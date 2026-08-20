# CC machine identity (council reviewer credential)

## A. Purpose
Stop the recurring destruction of Max's Claude login and keep the CC council reviewer dispatchable without any human credential. Owns: how CC authenticates, how the key rotates, and how to diagnose credential failures on the CC path.

## B. The design (S1573, causal story corrected S1582 per T-2026-000686)
**The Council panel path runs CC on the OAuth machine profile, on Max's plan, by Max's directive.** `scripts/council_dir.py:_cc_env` deliberately strips `ANTHROPIC_API_KEY` (and every override var) from the child environment; that stripping is correct and must not be "fixed". The dedicated API key below remains live only for **non-panel** headless dispatches through `claude_code_client._build_env`.

**Corrected root cause of the recurring 401s (S1581 evidence, T-2026-000686).** The S1573 theory — sibling OAuth grants revoking each other server-side — is contradicted by direct evidence and is retired. Nothing was ever revoked: the config-scoped Keychain credential (`Claude Code-credentials-2d3f080c`) was valid and unexpired through every incident. The real cause was `scripts/setup_cc_profile.sh`: when its interactive `claude login` is abandoned before browser completion, the CLI leaves `~/.claude-koskadeux/.credentials.json` with EMPTY accessToken/refreshToken strings (metadata populated). Claude Code prefers that file over the Keychain, and empty tokens return a 401 that reads exactly like revocation. 23 quarantined stubs 13–20 Aug match ~18 setup-script re-runs in shell history: CC failed, an operator re-ran the setup script to repair it, the abandoned login wrote a fresh stub, and the stub caused the next failure. The repair was the cause. The S1532 profile isolation itself was correct and holds.

- Canonical secret: Infisical `koskadeux-mcp` / `prod` / `CC_COUNCIL_ANTHROPIC_API_KEY`.
- Cache fallback: `/Users/max/koskadeux-state/secrets/cc-council-api-key` (0600), refreshed on every successful Infisical fetch; keeps dispatch working when the secret store is down.
- Code: `koskadeux-mcp/cc_profile.py` (`council_api_key()`, `apply_to_env`). The profile dir `~/.claude-koskadeux` is still applied in API-key mode so CC never reads the interactive config. The OAuth profile remains as fallback only.
- As of S1573 the slot is **seeded with the shared backend key**. Rotate to a dedicated console key (console.anthropic.com → new key → paste into the Infisical secret) to complete identity separation. Rotation is one Infisical value change; no code, no restart.

## C. Failure / symptom table
| Symptom | Meaning | Action |
|---|---|---|
| `401 OAuth access token has been revoked` in `council/cc/launcher-*.log` | Almost always an empty-token `.credentials.json` stub shadowing a VALID Keychain credential (T-2026-000686), not real revocation | Check `~/.claude-koskadeux/.credentials.json` for empty accessToken/refreshToken; `cc_profile.heal_empty_stub()` retires it (runs in `apply_to_env`). Do NOT re-run `setup_cc_profile.sh` as a reflex — an abandoned login run is what writes the stub |
| `.credentials.json` empty-token stub in `~/.claude-koskadeux` | An abandoned interactive `claude login` (usually from `setup_cc_profile.sh`) wrote a placeholder mid-flight. This IS the cause of the panel 401s, not a symptom of revocation | Launcher auto-heals (renames stub). If stubs keep appearing, find and finish or kill the abandoned `claude login`; do not keep re-running the setup script |
| `invalid x-api-key` / `authentication_error` on CC runs | The API key itself is bad or was rotated upstream | Update the Infisical secret; delete the cache file to force re-fetch |
| CC dispatch refuses with "profile not provisioned" | Both key resolution and OAuth profile unavailable | Restore Infisical reachability or re-seed the cache file; last resort `scripts/setup_cc_profile.sh` |
| Max's interactive Claude login dies after machine re-provisioning | Concurrent refresh race on one shared credential (the original S1532 defect) | The isolated machine profile prevents this; keep the profiles separate. If the machine profile needs re-provisioning, complete the browser login in one sitting — an abandoned run leaves a 401-causing stub |

## D. Verification
`python3 -c "import sys; sys.path.insert(0,'/Users/max/koskadeux-mcp'); import cc_profile; print(cc_profile.status())"` — expect `council_api_key: True`. End-to-end: dispatch `council_request(agent=cc, mode=open_response, task='Reply with exactly: COUNCIL-CC-OK')`.

## E. Scope boundaries
Kimi and GLM have their own transports (see `infra:council-comms`). The same one-account defect exists on the OpenAI side (MP builder + GLM on `/Users/max/.codex/auth.json`) — tracked under BQ-GLM-CODEX-TRANSPORT-MIGRATION-S1566; apply the same identity-separation principle there when that work resumes.
