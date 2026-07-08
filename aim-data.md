# AIM Data — Local-First Data Publishing for ai.market

AIM Data is what a data seller installs on their own infrastructure to list datasets on the ai.market marketplace. It runs as a Docker container on the seller's machine, profiles the data, generates the listing metadata via allAI, and never copies the raw data anywhere. When a buyer purchases a listing, ai.market issues a signed delivery token and the bytes flow peer-to-peer from the seller's AIM Data install to the buyer. ai.market handles discovery, payments via Stripe, and the delivery token, but never sees or touches raw data.

**IS:** Customer-deployed Docker app. Local-first. Non-custodial. Tied to one seller identity on ai.market. The conduit through which allAI's metadata-generation work reaches the seller's data sources.

**IS NOT:** A cloud service. A data warehouse. A data mover. AIM Data never phones home with raw data, never stores buyer-side state, and never holds keys to the customer's S3 buckets. Long-lived AWS credentials stay in the customer's account. AIM Data only holds short-lived assumed-role sessions when it reads.

**Pillar:** AIM Data is the customer-deployed product that data sellers install to list datasets on ai.market. Originally launched as AIM Connect, then renamed to AIM Data. The codebase was forked from vectorAIz's into its own repo at `aidotmarket/aim-data`, since AIM Data does not need the document-to-vector-database conversion that defines vectorAIz. The two products are now separate codebases on separate lifecycles.

**Customer install URL (the advertised path):**
```
curl -fsSL https://get.ai.market/aim-data | bash           # macOS / Linux
irm https://get.ai.market/aim-data/windows | iex            # Windows
```

The one-liner routes through a Cloudflare Worker at `get.ai.market` that serves `installers/aim-data/install.sh` and `install.ps1` from the repo. CF Worker config lives in [cloudflare-worker.md](cloudflare-worker.md).

