# Connectivity Layer

**Status:** CURRENT — live-verified 2026-05-31 (S738.w, Mars) against Titan-1 incl. serials + `tailscale whois`.
**Owner:** SysAdmin agent / Council instances.
**Last updated:** 2026-05-31.

## What this covers

How Claude (Vulcan, Mars on claude.ai) reaches the Koskadeux MCP gateway on Titan-1, and
the LAN / tailnet topology the machines sit on. Cloudflare detail lives in
`cloudflare-and-dns.md`; gateway internals in `mcp-gateway.md`. This is the canonical
answer to "how do the machines talk to each other and to Claude, and where is it redundant."

## Physical & network topology

| Element | Value (verified 2026-05-31) |
|---|---|
| Workhorse | Mac Studio, serial **G6XQC2KL44** — the machine the team calls **"Titan-1"** |
| LAN interface | `en0`, **192.168.1.192/24**, wired ethernet |
| LAN gateway/router | **192.168.1.1** |
| Public WAN IP | **79.154.174.218** (single uplink — all egress + the Cloudflare tunnel ride this one link) |
| The laptop | **MAXBOOKPRO-2**, LAN **192.168.1.200** (same ethernet segment as Titan-1) |

One site, one ethernet, one internet uplink. Everything below shares that uplink — it's the
dominant common-failure-domain.

## Tailnet node map (the names mislead — verified by serial + whois)

| Tailscale node | Tailscale IP | Actual machine | Notes |
|---|---|---|---|
| `Koskadeux (10)` / `koskadeux-10` | 100.95.61.121 | **Mac Studio (Titan-1, G6XQC2KL44)** | The live node. Gateway, cloudflared, Funnel. |
| `titan-1` | 100.108.49.1 | **ALSO the Mac Studio (G6XQC2KL44)** — a **stale/duplicate tailnet identity** | NOT a separate machine. SSH to it returns serial G6XQC2KL44; `whois` shows same owner. **Ghost node — cleanup candidate.** |
| `localhost` / `iphone172` | 100.71.214.47 | Max's iPhone (iOS) | — |
| `funnel-ingress-node` ×~24 | fd7a:115c:… | Tailscale's own Funnel edge | Infra; present because Funnel is on. |

**Critical:** the node named `titan-1` is a **duplicate of the Mac Studio**, not the laptop.
**The laptop (MAXBOOKPRO-2) is NOT on the tailnet** — it is reachable only on the local
ethernet (192.168.1.200). The only real tailnet members are the Mac Studio (appearing twice
via the duplicate identity) and the iPhone.

## How the machines actually talk today

- **Claude → MCP gateway:** over **Cloudflare** (`https://mcp.ai.market`, `cloudflared tunnel
  run koskadeux` → `localhost:8767`). This is the live path. **Tailscale Funnel**
  (`koskadeux-10.tail30cd96.ts.net` → same `:8767`) is a parallel, idle public exposure.
- **Laptop ↔ Titan-1 (screen sharing, file sharing, etc.):** over the **local ethernet**
  (both on 192.168.1.0/24), NOT Tailscale — because the laptop isn't on the tailnet. Apple
  Continuity (rapportd, link-local) also runs locally. Confirmed: an active Screen Sharing
  session was observed between Titan-1 and 192.168.1.200 over the LAN.

## Remote access to Titan-1

Titan-1 exposes two remote-admin surfaces, both gated on **being a member of the tailnet**:

- **SSH over Tailscale** — out-of-band admin path; reach Titan-1 to `launchctl kickstart`
  the gateway even when the MCP surface is degraded. Independent of Cloudflare.
- **Apple Screen Sharing (VNC)** — **enabled** on Titan-1: `screensharingd` listens on
  `:5900` (all interfaces, incl. the tailnet IP; verified `100.95.61.121:5900` reachable).
  From a tailnet device: `vnc://100.95.61.121` (or the MagicDNS name if the client has
  Tailscale DNS on). The macOS login password still gates the session.

