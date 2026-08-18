# CC machine identity (council reviewer credential)

## A. Purpose
Stop the recurring destruction of Max's Claude login and keep the CC council reviewer dispatchable without any human credential. Owns: how CC authenticates, how the key rotates, and how to diagnose credential failures on the CC path.

## B. The design (S1573)
CC's primary identity is a dedicated Anthropic **API key**, not an OAuth login. OAuth grants on one account revoke each other server-side when siblings are re-issued (evidence: 19 empty-credential stubs in `~/.claude-koskadeux` 13–18 Aug 2026, every one written after the server refused a refresh as *revoked*; both the "isolated" profile and Max's interactive login were the same account, max@kisa.cat). API keys have no refresh rotation and no sibling-grant lifecycle, which removes the failure class regardless of what else is signed in on the machine.

- Canonical secret: Infisical `koskadeux-mcp` / `prod` / `CC_COUNCIL_ANTHROPIC_API_KEY`.
- Cache fallback: `/Users/max/koskadeux-state/secrets/cc-council-api-key` (0600), refreshed on every successful Infisical fetch; keeps dispatch working when the secret store is down.
- Code: `koskadeux-mcp/cc_profile.py` (`council_api_key()`, `apply_to_env`). The profile dir `~/.claude-koskadeux` is still applied in API-key mode so CC never reads the interactive config. The OAuth profile remains as fallback only.
- As of S1573 the slot is **seeded with the shared backend key**. Rotate to a dedicated console key (console.anthropic.com → new key → paste into the Infisical secret) to complete identity separation. Rotation is one Infisical value change; no code, no restart.

## C. Failure / symptom table
| Symptom | Meaning | Action |
|---|---|---|
| `401 OAuth access token has been revoked` in `council/cc/launcher-*.log` | OAuth fallback in use and its grant was revoked | Confirm `CC_COUNCIL_ANTHROPIC_API_KEY` resolves (Infisical up? token file `~/.config/infisical/sysadmin-token` valid? cache file present?); API-key mode bypasses OAuth entirely |
| `.credentials.json` empty-token stub in `~/.claude-koskadeux` | Server refused a refresh; CLI blanked the file. Symptom, not cause | Launcher auto-heals (renames stub). No action if API-key mode active |
| `invalid x-api-key` / `authentication_error` on CC runs | The API key itself is bad or was rotated upstream | Update the Infisical secret; delete the cache file to force re-fetch |
| CC dispatch refuses with "profile not provisioned" | Both key resolution and OAuth profile unavailable | Restore Infisical reachability or re-seed the cache file; last resort `scripts/setup_cc_profile.sh` |
| Max's interactive Claude login dies after machine re-provisioning | An OAuth login was run for the machine again | Don't. Machine identity is the API key; never `claude login` for dispatch |

## D. Verification
`python3 -c "import sys; sys.path.insert(0,'/Users/max/koskadeux-mcp'); import cc_profile; print(cc_profile.status())"` — expect `council_api_key: True`. End-to-end: dispatch `council_request(agent=cc, mode=open_response, task='Reply with exactly: COUNCIL-CC-OK')`.

## E. Scope boundaries
Kimi and GLM have their own transports (see `infra:council-comms`). The same one-account defect exists on the OpenAI side (MP builder + GLM on `/Users/max/.codex/auth.json`) — tracked under BQ-GLM-CODEX-TRANSPORT-MIGRATION-S1566; apply the same identity-separation principle there when that work resumes.