**Repo:** [aidotmarket/aim-data](https://github.com/aidotmarket/aim-data) (private)
**Source repo (git — build and edit here):** `/Users/max/Projects/ai-market/aim-data` (the active feature branch is checked out here).
**Deploy directory (NOT a git repo):** `/Users/max/aim-data` — holds `docker-compose.aim-data.yml`, `.env` (secrets + `AIM_DATA_VERSION`), `import/`, and the `aim-data-data` Docker volume. These two directories are easy to confuse; the source code is NOT under `/Users/max/aim-data`.
**Container image:** `ghcr.io/aidotmarket/aim-data` — published as `:latest` and version-tagged (e.g. `aim-data-v1.20.53`)
**Customer install guide:** `docs/INSTALL.md` in the repo
**Release runbook:** [aim-data-release-process.md](aim-data-release-process.md) — NOTE: that runbook still references the old `aidotmarket/vectoraiz` monorepo path. The codebase has been forked to its own `aidotmarket/aim-data` repo. Release runbook needs an update.

## Capability Matrix

What AIM Data does today, by feature, with status and the code that backs it. `BROKEN` and `PARTIAL` items have a `Notes` line. Everything else is shipped and working unless flagged otherwise.

| Feature | Status | Backing code | Customer-facing |
|---------|--------|--------------|-----------------|
| Install via one-liner from get.ai.market | **BROKEN** | `installers/aim-data/install.sh`, CF Worker | Yes — currently returns 502; customers cannot install via the advertised path |
| Install via manual compose | SHIPPED | `docker-compose.aim-data.yml` + `docs/INSTALL.md` | Yes — works; 7 env vars to set |
| Sign in with ai.market account | SHIPPED | `app/auth/`, `app/routers/auth.py` | Yes — sign in (or create) with an ai.market account at `localhost:8080/login`; no separate AIM Data account |
| Serial + bootstrap-token activation | SHIPPED | `app/services/activation_manager.py` | Silent at first boot, no UI prompt |
| Local data profiling | SHIPPED | `app/services/profiling/` | Surfaces in the listing draft |
| Local PII scanning (tri-state signal) | SHIPPED | `app/services/pii_scanner.py` | Yes — `passed` / `flagged` / `not run` per ai.market/aim-data trust signals |
| Local quality scoring (nullable) | SHIPPED | `app/services/quality_scorer.py` | Yes — nullable score on listing |
| allAI metadata generation | SHIPPED | `app/services/allai_client.py` | Yes — generates description and tags |
| Marketplace registration | SHIPPED | `app/services/marketplace_register.py` | Yes — Settings → Marketplace |
| Listing publish (signed VZ flow) | SHIPPED | `app/routers/marketplace_publish.py` → ai.market `/api/v1/vz/publish` | Yes — see "Publishing to ai.market (signed VZ flow)" below. NOT `/datasets/{id}/publish` (processing-era, dead after de-vectorization). |
| S3 source connector (STS assume-role, no-copy) | SHIPPED | `app/routers/s3_connections.py`, `app/models/s3_connection.py`, `app/models/s3_scan_job.py`, `app/models/s3_object_metadata.py` | Yes — full flow live: create connection → set role ARN → verify (STS AssumeRole) → scan bucket → review objects → register object as dataset → publish. allAI assists IAM-role setup on the connection screen. Remaining (separate items): buyer-side download UX on the marketplace frontend, and agent-QA use of the assumed credentials. |
| Signed delivery tokens | SHIPPED | `app/services/delivery_token.py` | No — server-to-server with ai.market backend |
| Peer-to-peer delivery channel | SHIPPED | `app/peer/` (shared aim-core with AIM Node) | No — kicks in at buyer-purchase time |
| Stripe payouts | SHIPPED | server-side at ai.market backend (Stripe Connect) | Yes — connects via Settings → Marketplace |
| One-click auto-update from UI | SHIPPED | mounts `/var/run/docker.sock` in compose | Yes — optional; customer can remove the mount |
| Embedded allAI assistant chat | SHIPPED | `app/routers/allai_chat.py`, `app/services/allai_agentic_provider.py` | Yes — routes through ai.market's `/api/v1/allie/chat/agentic` proxy; no customer Anthropic key needed |
| MCP server endpoint | SHIPPED | `app/mcp_server.py` | Yes — exposes AIM Data to AI agents |
| Database connector (BQ-VZ-DB-CONNECT) | SHIPPED | `app/services/db_extractor.py` | Yes — extract from customer's local Postgres / MySQL |
| Tika document parsing | SHIPPED | `app/services/tika_client.py` | Yes — extracts text from PDFs and Office docs |

## Architecture

Two containers on the customer's machine.

```
docker-compose.aim-data.yml
├── vectoraiz    ghcr.io/aidotmarket/aim-data:${AIM_DATA_VERSION}   nginx (UI) + uvicorn (API)
└── postgres     postgres:16-alpine                                  metadata, local auth, usage tracking
```

AIM Data does not bundle a vector database. The earlier stack carried a Qdrant container that has been removed from the product because AIM Data does not convert documents into vector databases. That capability lives in vectorAIz (the separate parallel product), where it is the value prop for corporate customers who want to ship vector-ready data to the market.

The image is one container with both nginx and uvicorn running side by side via the entrypoint. nginx exposes port 80 internally and serves the React UI plus reverse-proxies `/api/*` to uvicorn on `127.0.0.1:8000`. The compose file maps the customer's `${AIM_DATA_PORT:-8080}` to the container's 80. Uvicorn is locked to a single worker because the Co-Pilot uses a file-lock for coordination; scaling to multiple workers requires migrating that to Redis pub/sub. Cloudflared is baked into the image and the `tunnel` router exists for optional outbound-only tunnel deployments (useful for sellers behind restrictive NATs).

Inside the API container, the layout follows a standard FastAPI app. This tree is the **source repo at `/Users/max/Projects/ai-market/aim-data/`**, not the deploy directory:

```
/Users/max/Projects/ai-market/aim-data/
├── app/
│   ├── main.py              FastAPI entrypoint + router wiring
│   ├── mcp_server.py        MCP server entrypoint for agent integration
│   ├── config.py            settings (env vars, feature flags, service URLs)
│   ├── auth/                ai.market account sign-in, API key issuance, JWT
│   ├── routers/             ~35 endpoint groups (listings, sources, allai_chat, marketplace, ...)
│   ├── services/            ~95 service modules (profiling, PII, quality, S3, allAI client, etc.)
│   ├── models/              SQLAlchemy models (~28 tables, alembic-managed)
│   ├── schemas/             Pydantic request/response schemas
│   ├── middleware/          auth middleware, request logging, CORS
│   ├── core/                cryptography, structured logging, error handling
│   ├── cli/                 Click CLI (admin operations from inside the container)
│   ├── scripts/             one-off setup scripts (run via entrypoint or manually)
│   └── prompts/             Jinja templates for allAI prompts
├── alembic/                 database migrations
├── docker-compose.aim-data.yml
├── Dockerfile               developer build
├── Dockerfile.customer      production image pushed to GHCR
├── entrypoint.sh            starts nginx + uvicorn together
├── docs/
│   ├── INSTALL.md           customer install guide (the one /aim-data#install links to)
│   ├── RELEASING.md         developer release procedure
│   ├── diagnostics/TROUBLESHOOTING.md
│   └── security/SECURITY_MODEL.md
└── installers/
    └── aim-data/
        ├── install.sh       served at get.ai.market/aim-data via CF Worker
        └── install.ps1      served at get.ai.market/aim-data/windows
```

### Integration points

| Integrates with | How | Purpose |
|-----------------|-----|---------|
| ai.market backend | HTTPS API + WebSocket Trust Channel | Marketplace registration, listing publish, delivery token issuance, metering, billing |
| ai.market backend (Stripe Connect) | OAuth handoff | Seller Stripe account linking; payouts flow seller-direct |
| allAI | HTTPS via ai.market proxy | Metadata generation, classification, listing description authoring |
| Customer's S3 bucket | STS assume-role into customer's AWS account | Read-only; short-lived sessions; never reads when buyer isn't paying |
| Customer's local databases | Direct via `host.docker.internal` or service name | Postgres, MySQL extraction (BQ-VZ-DB-CONNECT) |
| Buyer's AIM Node or browser | Peer-to-peer encrypted channel (ChaCha20-Poly1305) | Data delivery at purchase time |
| GHCR | Docker image pull | Customer pulls `ghcr.io/aidotmarket/aim-data:latest` at install and update |
| Anthropic API | Not used directly — no customer key | Embedded allAI chat routes through the ai.market `/api/v1/allie/chat/agentic` proxy; AIM Data holds no Anthropic key. (Corrects prior drift: there is no customer-key path.) |

### Fork ancestry, vectorAIz relationship, and legacy naming

vectorAIz is the parallel product that converts documents into vector database files. That capability is its value prop, aimed at attracting corporate data to the marketplace where buyers can purchase ready-to-use vector data. vectorAIz remains a live product on its own development track.

AIM Data was forked from vectorAIz's repo into its own `aidotmarket/aim-data` codebase because AIM Data does not need the document-to-vector-database conversion, and the two products serve different seller workflows on different roadmaps. The two are now separate codebases on separate lifecycles.

The fork is recent enough that legacy vectorAIz naming still surfaces inside AIM Data. Env vars like `VECTORAIZ_CHANNEL`, `VECTORAIZ_VERSION`, and `VECTORAIZ_SECRET_KEY` appear in `docker-compose.aim-data.yml`. The compose service that runs the API is still named `vectoraiz`. A handful of files like `vectoraiz_crypto.py` and `local_only_*` remained in the repo because internal code in `app/services/` still imports them. This naming is cosmetic legacy from the fork ancestor. Customer installs work fine through it. Rename cleanup is on the backlog and not blocking anything customer-facing.

## Agent Capability Map

Which AI agents touch AIM Data and what they can do.

| Agent | Where it runs | What it does | Scope |
|-------|---------------|--------------|-------|
| allAI (metadata generator) | ai.market backend, called from inside AIM Data | Reads customer's profiled data structure (NOT raw rows), writes listing description, generates tags, classifies fields, scores PII risk, scores quality | Metadata only. Never sees raw data. Output is structured (Pydantic schemas). |
| allAI (embedded chat / CoPilot) | AIM Data container UI; all LLM calls go out through the ai.market `/agentic` proxy (no customer Anthropic key) | Every-page in-product assistant; on the S3 setup screen it walks the seller through creating the IAM role, hands them the trust policy stamped with their external ID, and validates the pasted role ARN | Proxy-only. Metered + capped per the allAI usage billing policy (see the allAI usage billing section below; `monthly_free_cap` shipped S779). |
| ai.market MCP server (server-side) | ai.market backend | Exposes the marketplace to AI agents: search, listing detail, purchase intent, requirements board | AIM Data's listings are automatically agent-discoverable through this. No extra integration on the seller's side. |
| AIM Data MCP server (customer-side) | Inside the AIM Data container | Exposes seller-side data operations (listing draft, publish, source management) to local AI agents | Customer-side automation. Off by default; customer enables when they want agent-driven publishing. |
| AG / MP / DeepSeek / CC (Council) | ai.market backend during build/review | Reviews specs and PRs that touch AIM Data. Not customer-facing. | Internal dev only. Never exposed to sellers or buyers. |

The principle from CORE.md §2 holds end-to-end: **allAI mediates everything**. Buyers and sellers never communicate directly. The agent that prepared the listing on the seller's side is the same one that answers a buyer's clarifying question on the marketplace side.

## Operate — Serving Sellers

The end-to-end flow from "seller signs up on ai.market" to "buyer's purchase pays out via Stripe."

### Install

1. Seller visits ai.market/aim-data and clicks Install.
2. Seller runs the one-liner appropriate for their OS. Verified live at `get.ai.market` (HTTP 200) as of S900 (2026-06-16); the manual compose flow in `docs/INSTALL.md` remains the fallback for sellers behind restrictive setups.
3. Seller creates a `.env` file per the values in `docs/INSTALL.md`. `POSTGRES_PASSWORD` is required (the compose fails fast without it). Other values either auto-generate to `/data` on first boot if not provided (HMAC secret, Fernet key) or come from me at activation time (serial + bootstrap token + keystore passphrase). AIM Data does NOT use the customer's own Anthropic API key — all allAI calls route through the ai.market `/agentic` proxy. INSTALL.md currently still lists `ANTHROPIC_API_KEY` as required; that's documentation drift from before the air-gap refactor and is flagged for correction.
4. `docker compose -f docker-compose.aim-data.yml up -d` pulls about 5GB of images on first run and brings up the three containers.
5. After roughly a minute, `curl http://localhost:8080/api/health` returns `status: ok`.

### First sign-in (ai.market account)

AIM Data has **no local admin account** — that concept belongs to vectorAIz, the standalone tool AIM Data was forked from at the 2026-05-28 split. AIM Data authenticates **only** against ai.market. The seller opens `http://localhost:8080`, lands on the sign-in screen ("Sign in with your ai.market account"), and signs in with an existing ai.market account or uses "Create one at ai.market" to register. There is no separate AIM Data account and no install-side admin-creation or password-reset screen — account and password management live entirely at ai.market.

### Serial activation

If I issued the seller a serial and bootstrap token (per-customer values I send by email at signup), they go in `.env` as `AIM_DATA_SERIAL` and `AIM_DATA_BOOTSTRAP_TOKEN`. The container reads both at first boot, calls home to ai.market once to register, and clears the bootstrap token from memory after a successful activation. After that the seller only needs the serial. The activation is silent and has no UI prompt. Without the serial, the install still runs but is not marketplace-connected.

### Connect to ai.market as a seller

Inside the app: Settings → Marketplace. The flow asks for the seller's name, billing email, and counterparty business details. After submit, ai.market sends a confirmation email. Clicking the link makes the install show up as a seller on the marketplace. Until that click, no listings can publish.

Auto-promotion (S772): a first-time **buyer**-role account is promoted to **seller** automatically on its first `POST /api/v1/vz/register` during publish, so a brand-new account can list without doing the Settings -> Marketplace step first. That promotion writes `users.role`, a Postgres `userrole` enum. A bug that wrote the value as bare varchar made `/vz/register` return 500 and publish return 409 ("VZ install registration not available") for buyer-role accounts; fixed S772 by casting the value to the enum and dropping an enum-vs-varchar `WHERE` comparison. If a fresh account 409s on publish again, check the register role-write path first.

### Set up the S3 source connector

The seller connects a bucket directly from the listing flow, with no separate Settings step. AIM Data renders a JSON trust policy that names the ai.market AWS account as the trusted principal. The seller copies the JSON, opens their own AWS IAM console, creates a role with S3 read access to the bucket they want to list from, pastes the trust policy as the role's trust relationship, and pastes the role ARN back into AIM Data. Clicking Verify runs an STS `AssumeRole` call. Green means the connector is ready. Long-lived AWS credentials stay in the seller's account. AIM Data only holds the short-lived assumed-role session when it reads.

### Prepare and publish a listing

As of v1.20.53 (S773) listing a file is a guided three-screen wizard. Raw data never leaves the seller; only metadata and the description go live on ai.market.

1. Privacy Review (automatic). When the seller opens a dataset the PII scan runs automatically on entry, with no manual scan button. The seller lands directly on the Privacy Review results and reviews detected PII; the privacy attestation is recorded truthfully from this screen. Click Continue.
2. Metadata Review. Metadata is auto-generated on entry through allAI (claude-opus-4-8 via the /agentic proxy, cost capped). The seller reviews the generated title, description, tags, and category, edits if needed, clicks Approve, then Continue to publish.
3. Listing Details and Disclosure (S804, merged main 18aa999). The seller confirms listing details (price, category), makes an explicit public-sample decision — publish the exact real rows shown in a read-only table, or publish no sample rows (the default; synthetic is never offered) — and checks a single confirmation stating the approved content becomes public and may be shared with search engines, AI assistants, HuggingFace, and AI-training crawlers. Then Publish to ai.market. After publish returns the listing_id, the app creates the backend disclosure snapshot (POST /api/v1/listings/{listing_id}/disclosure-snapshots via a local seller-auth proxy in marketplace_publish.py — NOT the VZ publish JWT); snapshot success is what activates the SEO push pipeline (JSON-LD refresh, IndexNow, HuggingFace). If publish succeeds but the snapshot fails, the seller sees "Listing published, disclosure snapshot pending" with Retry and Review actions — never silent success. Client-side sample limits: 100 rows / 25 columns / 250 KB, columns must match (frontend/src/lib/disclosure.ts). Disclosure decision audit persists on the dataset record with the backend-generated disclosure_version.

Publish is the signed path: POST /api/marketplace/publish to {ai_market}/api/v1/vz/publish. A first-time seller account is auto-promoted from buyer to seller on /vz/register. AIM_DATA_KEYSTORE_PASSPHRASE must be set or publish returns 503. Quality score still surfaces when enabled.

Dead paths, do not use: /pipeline, /process-full, /{id}/publish, /{id}/confirm. No vectorization, Qdrant, or RAG in this flow.

**Post-publish setup routing (S996).** ai.market keeps a published listing live but **not purchasable** until the seller is payout-ready (2FA enabled, then Stripe connected) — a backend gate, audited and production-verified under S774/S778. The AIM Data frontend reflects this: the marketplace login/`me` response carries `onboarding_required` / `onboarding_step`, now surfaced on `AuthContext`. On a successful publish, if `onboarding_required` is true, the app shows a “live but not purchasable until you finish setup” notice (15s toast with a **Finish setup** action) and deep-links the seller in a new tab to the canonical ai.market setup stepper at `https://ai.market/dashboard` (the website’s own 2FA-first → Stripe stepper, built S777; URL via `getActiveBrand().externalUrl`, de-skinned S751). The flag refreshes on tab-visible, so a seller returning from the setup tab is not wrongly re-nudged on a later publish in the same session. If `onboarding_required` is false, publish keeps the prior behavior (navigate to `/datasets`). AIM Data hosts **no** 2FA/Stripe UI of its own, and the app’s local `/setup` route is the install’s activation page, not marketplace onboarding. Merged to `aidotmarket/aim-data` main `520f789` (PR #38).

### Publishing to ai.market (signed VZ flow) — READ before touching publish

The **only** path that puts a listing on the live market:

1. The editor calls `POST /api/marketplace/publish` (`app/routers/marketplace_publish.py`) — the signed proxy.
2. The install registers its Ed25519 public key **once** with ai.market via `POST /api/v1/vz/register` (authed with the seller's ai.market bearer token), which returns a backend `install_id` (UUID). Client: `registration_service.ensure_vz_install_registered`; persisted in `serial.json` as `vz_install_id`.
3. To publish, the proxy signs a short-lived EdDSA JWT (`iss = install_id`, `sub = seller_id`, `metadata_hash`, 5-min exp, `jti`) and POSTs metadata to `{ai_market}/api/v1/vz/publish`. The backend looks up the `VZInstall` by `iss`, verifies the signature with the stored public key, checks `sub`, enforces replay (`jti` via Redis) and rate limits.

**Dead paths — do NOT wire publish to these:**
- `POST /api/datasets/{id}/publish` → `MarketplacePushService` is processing-era: it needs `/data/processed/{id}` artifacts that de-vectorization removed, plus a shared internal key. Returns 401/403.
- Local raw-listing publish (`RawListingService.publish_listing`) only sets a **local** status; it never syncs to ai.market.

**Two registrations that are easy to confuse** (they are different and write different tables):
- *Trust Channel* device registration → `POST /api/v1/trust/register` (`registration_service.register_with_marketplace`). Used for delivery/trust channel.
- *VZ publish* registration → `POST /api/v1/vz/register` (`ensure_vz_install_registered`). The publish JWT validates against the `VZInstall` created **here** — NOT the trust-channel registration. An install can be trust-registered yet still fail publish with `401 "VZ install not found"` if it was never vz-registered.

**Hard prerequisite — signing passphrase:** `AIM_DATA_KEYSTORE_PASSPHRASE` must be set (non-empty) in the deploy `.env`. Without it the app skips keypair generation at boot, never creates `/data/keystore.json`, and publish fails to sign (503 "Keystore passphrase not configured"). It is the device's signing identity — losing or rotating it orphans existing listings (see F-12). Store a copy safely.

> Status (S773): shipped and confirmed live in production. The signed flow (wired S760 on `fix/devectorize-publish-s760`) is merged to `main`, and a real signed publish from a fresh seller account succeeded end to end on 2026-06-05.

### The list-a-file flow end to end — PII review, allAI metadata enhancement, billing (READ FIRST when "the listing step is broken")

> Added S769 (2026-06-04). This step has been re-diagnosed and re-fixed many times and keeps rotting. If a seller "can't get allAI to enhance the metadata" or "publish does nothing," read this BEFORE changing any code. The repeated failures have come from fixing dead code and from a billing-mode gap, not from the listing logic itself.

**The live flow (post de-vectorization, S758-S760):**
1. Seller picks a file or connects a source (e.g. the S3 connector).
2. For an S3 object: register downloads the object locally via a presigned URL into `record.upload_path`, then kicks `process_dataset_task` -> `processing_service.process_file`. That path extracts the file, runs the **PII scan inside `_run_post_extract_analysis`** (writes `record.metadata["pii_scan"]`), enriches via DuckDB, and lands the dataset at `PREVIEW_READY`. **PII genuinely runs here.** `listing_metadata` does NOT run in `process_file`.
3. The seller steps through the three-screen wizard: the PII scan auto-runs on entry and lands on **Privacy Review** (review detected PII; attestation recorded), Continue to **Metadata Review** (allAI auto-generates title, description, tags, and category; the embedded assistant helps refine; Approve, then Continue to publish), then **Listing Details and Publish**. See "Prepare and publish a listing" above for the screen-by-screen detail.
4. Seller clicks **Publish to ai.market** -> `POST /api/marketplace/publish` (`app/routers/marketplace_publish.py`) -> signs a short-lived EdDSA JWT -> `POST {ai_market}/api/v1/vz/publish`. Only metadata goes live; raw data stays with the seller.

**The dead-path trap - the #1 reason this work gets redone:**
- `POST /api/datasets/{id}/publish` (`MarketplacePushService`) is **processing-era and dead** after de-vectorization. It needs `/data/processed/{id}` artifacts that no longer exist plus a shared internal key; it returns 401/403. **Do not wire publish to it.**
- `RawListingService.publish_listing` only sets a **local** status; it never syncs to ai.market.
- Wiring metadata generation into `process_file` or the `PipelineService` (`run_pipeline` / `run_full_pipeline`) is **also wrong** for the listing flow - those are processing-era and the live flow never calls them. Note the inverted names: `run_pipeline` is the EXTENDED step set (includes `listing_metadata`); `run_full_pipeline` is the smaller set. Neither is on the live listing path.

**allAI runs on OUR Anthropic key, through the proxy - config lives on the ai.market BACKEND, not in AIM Data:**
- AIM Data holds **no Anthropic key**. The assistant routes through ai.market's agentic proxy (`/api/v1/allie/chat/agentic`; service `app/services/allie_proxy_service.py`). The structured enricher is `app/allai/agents/listing_enricher.py` (`ListingEnricherAgent`).
- **Listing-assistance model:** the proxy default is `allie_model_default` (was `claude-sonnet-4-5-*`). Listing assistance should run on **Opus 4.8 (`claude-opus-4-8`)** (Max, S769).
- **Anti-abuse cap, not a billing lever:** a real metadata enhancement costs **pennies**. The cap exists only to stop a customer hammering allAI on a product that is free to them. Two distinct knobs: a per-operation guardrail `ListingEnricherAgent.budget_cap_usd` (was `$5.00`), and the per-customer ceiling that ships with the free-with-cap billing mode below. Max's target abuse ceiling for AIM Data is **$20** (S769).
- Cosmetic red herring: `/api/allai/status` can report `not_configured` under proxy mode (RC#19) even when allAI works. Do not chase it as the cause.

**Billing model - the deep root cause of "works once then rots":**
- **Product intent (Max, S769):** vectorAIz is an ongoing tool (an LLM searching the customer's own vectorized documents), so it gets a **$5 trial then paid** use. **AIM Data has exactly one job** - get the customer's data onto the market and be the peer-to-peer fulfillment vehicle when it sells - so **we pay for the metadata enhancement; that is the product's purpose.** AIM Data allAI use is free to the customer, capped only to prevent abuse.
- **Reality on `main` today:** AIM Data runs the **same** billing as vectorAIz - starter trial credit then prepaid/"buy more" (`app/services/credits_service.py`: `free_trial` -> `balance`; `billing_mode` enum is only `prepaid`/`invoice`). The intended **free-with-cap** mode (`monthly_free_cap`, `build:bq-aim-data-allai-monthly-cap-s736`) is **merged and live in production** (origin/main `a22a42e0`, PR #108, S779). Schema default cap is $10; AIM Data's operator target is $20, set per-customer via the internal admin endpoint (new accounts start at the $10 default until set). Reviews on record: Vulcan APPROVE, AG APPROVE, DeepSeek REVISE (soft-cap overshoot, accepted by Max as expected).
- **Consequence (legacy `trial_then_pay` accounts only, pre-S779 default):** such an AIM Data account behaves like vectorAIz - the moment its starter credit lapses, allAI stops responding and the metadata step **looks broken**. A freshly registered account has starter credit (covers a pennies-cost enhancement), so a first listing can succeed, but reused or aged accounts hit the wall. That intermittency is the "fixed it, then it broke again" symptom.

- **Operator controls + surfaces (live, S779):** internal `X-Internal-API-Key` GET/PATCH endpoints set the per-customer cap, toggle the allowance on/off, and switch billing mode. Both billing surfaces honor the cap — the allAI chat/listing proxy (`billing_service.record_allai_monthly_usage_once`) and the Co-Pilot deduct path (`credits_service.deduct_credits`) — each incrementing monthly spend under a `SELECT ... FOR UPDATE` row lock and idempotent per usage/deduction record. The cap is intentionally **soft**: the preflight allowance check and postflight spend record are not a reservation, so a burst of simultaneous requests right at the ceiling can overshoot by a small, bounded amount (cost absorbed); accepted by Max (S779) as expected for an abuse-prevention guardrail, strict-ceiling hardening is an optional future item.

**Fix order when this breaks:**
1. Confirm you are on the **live** publish path (`/api/marketplace/publish` -> `vz/publish`), not a dead path.
2. Confirm listing assistance uses **Opus 4.8** and the abuse cap is **$20**.
3. Confirm the account is not blocked by **credit exhaustion** (durable fix SHIPPED S779: set the account's billing mode to `monthly_free_cap` so it never depends on trial credit; accounts left on the legacy `trial_then_pay` default still hit this).
4. Confirm `AIM_DATA_KEYSTORE_PASSPHRASE` is set, or publish fails to sign (see the signed-VZ-flow section above).

### Buyer purchases, delivery happens

When a buyer purchases on ai.market, Stripe processes payment. ai.market sends the seller's AIM Data instance a signed delivery token over the Trust Channel. AIM Data validates the token, opens an encrypted peer-to-peer channel to the buyer (ChaCha20-Poly1305, per-session ephemeral keys), and streams the bytes. The relay sees only ciphertext. ai.market never sees the data. Stripe Connect pays out the seller minus the 5% marketplace commission.

### Update to a new version

When I release a new version:

```
docker compose -f docker-compose.aim-data.yml pull
docker compose -f docker-compose.aim-data.yml up -d
```

Data, settings, registration, and connectors carry across.

## Evolve — Invariants and Boundaries

What CAN'T change without re-architecting AIM Data.

### Invariants

1. **Non-custodial.** AIM Data is on the seller's machine. ai.market never holds the seller's raw data, never holds their AWS credentials, and never holds their data bucket contents. Any change that requires raw data to transit ai.market servers is BREAKING.
2. **allAI mediates everything.** Buyers and sellers never communicate directly through AIM Data. Any flow that creates a direct buyer-seller channel without allAI in the middle is BREAKING.
3. **Local-first processing.** Profiling, PII scanning, and quality scoring run on the seller's machine. Pushing any of these to ai.market is BREAKING.
4. **Honest signals.** PII and quality scores are nullable. `null` means "the seller has not run this scan." Faking a clean signal when a scan has not run is BREAKING.
5. **One seller identity per install.** AIM Data is tied to one ai.market seller account at activation. Multi-tenant inside one install is BREAKING.
6. **Read-only S3.** The STS assumed role grants S3 read only. Any code path that writes to a customer S3 bucket is BREAKING.
7. **Customer keeps the keystore passphrase.** The passphrase signs the seller's marketplace requests. ai.market never has it. If the seller loses it, they regenerate and lose attribution on existing listings. This is by design and is documented to customers.

### Boundaries — what stays in AIM Data, what stays at ai.market

| Stays inside AIM Data (seller's machine) | Stays at ai.market |
|------------------------------------------|-----|
| Raw data | Listing metadata only |
| Customer's AWS credentials | Listing index, search, agent-discoverable surface |
| Local Postgres state | Buyer accounts, purchase ledger |
| Customer's Anthropic key | Stripe Connect link to seller account |
| Profiling / PII / quality outputs | Delivery tokens (issued at purchase, signed) |
| Customer's seller identity keystore | Aggregated metering (counts, byte volumes) |

### Change classes

**BREAKING** — anything that violates the invariants above, or removes a Settings page, or changes the `.env` contract without a backwards-compatible default, or changes an authz scope.

**REVIEW** — anything that touches the activation flow, the marketplace registration flow, the Stripe Connect handoff, the delivery token validation, or the S3 STS trust policy template. These are the surfaces where a regression silently breaks customer trust.

**SAFE** — UI copy, internal service refactors that preserve external behavior, allAI prompt tweaks that don't change schema, version bumps to non-protocol dependencies.

### Active product changes in flight

Concrete items pending follow-up builds. Each is a real customer-facing risk if not closed.

- **~~Seller post-publish setup routing~~ DONE S996.** Last UX piece of the seller post-listing setup gate (BQ-SELLER-POST-LISTING-SETUP-GATE-S774; backend Gate-4 verified, web stepper S777). On first publish, a not-yet-payout-ready seller is deep-linked to the ai.market setup stepper (`https://ai.market/dashboard`, new tab) with a “live but not purchasable” notice; onboarding state refreshes on tab focus. No new 2FA/Stripe UI in AIM Data. Reviewed GLM APPROVE_WITH_NITS (both notes addressed). Merged `520f789` (PR #38). Detail under “Post-publish setup routing” in *Prepare and publish a listing*.

- **allAI usage billing for AIM Data — free monthly cost cap (SHIPPED S779, live in production).** AIM Data customers are intended to get allAI for free up to an operator-set monthly cost ceiling (default $10 per customer per month, resetting each calendar month), with no forced conversion to a paid plan. This is deliberately different from vectorAIz, where customers get a one-time free trial (~$5) and are then required to buy credits. Today the backend runs only the vectorAIz trial-then-pay model (`app/services/credits_service.py`: free_trial → balance → 'purchase more credits'), so AIM customers look free only while seeded trial credit lasts. Shipped to origin/main `a22a42e0` (PR #108, S779): a second billing mode (`monthly_free_cap`) on the account/credits model: monthly spend tracking with calendar rollover, soft cutoff at the cap (reason `monthly_allowance_reached`, no purchase prompt, we absorb the cost), and internal admin endpoints to set the per-customer cap / toggle allAI on-off / change billing mode. vectorAIz `trial_then_pay` behaviour is preserved unchanged. Follow-ups: ops.ai.market frontend console for per-customer cap view/edit/toggle; customer-app cutoff copy 'monthly allowance reached'. Business-logic detail: spec `specs/BQ-AIM-DATA-ALLAI-MONTHLY-CAP-S736.md` (ai-market-backend).

- **Qdrant removal from the AIM Data stack.** Product decision: AIM Data is not in the vector-database business; that capability belongs to vectorAIz. The Qdrant container has been removed from this runbook's architecture description. The actual `docker-compose.aim-data.yml`, any `qdrant_client` calls in `app/services/`, and the `QDRANT_HOST` / `QDRANT_PORT` env vars are pending removal in a follow-up build. Customer-facing impact: nothing breaks for current customers because Qdrant was internal to the stack; the next image build drops the container.

- **~~`get.ai.market` Cloudflare Worker returns 502~~ DONE 2026-05-27.** Repointed Worker GitHub-raw constant from `aidotmarket/vectoraiz` to `aidotmarket/aim-data` after the repo split moved the installer files. Same fix added `/aim-data/windows` and `/aim-node/windows` routes that were advertised on the marketing site but had no Worker handler. Both customer install one-liners (curl-bash and PowerShell irm) now return 200. Commits `46c3806` and `a6729e5` on `aidotmarket/cf-get-worker`. See §G-01 for the repeatable Worker install-path-drift pattern.

- **~~Installer image-name drift~~ DONE 2026-05-27.** Both `installers/aim-data/install.sh` and `install.ps1` now pre-pull `ghcr.io/aidotmarket/aim-data:latest` (multi-arch). Previous `ghcr.io/aidotmarket/vectoraiz:latest` was arm64-only — Intel Mac customers would have hit a manifest mismatch. Commit `c6665e0` on `aidotmarket/aim-data`.

- **~~Compose-file source URL drift~~ DONE 2026-05-27.** Both installer scripts now download the compose file from `aidotmarket/aim-data/main` (matching `docs/INSTALL.md`). Same commit `c6665e0` on `aidotmarket/aim-data`.

- **~~Release workflow smoke test broken~~ DONE 2026-05-27.** Workflow now uses `-p 8080:80` and hits `/api/health` so the smoke step actually verifies the container is up and the API responds. Commit `f12e953` on `aidotmarket/aim-data`. The next release tag will be the first one with a meaningfully verifying smoke job.

- **~~INSTALL.md `ANTHROPIC_API_KEY` drift~~ DONE 2026-05-27.** Both the prerequisites section and the env-var block in `docs/INSTALL.md` no longer mention `ANTHROPIC_API_KEY`. The env-var block was replaced with a short note that the embedded assistant routes through the ai.market proxy, with cleanup guidance for customers who have an older `.env`. Commits `34a559b` and `4d16186` on `aidotmarket/aim-data`.

- **Release runbook still references the old monorepo.** `aim-data-release-process.md` says the repo is `aidotmarket/vectoraiz`. The release script `release-aim-data.sh` does live in the monorepo (canonical at `/Users/max/Projects/vectoraiz/vectoraiz-monorepo/scripts/`), but the AIM Data product repo is now `aidotmarket/aim-data`. Update the release runbook to reflect both paths.

### Known unfixed product bugs (from TROUBLESHOOTING.md)

Surfacing here so they don't get lost between sessions.

- **RC#22 (CRITICAL):** ProcessWorkerManager semaphore leak in indexing path. Every customer batch-uploading past `N` files hits a deadlock. `N` defaults to `max(2, min(cores//4, 8))` so on a typical 8-core machine this is 8 files. One-liner fix: add `handle._cleanup()` in `app/services/processing_service.py:_run_indexing()` after `handle.wait()`. (Captured as F-11 in §F.)
- **RC#15:** No re-queue on startup recovery. Files in `uploaded` status at restart never auto-resume; customer must manually re-trigger reprocessing. Fix in `app/main.py` lifespan after `recover_stuck_records()`.
- **RC#16:** WorkerHandle cleanup not guaranteed; `_active_processes` list grows forever in long-running containers.
- **RC#19:** `/api/allai/status` endpoint shows `not_configured` because it hasn't been updated to reflect the ai.market proxy mode. Cosmetic — customers think the LLM is broken when it works.

## Gotchas — sources of past confusion (read before debugging publish/deploy)

- **Two directories.** Source repo (git): `/Users/max/Projects/ai-market/aim-data`. Deploy dir (compose + `.env` + data volume, not git): `/Users/max/aim-data`. Build/edit in the first; deploy from the second.
- **Env var prefixes.** Settings read `AIM_DATA_<NAME>` or `VECTORAIZ_<NAME>` (via `_env_alias` in `app/config.py`). Check the prefixed name (e.g. `AIM_DATA_KEYSTORE_PASSPHRASE`), not the bare `KEYSTORE_PASSPHRASE`.
- **`docker inspect ... .Config.Env` lies about emptiness.** Compose passes `VAR=${VAR:-}`, so a key shows up in `Config.Env` even when its value is empty. Don't conclude a var is set from that listing. Verify the real value with `docker exec <c> printenv VAR`, and confirm effect via boot logs (`Device keypairs initialized` vs `…passphrase not set — skipped`) and `ls /data/keystore.json`.
- **Local test deploy (no CI/GHCR).** Build the customer image from the source repo: `docker build -f Dockerfile.customer -t ghcr.io/aidotmarket/aim-data:<tag> .`. `Dockerfile.customer` builds the React UI (node) + nginx + API; the plain `Dockerfile` is **backend-only and does not build the frontend** — UI changes won't appear if you use it. Then in the deploy dir set `AIM_DATA_VERSION=<tag>` (and the passphrase) in `.env` and `docker compose -f docker-compose.aim-data.yml up -d app`. The official release is `scripts/release-aim-data.sh` (pushes a tag; CI builds + pushes the GHCR image).

## Isolate — Diagnosing Deviations

The known failure modes a seller or operator hits, ranked by likelihood. This table is enriched as we run more real installs. Currently the highest-frequency entry is the install one-liner returning 502 because the customer never gets past step one.

| ID | Symptom | Probable causes | Verify by | Repair |
|----|---------|-----------------|-----------|--------|
| F-01 | `curl https://get.ai.market/aim-data` returned 502 (FIXED 2026-05-27) | Worker was fetching install.sh from `aidotmarket/vectoraiz` repo at the old path after the repo split moved files to `aidotmarket/aim-data`. Worker returned 502 with body `Upstream error: 404`. | `curl -I https://get.ai.market/aim-data` returns 200 (was 502). | Fixed in `aidotmarket/cf-get-worker` commit `46c3806` — repointed `GITHUB_RAW` from vectoraiz to aim-data. Same patch also added `/aim-data/windows` route for PowerShell `irm`. Reference for future similar Worker drift. |
| F-02 | Installer dies with "Docker is not installed" or "daemon not running" | Docker Desktop or Docker Engine not present, or daemon stopped. | `docker info` returns errors. | Customer installs Docker Desktop or Engine, starts the daemon, re-runs the installer. |
| F-03 | `docker compose up -d` fails with "port is already allocated" or "address already in use" | Customer already running something on 8080, or a previous AIM Data instance was not torn down. | `lsof -iTCP:8080 -sTCP:LISTEN` (Mac/Linux) or `netstat -ano \| findstr :8080` (Windows). | Set `AIM_DATA_PORT=<other>` in `.env` and `docker compose up -d`. |
| F-04 | Compose fails with "Set POSTGRES_PASSWORD in .env" before any container starts | `.env` file missing the required value. The compose file uses `:?` to hard-fail when this is missing. | `grep POSTGRES_PASSWORD .env` — empty or absent. | Add `POSTGRES_PASSWORD=<strong-random>` to `.env` (e.g. `openssl rand -hex 32`). Then `docker compose up -d`. |
| F-05 | Apple Silicon Mac fails docker pull with "no matching manifest for linux/arm64" | A release missed the multi-arch build, or QEMU setup in the release workflow regressed. | `docker manifest inspect ghcr.io/aidotmarket/aim-data:<tag>` must list both `amd64` and `arm64`. | Re-run the release workflow with QEMU setup verified. CI integrity gate normally catches this but has been known to slip. |
| F-06 | `docker compose up -d` looks frozen on first pull | First-pull downloads about 5GB of images. Slow connections take several minutes. Normal. | `docker compose -f docker-compose.aim-data.yml logs vectoraiz` shows pull progress. | Wait. Subsequent starts are fast. |
| F-07 | `localhost:8080` shows `ERR_CONNECTION_REFUSED` | Containers not running. Most often: customer ran `up` without `-d` and closed the terminal, or `docker compose down` was run. | `docker compose -f docker-compose.aim-data.yml ps` — no rows or all `Exited`. | `docker compose -f docker-compose.aim-data.yml up -d` again. Inspect `docker compose logs` if it won't start. |
| F-08 | S3 connector wizard shows `status=error` with "STS AssumeRole AccessDenied" or 403 | Trust policy paste wrong, role ARN wrong, missing `external_id` condition, role lacks `s3:ListBucket` + `s3:GetObject`, or bucket region mismatch. | From inside the container: `aws sts assume-role --role-arn <pasted> --role-session-name test` — should return temporary credentials. | Re-paste the trust policy from the wizard exactly. Add `s3:ListBucket` on bucket ARN plus `s3:GetObject` on `bucket/*` in the role's permission policy. Confirm bucket region matches. Click Verify. |
| F-09 | First-boot activation fails: container repeatedly logs "activation required" or "422 from /serials/{serial}/activate" | Customer pasted token wrong, token already redeemed (one-time-use), or network blocked outbound to `api.ai.market`. | `docker compose logs vectoraiz \| grep -i activation` shows the activation outcome. | Ask Max for a fresh token. Re-paste `AIM_DATA_SERIAL` and `AIM_DATA_BOOTSTRAP_TOKEN`. `docker compose restart vectoraiz`. |
| F-10 | Marketplace registration confirmation email never arrives | ai.market backend Stripe webhook delay, customer typo in billing email, or spam folder. | Check spam. Check the address in Settings → Marketplace matches the one I sent the serial to. | Resend from ai.market admin. Worst case I flip the seller-confirmation flag manually. |
| F-11 | Batch upload of N+1 files freezes after N complete; (N+1)th file stuck in `extracting` or `indexing` forever | **CRITICAL — RC#22 semaphore leak in indexing path.** `ProcessWorkerManager` leaks a semaphore on each indexing run. N defaults to `max(2, min(cores//4, 8))`. Every customer doing batch upload past N files hits this. | `docker exec ... ps aux \| grep python` shows only 1 python process; postgres `SELECT status, count(*) FROM dataset_records GROUP BY status` shows stuck files; container at low CPU. | **Workaround**: `docker restart vectoraiz` container; re-trigger reprocessing via UI. **Real fix pending**: one-liner add `handle._cleanup()` to indexing path in `app/services/processing_service.py:_run_indexing()` after `handle.wait()`. Tracked as RC#22 in TROUBLESHOOTING.md. |
| F-12 | After `AIM_DATA_KEYSTORE_PASSPHRASE` rotation, marketplace publish fails with signature error; existing listings orphan | Wallet identity is bound to passphrase via KDF; `/data/keystore/keystore.json` was generated with old passphrase. | Compare current `AIM_DATA_KEYSTORE_PASSPHRASE` in `.env` against backup. | Restore old passphrase from backup if available. If not, delete `/data/keystore/`, restart container, accept that existing listings orphan under fresh seller identity. Document the trade-off to customer up front. |
| F-13 | After `/data` volume wipe, install loses all API keys, keystore identity, and HMAC secret; encrypted-at-rest data unrecoverable | Customer wiped `/data` thinking it was scratch, or `docker compose down -v` recreated the volume. | `docker volume ls \| grep aim-data-data` — if missing, wipe happened. Check `/data/.vectoraiz_secret_key` and `/data/.vectoraiz_hmac_secret` on next boot — if regenerated, old keys lost. | Restore `/data` from backup. Without backup, all encrypted-at-rest data is unrecoverable; customer regenerates everything. |
| F-14 | `docker pull ghcr.io/aidotmarket/aim-data:latest` fails with `toomanyrequests` or 429 | GHCR rate limit per IP, or customer behind shared NAT with other GHCR users. | Error message includes "toomanyrequests" or "rate limit." | `docker login ghcr.io` with a GitHub personal access token (`read:packages` scope). Retry pull. |

## Repair Patterns

Concrete fixes for the failure modes above, ordered to match. For each: the change, the rollback, and how to verify the repair held.

These patterns assume the customer is technical enough to read a log file. For non-technical customers, escalate to me directly.

### G-01 — Worker install-path drift (the F-01 class of fix, shipped 2026-05-27)

**Symptom class:** A `get.ai.market/<product>` URL returns 502 with body `Upstream error: 404` (the Worker is alive and reached upstream, but upstream is missing the file).

**Root cause:** The Worker source in `aidotmarket/cf-get-worker` has hardcoded GitHub raw URLs at the top of `src/index.js`. When a product repo gets split or renamed, those constants need updating. The 502 is the Worker translating a 404 from `raw.githubusercontent.com`.

**Change:** Update the relevant constant in `src/index.js` (e.g. `GITHUB_RAW`, `AIM_NODE_RAW`). Then `cd /Users/max/Projects/ai-market/cf-get-worker && CLOUDFLARE_API_TOKEN=$(infisical secrets get CLOUDFLARE_API_TOKEN --projectId bd272d48-c5a1-4b52-9d24-12066ae4403c --env prod --domain https://secrets.ai.market --plain) npx wrangler deploy`. Wrangler may report a route-binding 401 — that's benign because routes in wrangler.toml already match what's configured at Cloudflare; the script upload step still succeeds.

**Rollback:** `git revert` the source commit, re-deploy. Customer fallback while the Worker is broken is the manual `docker compose` flow in `docs/INSTALL.md` which doesn't depend on `get.ai.market`.

**Verify:** `curl -sI -H "Cache-Control: no-cache" https://get.ai.market/aim-data` returns 200 with `Content-Type: text/x-shellscript`. Body of a successful `curl -sL` should start with `#!/usr/bin/env bash`.

**Adjacent paths to verify on every Worker change:** `/aim-data`, `/aim-data/install.sh`, `/aim-data/install.ps1`, `/aim-data/docker-compose.yml`, `/aim-data/windows`, `/aim-data/` (landing), and the peer `/aim-node` set. The Worker handles both products.

### G-02 to G-14 — Per the F-table

For now, the Verify and Repair columns in §F are the operational guidance. When this section is enriched in a follow-up session, each F-row gets a matching G-row with code-level entry points and rollback procedures.

## Acceptance Criteria — for this runbook

This runbook is acceptable when:

- A stateless operator (human or agent) given only this document and no prior context can: install AIM Data from scratch, diagnose any of the F-01 through F-14 failure modes, and execute the matching repair.
- Every status in the Capability Matrix matches reality on the day of last verification.
- Every BROKEN or PARTIAL item has a backing BQ or a flagged follow-up.
- The Invariants section reflects the current CORE.md product description for AIM Data.
- The install URLs (the curl one-liner and the manual compose URL) match what the ai.market website tells customers to run.

## Lifecycle

| Field | Value |
|-------|-------|
| Created | 2026-05-27 |
| Last verified end-to-end | (pending the first real customer install) |
| Refresh trigger | Any BREAKING change per §H, any new BROKEN status in the Capability Matrix, or 90 days since last verified |
| Owner | Vulcan (orchestration) for content sync, Max for product decisions |
| Escalation | Max directly |

## Conformance

The runbook standard at `specs/BQ-RUNBOOK-STANDARD.md` defines §A through §K with prescribed agent forms. This runbook follows the conceptual coverage of those sections but uses the narrative + tables style of `aim-node.md` rather than the strict template skeleton at `templates/runbook.template.md`. Reasons:

- The strict template is structured for the runbook linter and harness. Until both are wired against this file, the narrative form is more useful for a non-technical co-founder read.
- The peer product runbook (`aim-node.md`) is also narrative + tables, and is the de facto pattern in this repo today.

When the linter + harness ship, this runbook converts to the strict form. The conceptual content stays. Until then, the gaps from strict conformance are: no YAML frontmatter `linter_version` field, §E scenarios in prose rather than `yaml operate` blocks, §G patterns in prose rather than `yaml repair` blocks.

## Related

- [aim-data-release-process.md](aim-data-release-process.md) — release cut procedure (needs update to the forked repo path)
- [aim-node.md](aim-node.md) — peer product runbook (the dev conduit; AIM Data is the seller conduit)
- [cloudflare-worker.md](cloudflare-worker.md) — `get.ai.market` Worker that serves the install one-liner
- [infisical-secrets.md](infisical-secrets.md) — how the seller's `.env` values relate to operator-side secrets
- [ai-market-backend.md](ai-market-backend.md) — the marketplace side AIM Data talks to
- ai.market customer-facing pages: [/aim-data](https://ai.market/aim-data), [/sell-data](https://ai.market/sell-data)
- CORE.md product description: `docs/core/CORE.md` → "AIM-Channel — The Non-Dev Conduit" (CORE.md positions AIM-Channel as the data-seller conduit class; AIM Data is the current implementation of that role. CORE.md still describes a shared-codebase-with-vectorAIz model that is no longer accurate post-fork — flagged for CORE.md update. S996: AIM Channel is now RETIRED and superseded by AIM Data; the CORE.md pillar named "AIM-Channel" should be renamed to AIM Data via a peer-reviewed constitution edit.)