**To use either of these from another location, the connecting device must be on the
tailnet.** The laptop currently is NOT, so as configured it CANNOT reach Titan-1 remotely —
install + sign in Tailscale (account `max@ai.market`) on the laptop first. On the desk it
works only because both sit on the same LAN.

## Redundancy analysis — are Cloudflare and Tailscale redundant?

**Partly, and NOT against the failure you see.**

- **Redundant at the public edge:** two vendor edges (Cloudflare anycast vs Tailscale Funnel)
  both front the gateway. A Cloudflare-edge regional outage wouldn't kill the Funnel URL.
- **NOT redundant downstream:** both converge on the same gateway process (`:8767`), the same
  Mac, and the same single WAN uplink. A blip in the gateway, the Mac, the local
  router/switch, or the ISP link takes out both at once.
- **Likely cause of correlated glitches:** Claude↔MCP runs out over the WAN uplink
  (Cloudflare); laptop↔Titan-1 runs over the local router/switch. A disturbance in the shared
  local network gear or the uplink can hit both at the same moment. (Note: this is a
  LAN/uplink common-mode — it is NOT a Tailscale relay path, because the laptop isn't on the
  tailnet.) Real ingress redundancy would need a second uplink or a Claude-side failover URL
  on an independent path; neither exists today.

## Verification quick reference

    ioreg -l | grep IOPlatformSerialNumber            # G6XQC2KL44 = Mac Studio/Titan-1
    pgrep -fl cloudflared                              # cloudflared ... run koskadeux (live transport)
    tailscale status                                   # tailnet members; direct vs relay
    tailscale whois <100.x ip>                         # which machine a node really is
    tailscale funnel status                            # koskadeux-10...ts.net -> localhost:8767
    lsof -nP -iTCP -sTCP:LISTEN | grep -E ':5900|cloudflar'  # screensharingd + tunnel
    netstat -an | grep '\.5900 '                       # screen sharing listener (on-demand: may be dormant)
    ipconfig getifaddr en0; route -n get default       # LAN addr + uplink
    curl -s http://localhost:8767/health               # local gateway health

## Known issues / follow-ups

- **Duplicate tailnet node `titan-1` (100.108.49.1)** is a stale second identity of the Mac
  Studio (serial-confirmed). Remove it from the Tailscale admin console to stop the confusion
  (same hazard class as the duplicate MCP connector). Until removed, map nodes by `whois`/serial,
  not by name.
- **Laptop (MAXBOOKPRO-2) is not on the tailnet.** Remote SSH/Screen-Sharing to Titan-1 won't
  work while travelling until Tailscale is installed + signed in on the laptop.
- **No true ingress redundancy.** Cloudflare + Funnel share origin + uplink. A second uplink
  or an independent Claude-side failover URL is the only thing that buys real redundancy.
  Decision for Max — not yet scoped.

## History

- **2026-05-31 (S738.w):** Runbook created, then corrected the same session. Initial draft
  mis-identified the Tailscale node `titan-1` as the laptop and recorded a bogus "laptop
  relayed via Madrid, fixed to direct-LAN" item — that node is actually a duplicate of the
  Mac Studio itself (proven by SSH serial G6XQC2KL44 + `tailscale whois`, no SSH alias). The
  laptop (MAXBOOKPRO-2) is LAN-only and not on the tailnet. Verified: cloudflared PRIMARY,
  Funnel parallel/idle, Screen Sharing enabled (`:5900` reachable on the tailnet IP), single
  WAN uplink as common-failure-domain. Lesson recorded: verify to ground truth (serial/whois),
  not to node names.

## References

- `cloudflare-and-dns.md` — Cloudflare zones, Workers, mcp.ai.market tunnel detail.
- `mcp-gateway.md` — gateway/proxy internals, restart, session boot gate.
- `config:resource-registry` (Living State) — canonical service/path registry.

## Discipline

Keep current whenever transport, uplink, or tailnet topology changes. Verify with the
Verification block — and confirm machine identity by serial/`whois`, never by node name.
