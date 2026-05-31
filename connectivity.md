# Connectivity Layer

**Status:** CURRENT — live-verified 2026-05-31 (S738.w, Mars) against Titan-1.
**Owner:** SysAdmin agent / Council instances.
**Last updated:** 2026-05-31.

## What this covers

The end-to-end network path that lets Claude instances (Vulcan, Mars) on claude.ai
reach the Koskadeux MCP gateway on Titan-1, plus the local-area and tailnet topology
that the two physical machines (Mac Studio + laptop) sit on. This is the connectivity
overview; the Cloudflare-specific detail lives in `cloudflare-and-dns.md` and the
gateway/proxy internals live in `mcp-gateway.md`. This doc is the canonical answer to
"how do the machines talk to each other and to Claude, and where is it redundant."

## Physical & network topology

One site, one local ethernet, one internet uplink:

| Element | Value (verified 2026-05-31) |
|---|---|
| Workhorse | Mac Studio, serial **G6XQC2KL44** — the machine the team calls **"Titan-1"** |
| LAN interface | `en0`, **192.168.1.192/24**, status active (wired ethernet) |
| LAN gateway/router | **192.168.1.1** |
| Public WAN IP | **79.154.174.218** (single uplink; all egress + all ingress tunnels ride this one link) |
| LAN neighbours seen | ~8 hosts on 192.168.1.0/24 (router + several devices incl. the laptop) |

There is exactly **one internet uplink** for the site. Every path below — the Cloudflare
tunnel, the Tailscale connections, and any laptop traffic — shares that single link.
That shared link is the dominant common-failure-domain (see Redundancy analysis).

## Tailnet node map (READ THIS — the names are inverted)

The Tailscale node names do **not** match the team's machine names. This has caused
repeated confusion:

| Tailscale node name | Tailscale IP | Physical machine | Role |
|---|---|---|---|
| **`Koskadeux (10)` / `koskadeux-10`** | 100.95.61.121 | **Mac Studio (Titan-1, G6XQC2KL44)** | Runs the gateway, cloudflared, Tailscale Funnel. THE workhorse. |
| **`titan-1`** | 100.108.49.1 | **the laptop** (macOS; team serial HY769XY4QJ) | SSH target only; NOT the machine called Titan-1. |
| `localhost` / `iphone172` | 100.71.214.47 | Max's iPhone | — |
| `funnel-ingress-node` ×~24 | fd7a:115c:… (IPv6) | Tailscale's own Funnel edge nodes | Infrastructure; appear because Funnel is enabled. |

**Trap:** the node literally named `titan-1` is the laptop. The machine you call Titan-1
is the node `koskadeux-10`. Renaming the laptop node (e.g. to `laptop` / `macbook`) is a
recommended cleanup; until then, always map by Tailscale IP, not by node name.

## The two public ingress paths to the MCP gateway

Both of these are live **simultaneously** and both terminate at the **same** local origin
`http://localhost:8767` (the gateway proxy, PID family `com.koskadeux.gateway` → forwards
to the real handler on :8765):

| Path | Public URL | Mechanism | Status |
|---|---|---|---|
| **Cloudflare Tunnel** (PRIMARY) | `https://mcp.ai.market` | `cloudflared tunnel run koskadeux` (UUID `007ddc34-de07-474c-adbc-a648663b9c78`), config `~/.cloudflared/config.yml`, ingress → `localhost:8767`, `/api/admin/*` blocked at the edge (404) | **Live. This is the path Claude uses** — the claude.ai MCP connector points at `https://mcp.ai.market`. Verified: the only established connection to :8767 right now is cloudflared. |
| **Tailscale Funnel** (PARALLEL) | `https://koskadeux-10.tail30cd96.ts.net` | `tailscale funnel` / `serve` → `localhost:8767` | **On, but idle** — a second public exposure of the same gateway. Not currently wired as Claude's failover. |

So the long-running "is it Cloudflare or Tailscale?" doc contradiction resolves as:
**both are running; Cloudflare is the active transport, Tailscale Funnel is a parallel
exposure of the same origin.** Tailscale's load-bearing distinct value is the SSH backup
admin path (below), not ingress failover.

## Redundancy analysis — are Cloudflare and Tailscale redundant?

**Partly, and NOT against the failure you actually see.**

- **Redundant at the public edge:** two independent vendors (Cloudflare anycast vs
  Tailscale Funnel edge), different DNS, different global networks. A Cloudflare-edge
  regional outage would not take down the Tailscale Funnel URL.
- **NOT redundant downstream:** both paths converge on the **same gateway process
  (:8767)**, the **same Mac Studio**, and the **same single WAN uplink**. A blip in the
  gateway, the Mac, the router, or the ISP link takes out **both at once**.
