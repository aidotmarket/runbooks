# AIM Node — The Runtime

The universal network client for ai.market. Same codebase, two modes: **provider** (wraps a model/pipeline endpoint, serves it to buyers) and **consumer** (searches marketplace, sends requests via local HTTP proxy). Peer-to-peer — all model/pipeline traffic flows directly between buyer and seller nodes. ai.market never sees or touches payloads.

**IS NOT** a cloud service or model host. Runs on the participant's own infrastructure. Outbound connections only — works behind any firewall.

**Data plane:** Non-custodial. Encrypted relay forwards opaque frames (ChaCha20-Poly1305, per-session ephemeral keys). ai.market handles control plane and metering metadata only — never data plane content.

**Repo:** [aidotmarket/aim-node](https://github.com/aidotmarket/aim-node) (private)
**Local path:** `/Users/max/Projects/ai-market/aim-node`
**BQ:** BQ-AIM-NODE-APP (P0)
**Gate 2 spec:** `specs/BQ-AIM-NODE-APP-GATE2.md` in ai-market-backend repo

## Tech stack

Python 3.11+, Click (CLI), FastAPI (local proxy), websockets (relay + trust channel), cryptography (Ed25519/X25519, ChaCha20-Poly1305), httpx (market API client), Pydantic, tomli (config).

## Architecture

```
aim-node/
├── core/              # Shared with VZ (aim-core extraction)
│   ├── config.py      # AIMCoreConfig dataclass — no global imports
│   ├── crypto.py      # Ed25519/X25519 identity, keystore, envelope signing
│   ├── trust_channel.py  # WebSocket client to ai.market Trust Channel
│   ├── market_client.py  # HTTPS client to ai.market API
│   ├── auth.py        # Market API authentication
│   ├── logging.py     # Structured logging
│   └── offline_queue.py  # Queued ops when market unreachable
├── peer/              # Peer-to-peer data plane
│   ├── protocol.py    # AIM wire protocol — frame types, encode/decode
│   ├── encryption.py  # ChaCha20-Poly1305 AEAD, X25519 key exchange
│   ├── frames.py      # Frame serialization
│   ├── relay.py       # WebSocket relay client
│   └── connection.py  # Connection state machine + heartbeat
├── provider/          # Seller-mode
│   ├── adapter.py     # HTTP/JSON adapter — wraps seller endpoint
│   ├── session_handler.py  # Accept/manage incoming sessions
│   ├── health.py      # Endpoint health checking
│   └── config.py      # Provider configuration
├── consumer/          # Buyer-mode
│   ├── proxy.py       # Local HTTP proxy on :8400
│   ├── session_client.py  # Initiate/manage outbound sessions
│   ├── discovery.py   # Marketplace search proxy
│   └── config.py      # Consumer configuration
├── cli.py             # Click CLI commands
└── main.py            # Entrypoint, service orchestration
```

## Integration points

| Integrates with | How | Purpose |
|-----------------|-----|---------|
| ai.market backend | HTTPS API + WebSocket Trust Channel | Session negotiation, metering submission, marketplace discovery, billing |
| ai.market relay | WebSocket | Forwards encrypted frames between buyer and seller nodes |
| vectorAIz | Shared aim-core library | Crypto, trust channel, device provisioning — extracted with config injection |

## Configuration (aim-node.toml)

```toml
[node]
mode = "provider"   # or "consumer"
market_url = "https://api.ai.market"

[provider.adapter]
type = "http_json"
endpoint_url = "http://localhost:8080/predict"
health_check_url = "http://localhost:8080/health"
timeout_seconds = 30
max_concurrent = 10

[consumer]
port = 8400   # local proxy port
```

## CLI commands

| Command | Purpose |
|---------|---------|
| `aim-node serve` | Start in provider mode — wrap endpoint, connect to market |
| `aim-node connect` | Start in consumer mode — local proxy, marketplace access |
| `aim-node status` | Show node status, active sessions, metering |
| `aim-node config` | View/edit configuration |

## Provider mode

1. Reads `aim-node.toml` provider config
2. Loads Ed25519 identity keypair (generates on first run)
3. Connects to ai.market Trust Channel (WebSocket)
4. Registers node + listing on market
5. Listens for SESSION_NEGOTIATE from market
6. On session accept: establishes encrypted relay connection with buyer
7. Forwards requests to seller's HTTP endpoint via adapter
8. Reports seller-side metering events (cumulative, signed)

### Adapter (Phase 1: HTTP/JSON only)

Wraps exactly one protocol: HTTP endpoints that accept and return JSON. Receives decrypted REQUEST frame, extracts JSON payload, applies optional JSONPath transforms, forwards as POST to seller endpoint, wraps response back into RESPONSE frame. Error codes: 1006 (adapter error), 1007 (timeout).

### Health checking

Every 60s, hits the health check URL. After 3 consecutive failures: reports NODE_HEALTH_DEGRADED to market, rejects new sessions, existing sessions continue. Resumes on recovery.

## Consumer mode

1. Starts local HTTP proxy on `127.0.0.1:8400`
2. Connects to ai.market Trust Channel
3. Exposes endpoints:
   - `POST /aim/sessions/connect` — initiate session with a listing
   - `POST /aim/invoke/{session_id}` — forward request to seller
   - `GET /aim/sessions` — list active sessions
   - `DELETE /aim/sessions/{id}` — close session
   - `GET /aim/marketplace/search?q=...` — search marketplace

### Local proxy behavior

Request body forwarded as-is to seller. Response body forwarded as-is back. Response headers include `X-AIM-Trace-Id`, `X-AIM-Latency-Ms`. Error codes: 502 (adapter error), 504 (timeout), 503 (session closed/expired). Binds to `127.0.0.1` only — not externally accessible.

## Security model

### Encryption

All peer data flows encrypted with ChaCha20-Poly1305 AEAD. Per-session ephemeral X25519 keys provide forward secrecy. The relay sees only opaque ciphertext — it cannot decrypt, inject, replay, or impersonate.

### Key exchange (per session)

1. Market issues session tokens containing peer Ed25519 public keys
2. Both peers generate ephemeral X25519 keypairs
3. HANDSHAKE_INIT / HANDSHAKE_ACCEPT exchange ephemeral pubkeys + Ed25519 signatures
4. Shared secret via X25519 DH → HKDF-SHA256 → encryption_key, mac_key, iv_prefix
5. Ephemeral keys discarded after session — forward secrecy guaranteed

### Peer authentication

Chain of trust: market platform key → session token → peer Ed25519 pubkey → handshake signature. Invalid signatures rejected before any data exchange.

### Replay protection

Monotonically increasing sequence numbers per direction. Receiver rejects sequence ≤ last seen.

## Wire protocol (AIM/1.0)

| Type | ID | Direction | Purpose |
|------|-----|-----------|---------|
| HANDSHAKE_INIT | 0x01 | buyer→seller | Key exchange start |
| HANDSHAKE_ACCEPT | 0x02 | seller→buyer | Key exchange response |
| HANDSHAKE_REJECT | 0x03 | seller→buyer | Rejection with reason |
| REQUEST | 0x10 | buyer→seller | Model invocation |
| RESPONSE | 0x11 | seller→buyer | Invocation result |
| ERROR | 0x12 | either | Error with code |
| HEARTBEAT | 0x20 | either | Keepalive (30s interval) |
| HEARTBEAT_ACK | 0x21 | either | Heartbeat response |
| CANCEL | 0x30 | buyer→seller | Cancel in-flight request |
| CANCEL_ACK | 0x31 | seller→buyer | Cancel acknowledged |
| SESSION_CLOSE | 0x40 | either | Graceful teardown |
| SESSION_CLOSE_ACK | 0x41 | either | Close acknowledged |

### Heartbeat / liveness

Send HEARTBEAT every 30s of inactivity. HEARTBEAT_ACK expected within 5s. 3 missed = 90s dead detection → report to market, 1 reconnection retry, close if retry fails.

### Backpressure

Concurrency window: buyer tracks in-flight count against seller's `max_concurrent_requests` (default 10). Blocks new requests when full.

### Error codes

1000=generic, 1001=invalid frame, 1002=unsupported version, 1003=auth failed, 1004=session expired, 1005=rate limited, 1006=adapter error, 1007=timeout, 1008=payload too large, 1009=cancelled, 1010=session closing.

## Session lifecycle

```
Buyer calls POST /aim/sessions/connect
  → Market creates SpendReservation
  → Market sends SESSION_NEGOTIATE to seller via Trust Channel
  → Seller validates capacity, sends SESSION_ACCEPT
  → Market issues session tokens to both peers
  → Relay connection established (encrypted via key exchange)
  → REQUEST/RESPONSE loop
  → Both sides report metering events (cumulative, signed)
  → Ceiling enforcement: 90% warning, 100% auto-close
  → SESSION_CLOSE → final metering (is_final=true)
  → Reconciliation → settlement → payout (server-side)
```

### Edge cases

| Scenario | Behavior |
|----------|----------|
| Buyer disconnects | Seller detects via 90s heartbeat timeout, session open for 5min reconnection, then auto-closed |
| Seller endpoint crashes | ERROR frames, buyer sees 502, metering continues |
| Relay crashes | Both lose WebSocket, 1 retry, fail → closed after 5min |
| Ceiling hit mid-request | Session closed, in-flight completes best-effort, no new requests |
| Insufficient reservation | Rejected at negotiation (pre-connection) |

## Shared code with VZ (aim-core)

Extracted from VZ (`/Users/max/Projects/vectoraiz/vectoraiz-monorepo/`) with config injection refactoring:

| Component | VZ source | Extraction complexity |
|-----------|-----------|----------------------|
| Crypto (Ed25519/X25519) | app/core/crypto.py | Low |
| Trust Channel | app/services/trust_channel_client.py | Medium (settings coupling) |
| Serial store | app/services/serial_store.py | Medium |
| Activation manager | app/services/activation_manager.py | Medium |
| Auth service | app/services/auth_service.py | Low |
| Connectivity tokens | app/services/connectivity_token_service.py | Low |
| Offline queue | app/services/offline_queue.py | Low |
| Structured logging | app/core/structured_logging.py | Low |

All extracted modules use `AIMCoreConfig` dataclass (constructor injection) instead of VZ's global `app.config.settings`.

## Metering integration

Both sides submit metering events to `POST /aim/metering/events` on ai.market using signed envelopes. Events carry cumulative totals (not deltas). The server-side MeteringIngestionService updates `SpendReservation.consumed_cents` on buyer events and enforces ceiling checks.

Metering reporter submits at configurable intervals (default: every 60s or every 100 calls, whichever first).

## Troubleshooting

| Problem | Diagnosis | Fix |
|---------|-----------|-----|
| Can't connect to market | Trust Channel WebSocket fails | Check `market_url` in config, verify ai.market is up |
| Session negotiation timeout | No HANDSHAKE_ACCEPT within 10s | Seller node may be down or at capacity |
| Local proxy 503 | Session expired or relay dropped | Check session status, reconnect if needed |
| Local proxy 502 | Seller endpoint returned error | Check seller's endpoint health, adapter config |
| Heartbeat timeout (90s) | Peer unreachable | Network issue or peer crashed, 1 retry attempted |
| "NODE_HEALTH_DEGRADED" | Seller endpoint failing health checks | Fix the underlying endpoint, node auto-recovers |
| Identity key not found | First run or keystore corrupted | Delete keystore, restart (generates new identity) |
| Metering events not submitting | Offline queue backed up | Check market connectivity, events replay on reconnect |

## Development

```sh
cd /Users/max/Projects/ai-market/aim-node
pip install -e .
aim-node serve   # or aim-node connect
```

## Packaging (Phase 1)

Git clone + `pip install -e .` for development. PyPI package (`pip install aim-node`) planned for Phase 2.

## Related

- **Backend metering:** MeteringIngestionService in ai-market-backend (`app/services/metering_ingestion_service.py`)
- **Reservations:** ReservationService (`app/services/reservation_service.py`)
- **Gate 2 spec:** `specs/BQ-AIM-NODE-APP-GATE2.md` in ai-market-backend
- **VZ (data seller app):** [vz-release-process.md](vz-release-process.md)
- **CORE.md product description:** `docs/core/CORE.md` → "AIM Node — The Runtime"
