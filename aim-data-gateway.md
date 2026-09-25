---
title: AIM Data gateway — operations
owner: vulcan
last_verified: '2026-09-25'
aliases: [aim-gateway, AIM Data gateway, gateway canary, egress canary, gw-canary]
error_signatures: [Cloudflare GraphQL error, Cloudflare zone unavailable, Cloudflare DNS analytics unavailable, invalid canary label]
---

# AIM Data gateway — operations

The AIM Data gateway is the small open-source Go service that sellers run with Docker to list and serve files from their own infrastructure. It replaces legacy AIM Data (`aim-data.md`), which is frozen. Design authority: `specs/BQ-AIM-DATA-GATEWAY-S1741-GATE1.md` and `specs/BQ-AIM-DATA-GATEWAY-S1741-GATE2.md`. Build record: Living State `build:bq-aim-data-gateway-rebuild-s1741`.

This page covers what is live today: the repository and release, and the egress canary (DNS records, the backend's server-side check and its credentials). Pairing configuration, the `gateway-signer` service and the production KMS keys are not provisioned yet; add them here when they are.

## Repository and release

- Repo: `aidotmarket/aim-data-gateway` (public), checkout `/Users/max/Projects/ai-market/aim-data-gateway` (fetch and read `origin/main`; the local `main` branch there can be stale).
- Image: `ghcr.io/aidotmarket/aim-gateway`, published by `.github/workflows/release.yml` on a `v*` tag. The workflow builds twice and compares digests, pushes, checks an anonymous pull, signs with cosign keyless and attaches SBOM and provenance. The binary version comes from the tag.
- Current release: `v0.1.1`. `v0.1.0` is a superseded prerelease (it reported `0.1.0-dev`).

## Egress canary

The gateway checks that the seller's deny-all egress is really in place (GATE2 §6.7). Every hour and on every reconnect it resolves `<16 hex>.gw-canary.ai.market` and opens TCP to `egress-canary.ai.market:443`. Both must fail. It reports the result in a signed `canary_result`.

### DNS records (Cloudflare zone ai.market, zone id `f82ac6762af544d71e8ad5eb3d7fca0c`)

| Name | Type | Content | Proxied |
| --- | --- | --- | --- |
| `*.gw-canary.ai.market` | A | `192.0.2.1` | yes |
| `egress-canary.ai.market` | A | `192.0.2.1` | yes |

The origin `192.0.2.1` is deliberately unroutable (TEST-NET-1). Proxying makes Cloudflare answer every label with its edge addresses and accept TCP on 443, so any gateway with open egress sees an answer and a connection. Do not unproxy these records or point them at a real origin.

### Server-side check (backend)

- Code: `app/services/aim_gateway_canary_cf.py` (adapter) and `_correlate_canary_logs()` in `app/tasks/aim_gateway_door.py`. The adapter is installed only when all three settings are set: `GATEWAY_CANARY_CF_API_TOKEN`, `GATEWAY_CANARY_CF_ZONE_ID` (`f82ac6762af544d71e8ad5eb3d7fca0c`) and `GATEWAY_CANARY_ZONE` (`gw-canary.ai.market`). Without it, every gateway stays `unknown` and cannot publish.
- Source: Cloudflare GraphQL `dnsAnalyticsAdaptiveGroups`, filtered by `queryName_in`. The worker waits 3 minutes after a result arrives (analytics lag) and queries from 5 minutes before receipt up to the time of the query.
- **Sampling (Amendment C, Max decision dde536b1):** Cloudflare keeps 1 in 10 DNS queries (`sampleInterval` 10). A hit means `open`. A miss counts as "no server-side hit", not as proof. The expected detection rate for a gateway that lies is about 10% per hourly canary, about 92% within 24 hours.
- Token: Infisical project `ai-market-backend`, env `prod`, key `GATEWAY_CANARY_CF_API_TOKEN` (requested from Max on 2026-09-25; until it exists, the general `CLOUDFLARE_API_TOKEN` in the same project, which has Analytics Read, was used for verification). Scope: Zone → Analytics → Read on ai.market only. Only a human creates or rotates this token, in the Cloudflare dashboard; agents never mint or copy it.

### Verify (headless, on Titan-1)

The sysadmin Infisical token lives at `~/.config/infisical/sysadmin-token`. Never print a token.

```bash
export PATH=/opt/homebrew/bin:$PATH
JWT=$(tr -d '\r\n' < ~/.config/infisical/sysadmin-token)
CFT=$(infisical secrets get GATEWAY_CANARY_CF_API_TOKEN --projectId bd272d48-c5a1-4b52-9d24-12066ae4403c \
  --env prod --domain https://secrets.ai.market --token "$JWT" --plain --silent | tr -d '\r\n')
L=$(openssl rand -hex 8); dig +short @1.1.1.1 $L.gw-canary.ai.market   # must answer (proxied)
# analytics for the zone, last 30 min: expect avg.sampleInterval 10
S=$(date -u -v-30M +%Y-%m-%dT%H:%M:%SZ); U=$(date -u +%Y-%m-%dT%H:%M:%SZ)
curl -s https://api.cloudflare.com/client/v4/graphql -H "Authorization: Bearer $CFT" -H 'Content-Type: application/json' \
  -d '{"query":"{viewer{zones(filter:{zoneTag:\"f82ac6762af544d71e8ad5eb3d7fca0c\"}){dnsAnalyticsAdaptiveGroups(limit:20,filter:{datetime_geq:\"'$S'\",datetime_leq:\"'$U'\",queryName_like:\"%gw-canary.ai.market\"}){count avg{sampleInterval} dimensions{queryName}}}}}"}'
```

Because of sampling, a single fresh label is often missing. To prove the pipeline works, resolve about 20 fresh labels and expect a few to show up within a few minutes (S1751: 4 of 20 after 6 minutes).

## When it breaks

- `Cloudflare GraphQL error: ... authentication` or an HTTP 401/403 in the correlation worker log: the token is missing Analytics Read or was revoked. Ask Max to fix the token in Cloudflare and Infisical, then redeploy the backend. While it is broken, every gateway falls to `unknown` (fail-closed), so publishing and new permissions stop.
- `Cloudflare zone unavailable`: `GATEWAY_CANARY_CF_ZONE_ID` is wrong or the token is not scoped to ai.market.
- All gateways `unknown` although they report `closed`: check that all three settings are set on the backend and the worker (Celery beat runs correlation every 300 s).
- A gateway flips to `open` while it reports `closed`: this is the check working. The seller's egress is open. The gateway stays unsupported until its canary is clean.