- **This explains the correlated glitches.** When Claude↔MCP glitches at the same moment
  as laptop↔Titan-1, the common cause is almost always the shared local uplink / router:
  cloudflared's outbound tunnel AND the laptop's Tailscale path BOTH ride that one link
  (the laptop link is relay-routed over the WAN today — see next section), so they drop
  together. The two "redundant" paths are not independent at the layer that fails most.

To get real ingress redundancy you would need Claude pointed at a failover URL on a
*different* uplink (not just a second tunnel on the same link), or a second WAN uplink
on the Mac Studio. Today neither exists.

## Same local segment — are we tunnelling traffic that should stay on the wire?

**Yes, currently the laptop↔Mac-Studio link is taking the long way around.**

The laptop (Tailscale node `titan-1`, 100.108.49.1) reaches the Mac Studio over Tailscale
via a **DERP relay in Madrid** — it is **not** a direct connection and advertises **no LAN
endpoint** (no 192.168.x candidate). The Mac Studio itself does advertise its LAN endpoint
(`192.168.1.192:41641`). If the two machines are on the same ethernet segment (the Mac
Studio is on 192.168.1.0/24), their traffic is detouring out to Madrid and back instead of
crossing the local switch — wasteful on latency/bandwidth and, critically, a **shared
failure point with the Cloudflare path** (same WAN uplink → they fail together).

**Caveat (cannot fully confirm same-segment from Titan-1):** the laptop is not advertising
any 192.168.x endpoint, which is itself the symptom. If it were healthily on the same L2,
Tailscale would normally have found a direct LAN path (`CurAddr` would show 192.168.1.x).
Likely causes of the relay fallback: laptop on Wi-Fi with AP/client-isolation, on a
different subnet/VLAN, or genuinely off-site. **Fix path if same-segment:** put both on the
same L2 with client-isolation off; verify a direct path appears via
`tailscale status` (peer shows `direct 192.168.1.x:port`, not `relay "mad"`).

## Tailscale SSH backup admin path

Tailscale's genuinely load-bearing role here is **out-of-band admin access**, independent
of the Cloudflare tunnel. If the gateway is wedged but the Mac is up, Tailscale SSH reaches
Titan-1 to run `launchctl kickstart -k …` even when `mcp.ai.market` is degraded. This is
the recovery path when the only normal way in (the MCP surface) is down.

## Verification quick reference

    # On Titan-1 (the Mac Studio / node koskadeux-10):
    ioreg -l | grep IOPlatformSerialNumber            # expect G6XQC2KL44
    pgrep -fl cloudflared                              # cloudflared tunnel ... run koskadeux
    cat ~/.cloudflared/config.yml                      # ingress mcp.ai.market -> localhost:8767
    tailscale status                                   # node map; who is direct vs relayed
    tailscale funnel status                            # koskadeux-10...ts.net -> localhost:8767
    lsof -nP -iTCP:8767                                # who is connected to the gateway now
    ipconfig getifaddr en0; route -n get default       # LAN addr + uplink
    curl -s http://localhost:8767/health               # local gateway health
    curl -s -i https://mcp.ai.market/.well-known/oauth-protected-resource   # public path

## Known issues / follow-ups

- **Laptop↔Mac-Studio relayed via Madrid, not direct-LAN** (above). Diagnose same-segment;
  if co-located, fix to a direct LAN path. Removes a needless WAN dependency + the
  correlated-glitch coupling.
- **No true ingress failover.** Cloudflare + Tailscale Funnel share origin + uplink. A
  second uplink, or a Claude-side failover URL on an independent path, is the only thing
  that buys real redundancy. Decision for Max — not yet scoped.
- **Tailnet node naming inverted** (`titan-1` = laptop). Rename to avoid recurring
  confusion.
- **`mcp-gateway.md`** was already corrected upstream (S690 audit H-1/H-5 rewrite, now on
  main): it states cloudflared is the primary transport. This doc is the topology-level
  companion to it and to `cloudflare-and-dns.md`.

## History

- **2026-05-31 (S738.w):** Runbook created. Live-verified the full path: cloudflared
  PRIMARY (mcp.ai.market), Tailscale Funnel parallel/idle, laptop relayed via Madrid DERP
  (no direct LAN), single WAN uplink as common-failure-domain, tailnet node-name inversion.
  Resolves the Cloudflare-vs-Tailscale ambiguity that recurred across mcp-gateway.md.

## References

- `cloudflare-and-dns.md` — Cloudflare zones, Workers, and the mcp.ai.market tunnel detail.
- `mcp-gateway.md` — gateway/proxy internals, restart, session boot gate.
- `config:resource-registry` (Living State) — canonical service/path registry.

## Discipline

Keep this current whenever the transport, uplink, or tailnet topology changes. Re-verify
with the Verification quick reference block; do not edit from memory. If a change touches
the public path, update `cloudflare-and-dns.md` and `mcp-gateway.md` in the same session.
