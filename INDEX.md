# Runbook index

## Account Capability & Onboarding Runbook
- Path: `account-capability-onboarding.md`
- Purpose: Covers the capability model that gates buying and selling on ai.market: how a user becomes a seller, what "provisioning" vs "active" means, the readiness signals that move a seller to active, the `require_capability` guard, the 403 `CapabilityRequiredError` contract, the self-serve buyer→seller request endpoint, the read-capabilities endpoint, and the capability-aware dashboard. Backing code verified against `aidotmarket/ai-market-backend` deployed main `839eef35` (slice-2 ship, S1054) and `aidotmarket/ai-market-frontend` deployed main `4932ecd` (capability-aware dashboard + floating setup bar, S1054).
- Owner: `Vulcan / Mars (ai.market backend peers)`
- Last verified: `2026-07-02`
- Aliases: none
- Error signatures: none
- Status: current

## Account Teardown & User-Data Erasure
- Path: `account-teardown.md`
- Purpose: Covers the verified data footprint of a user account on ai.market (the `users` FK closure, delete-rule inventory, and no-FK "weak link" identifier tables), the manual operator teardown procedure that works today, the external PII surfaces (Stripe, CRM, tokens, backups), and the guardrails any future automated teardown feature must honor. Re-authored S1165 from live production measurements (backend main `abb5b55d`, prod DB read 2026-07-09) after the S1161 draft was lost uncommitted. The automated teardown FEATURE is planned, not shipped — owner BQ: `BQ-E2E-TESTING-FRAMEWORK-S1152` (E2E Option B rides on it); its spec requires UNANIMOUS Council (customer-data class).
- Owner: `vulcan`
- Last verified: `2026-07-11`
- Aliases: none
- Error signatures: interactive-login garbage from the infisical CLI, empty secret value (rc=0, len 0), foreign_key_violation on NO ACTION/RESTRICT tables, residual weak-link rows
- Status: current

## ACL Sole-Writer Enforcement (WS9)
- Path: `acl-sole-writer-enforcement.md`
- Purpose: **PARTIAL note (Phase D enforce-flip):** code-complete and unit-tested but never executed against production; gated on (a) explicit Max direction, (b) the live write-path hook landing (Chunk 6, see PLANNED row), and (c) resolution of the precedence defect in When it breaks-05. Operative mode for the whole subsystem today is WARN-only, and no live interception exists until the Chunk 6 hook ships.
- Owner: `vulcan`
- Last verified: `2026-06-24`
- Aliases: none
- Error signatures: ValueError "field_acl already contains enforce rows, verdict.ready is False with non-empty blocked_reasons, StateRequestError 409 acl_phase_c_slo_not_ready, StateRequestError 409 field_acl_row_already_enforced, StateRequestError 404 field_acl_row_not_found, empty report (total_writes=0)
- Status: current

## Activation Verification Runbook
- Path: `activation-verification.md`
- Purpose: **S612 Process Consolidation Owner**: this runbook is the single canonical reference for CI gates AND deploy verification after the S612 consolidation that collapsed ~8 process BQs into BQ-PROCESS-CI-DEPLOY-GATES-S612 (P1). Per Council mandate, this file now covers BOTH pre-merge CI gates (branch protection, lint, smoke tests) and post-merge activation verification (proof-of-life checks). **Section layout:** - **§CI Gates (pre-merge)** — main-branch protection rules across ai-market-backend, ai-market-frontend, ops-ai-market, koskadeux-mcp, aim-node; required CI checks before merge; branch-protection configuration. - **§Lint gates** — lint pass enforcement; ops-ai-market lint configuration. - **§Deploy verification (post-merge)** — Railway deploy receipt verification; production smoke tests; activation proof-of-life (existing body below). Backend correctness primitives (atomic-write idempotency, token target binding, entity CAS locking) are explicitly NOT consolidated under this BQ per Council mandate; they remain product backend BQs. Revisions land as PRs; require MP review-mode approval. Filed under S612.
- Owner: `unassigned`
- Last verified: `2026-07-11`
- Aliases: none
- Error signatures: none
- Status: current

## Agent Completeness
- Path: `runbooks/agent-completeness.md`
- Purpose: **Fetch trigger:** agent creation or Gate 3 agent-compliance review.
- Owner: `vulcan`
- Last verified: `2026-08-24`
- Aliases: none
- Error signatures: incomplete_agent_surface
- Status: current

## Agent Dispatch
- Path: `runbooks/agent-dispatch.md`
- Purpose: **S1527 reviewer-transport supersession.** `runbooks/council.md` is the sole authority for CC, Kimi, and GLM dispatch. All reviewer-wrapper, exact-SHA, package-validation, turn-budget, retry, parser, verdict-persistence, and Council Hall instructions below are historical and must not be executed. The only active reviewer path is `council_request` as a thin trigger over `scripts/council_dir.py`: one request file in, one response file out. This runbook remains authoritative only for the separate MP build path and general non-reviewer dispatch operations.
- Owner: `vulcan`
- Last verified: `2026-08-25`
- Aliases: none
- Error signatures: bootout_without_plist_patch, cutover_admission_unknown, default_cwd_false_positive, env_var_in_inherited_only, gateway_timeout, health_failure, mp_busy, progress_guard_timeout, schema_validation_failure, stale_task_state, strict_verdict_invalid, structural_gate_unknown, tr_truncation_false_negative, unsupported_line_claim
- Status: current

## Aging Policy
- Path: `runbooks/aging-policy.md`
- Purpose: **Fetch trigger:** stale or critical-stale standup or queue decision.
- Owner: `vulcan`
- Last verified: `2026-07-17`
- Aliases: none
- Error signatures: stale_queue_undispatched
- Status: current

## ai-market-backend — Central Platform API
- Path: `ai-market-backend.md`
- Purpose: FastAPI backend powering all of ai.market. Handles auth, listings, orders, payments, agents, CRM, fulfillment, and the allAI intelligence layer.
- Owner: `unassigned`
- Last verified: `2026-08-27`
- Aliases: Railway backend deployment, FastAPI production API
- Error signatures: none
- Status: current

## ai-market-frontend — Marketplace Web App
- Path: `ai-market-frontend.md`
- Purpose: Content refresh S811 (PR #28): dual-audience homepage and buyer landing. AIM Federate is retired, with no current public surface, route, redirect, or asset; reintroduction requires explicit Max decision. Copy is governed by website-copy-standard.md.
- Owner: `unassigned`
- Last verified: `2026-08-25`
- Aliases: frontend build, Railway frontend deployment, Next.js marketplace
- Error signatures: none
- Status: current

## ai.market Trust Channel Control Plane Runbook
- Path: `trust-channel.md`
- Purpose: This runbook was source-audited against `aidotmarket/ai-market-backend` `origin/main` at `a51770aba9fe372ab3e305b4a3e3ab871b94d857` on 2026-07-13. The KMS registration and handshake sections were re-audited against production merge `447075d43c8fa2ad1a43b05754457163990adce3` on 2026-08-25. The mounted API prefix is `/api/v1`; use the routes below, even where an endpoint docstring omits `/api`.
- Owner: `vulcan`
- Last verified: `2026-08-25`
- Aliases: none
- Error signatures: Device ID already registered to another user, AUTH_FAILED or Device is inactive or revoked, HTTP 503 KMS not ready, HTTP 404 Device not found, target socket remains usable after a check opportunity, A remains authorized after an exception, B disconnects with A, no targeted indeterminate injection exists, zero rows, active DB row but no live socket, CRYPTO_SCHEME_MISMATCH, KMS readiness check failed
- Status: current

## AIM Data Release Process
- Path: `aim-data-release-process.md`
- Purpose: Builds and publishes new AIM Data versions. Creates GitHub releases, triggers GHCR Docker multi-arch builds, and runs smoke tests.
- Owner: `unassigned`
- Last verified: `2026-08-14`
- Aliases: none
- Error signatures: none
- Status: current

## AIM Data Seller Publish Journey
- Path: `aim-data-seller-publish-journey.md`
- Purpose: This page fills the AIM Data seller-publish documentation gaps historically recorded as S1216-D3, S1219-D1, and their predecessors. Those identifiers are provenance, not current admission or close requirements. The procedure starts after the customer has an AIM Data install and follows the customer-visible path through ai.market sign-in, install registration, local listing preparation, explicit disclosure confirmation, signed publish, and live-listing verification.
- Owner: `mars`
- Last verified: `2026-07-15`
- Aliases: none
- Error signatures: POST /api/v1/vz/register returns 500 with operator does not exist: userrole <> character varying, VZ install registration auth failed (401 or 403), Accept all & continue remains disabled while title and description are populated and dataset.listing_id is null, Metadata generation failed, HTTP 409 VZ install registration not available — sign in with ai.market and try publishing again, HTTP 403 detail.error=capability_required capability=seller, HTTP 503 Publish unavailable: security services offline, Listing published, disclosure snapshot pending, runner/job failure before the Publish request
- Status: current

## AIM Data — Local-First Data Publishing for ai.market
- Path: `aim-data.md`
- Purpose: AIM Data is what a data seller installs on their own infrastructure to list datasets on the ai.market marketplace. It runs as a Docker container on the seller's machine, profiles the data, generates the listing metadata via allAI, and never copies the raw data anywhere. When a buyer purchases a listing, ai.market issues a signed delivery token and the bytes flow peer-to-peer from the seller's AIM Data install to the buyer. ai.market handles discovery, payments via Stripe, and the delivery token, but never sees or touches raw data.
- Owner: `vulcan`
- Last verified: `2026-08-23`
- Aliases: none
- Error signatures: none
- Status: current

## AIM Node Release Process
- Path: `aim-node-release-process.md`
- Purpose: Builds and publishes new AIM Node versions. Creates GitHub releases, triggers GHCR Docker multi-arch builds, and runs smoke tests.
- Owner: `unassigned`
- Last verified: `2026-04-08`
- Aliases: none
- Error signatures: none
- Status: current

## AIM Node — The Runtime
- Path: `aim-node.md`
- Purpose: The universal network client for ai.market. Same codebase, two modes: **provider** (wraps a model/pipeline endpoint, serves it to buyers) and **consumer** (searches marketplace, sends requests via local HTTP proxy). Peer-to-peer — all model/pipeline traffic flows directly between buyer and seller nodes. ai.market never sees or touches payloads.
- Owner: `unassigned`
- Last verified: `2026-04-07`
- Aliases: none
- Error signatures: none
- Status: current

## aimarket-mcp-server — Public MCP Integration
- Path: `aimarket-mcp-server.md`
- Purpose: Model Context Protocol (MCP) server that lets any LLM client (Claude, ChatGPT, etc.) search, evaluate, and purchase datasets from ai.market. Published on PyPI and npm.
- Owner: `unassigned`
- Last verified: `2026-04-01`
- Aliases: none
- Error signatures: none
- Status: current

## Alerts at session open (S1529)
- Path: `runbooks/alerts-at-open.md`
- Purpose: Two rules hold this together and both are load-bearing:
- Owner: `mars`
- Last verified: `2026-08-30`
- Aliases: open items alerts, session open tally, ops build queue alerts
- Error signatures: alerts unavailable
- Status: current

## allAI Escalation Safety Spine
- Path: `allai-escalation-safety-spine.md`
- Purpose: Core invariant: silence is the only unacceptable outcome; over-paging is fine. `escalation_watchdog.ack(request)` means "the watchdog need not fail open for this request" - it does not mean "delivered." Delivery is proven by a successful Telegram send, a fallback send, or a confirmed dead-letter record that keeps the incident visible.
- Owner: `vulcan`
- Last verified: `2026-07-16`
- Aliases: none
- Error signatures: escalation_pipeline: Telegram disabled/unconfigured, escalation_pipeline: submit failed and dead-letter recording failed; leaving watchdog pending unacked, No allowlist log and no page, escalation_pipeline: deduplicated escalation, escalation_pipeline: Redis unavailable - sending without dedup, escalation_watchdog: fail-open page failed; retained for retry
- Status: current

## allAI — Agent Intelligence Layer
- Path: `allai-agents.md`
- Purpose: The intelligence layer inside ai-market-backend. Runs all autonomous agents (Brain, SysAdmin, CRM Steward, Matchmaker, etc.), the service bus for inter-agent communication, and the agent host that manages lifecycle, events, and subscriptions.
- Owner: `unassigned`
- Last verified: `2026-08-26`
- Aliases: none
- Error signatures: none
- Status: current

## AlphaFold Reference Listings
- Path: `alphafold-publish-scale-up.md`
- Purpose: The module boundary is one deployable unit of the publish path such as the backend listings service or the frontend listing detail page.
- Owner: `vulcan`
- Last verified: `2026-06-06`
- Aliases: none
- Error signatures: 422 unprocessable, AccessDeniedException 403, 500 internal server error
- Status: current

## Anthropic Prompt Caching
- Path: `runbooks/anthropic-prompt-caching.md`
- Purpose: This page records the verified state and remaining evidence gaps for Build Queue item `s1555`, “Stop paying full price for the same prompt,” which received its initial cache placement in exact `ai-market-backend` commit `84df5f976bd5dea6730c7ea7f1f8da476cf45b88`. Git proves that commit is an ancestor of production-reported revision `ed12d1b86c5475f41a9bed7057946b079a6bbd75`. The Railway deployment reported `SUCCESS` for deployment `82d8c1dc-2c81-4c22-ad65-f9f00c193ac3`, created `2026-08-18T22:07:14.283Z`.
- Owner: `vulcan`
- Last verified: `2026-08-19`
- Aliases: none
- Error signatures: none
- Status: current

## auth-signup-flow — Sign-up & Login Path Reference
- Path: `auth-signup-flow.md`
- Purpose: Reference for the customer authentication paths in `ai-market-backend`: Google OAuth, GitHub OAuth, magic-link, and password registration. Documents the architectural principle that protects sign-up, the known issues affecting it, and the diagnostic + recovery procedures.
- Owner: `unassigned`
- Last verified: `2026-08-15`
- Aliases: none
- Error signatures: none
- Status: current

## AWS Account — ai.market
- Path: `aws.md`
- Purpose: Parent runbook for ai.market's AWS account. Per-service detail lives in sub-runbooks: **aws-s3.md**.
- Owner: `Vulcan-Primary`
- Last verified: `2026-05-31`
- Aliases: none
- Error signatures: none
- Status: current

## AWS S3 — ai.market *(sub-runbook of [aws.md](./aws.md))*
- Path: `aws-s3.md`
- Purpose: Parent: **aws.md** (account-wide identity, access tiers, guardrails, billing). This sub-runbook is the source of truth for S3 buckets, their lockdown settings, lifecycle/cost, and the S3-connector assume-role.
- Owner: `Vulcan-Primary`
- Last verified: `2026-05-31`
- Aliases: none
- Error signatures: none
- Status: current

## Backup & Recovery — ai.market
- Path: `backup-and-recovery.md`
- Purpose: Source of truth for **what is backed up, where, on what cadence, how failure is alerted, and how to restore the market.** Destination/identity specifics: aws-s3.md. Secret locations: infisical-secrets.md. Architecture rationale: `BQ-AI-MARKET-COMPLETE-BACKUP-ARCHITECTURE-TITAN1-CENTRIC-S681`.
- Owner: `Vulcan-Primary / Mars-Worker`
- Last verified: `2026-08-25`
- Aliases: none
- Error signatures: none
- Status: current

## BQ-124 Retro-Verification Procedure
- Path: `bq-124-retro-verification.md`
- Purpose: Retro-verification procedure for the two BQ-124 beat-scheduled jobs that were previously closed without trustworthy production runtime proof:
- Owner: `unassigned`
- Last verified: `2026-04-19`
- Aliases: none
- Error signatures: none
- Status: current

## Branch Landed Verification
- Path: `runbooks/branch-landed-verification.md`
- Purpose: **Fetch trigger:** any of — writing a base SHA into a build brief; merging or pushing; reporting that work has landed; reading a dispatcher result that claims a push failed; reconciling a Build Queue item against code.
- Owner: `mars`
- Last verified: `2026-07-27`
- Aliases: none
- Error signatures: clean_tree_read_as_current, push_failed_but_landed, stale_build_base, unlanded_branch_believed_landed
- Status: current

## browser-session-auth — Login Sessions That Survive Reload
- Path: `browser-session-auth.md`
- Purpose: How a logged-in ai.market browser session stays alive across page reloads and new tabs. The model is deliberate: the **access token lives only in memory** (never in localStorage — XSS posture, see backend `lib/SECURITY.md`), and an **httpOnly refresh cookie** silently re-mints the access token on page load. On a fresh load the app calls `POST /api/v1/auth/refresh` with `withCredentials` and no body; the browser attaches the refresh cookie; the backend returns a new access token and rotates the cookie.
- Owner: `unassigned`
- Last verified: `2026-06-17`
- Aliases: none
- Error signatures: none
- Status: current

## Build Queue Reconciliation
- Path: `runbooks/build-queue-reconciliation.md`
- Purpose: The reconciler core reads one BQ entity from Living State, fetches Build Queue status, fetches git evidence for every `body.target_repos` repository, reads the gate chunk plan from the local spec, and classifies drift.
- Owner: `vulcan`
- Last verified: `2026-08-26`
- Aliases: none
- Error signatures: unsupported_target_repo
- Status: current

## Build-Queue Lifecycle Management
- Path: `build-queue-lifecycle.md`
- Purpose: **Lifecycle transition triggers (AC1.9).** Transitions are explicit, never inferred from CI/deploy/webhook signals:
- Owner: `vulcan`
- Last verified: `2026-07-26`
- Aliases: none
- Error signatures: completion_evidence_required, token_not_active
- Status: current

## Builder Controls
- Path: `runbooks/builder-controls.md`
- Purpose: This runbook exists by Max directive (S1455): a reference for future builders on exactly what controls surround the build and why. It is the companion to the S1455 minimal-bridge rebuild (specs/BQ-MINIMAL-BUILDER-BRIDGE-S1455-GATE1.md in koskadeux-mcp), whose Gate 1 R1 passed unanimously with mandates folded at 9cc065fc.
- Owner: `vulcan`
- Last verified: `2026-08-23`
- Aliases: builder-bridge, minimal-bridge, mp-builder-controls
- Error signatures: none
- Status: current

## Buyer Request Publication and Discovery
- Path: `runbooks/buyer-request-publication-and-discovery.md`
- Purpose: This runbook describes current code and deployed state separately; a merged commit is not called deployed until Railway proves the exact SHA.
- Owner: `vulcan`
- Last verified: `2026-08-29`
- Aliases: buyer-requests, request-matching, request-publication
- Error signatures: BUYER_REQUEST_MATCH_RELEVANCE_QUESTION, delivery_cycle_failed, request_match_deliveries table does not exist, rolling_24h_cap
- Status: current

## CC machine identity (council reviewer credential)
- Path: `cc-machine-identity.md`
- Purpose: Stop the recurring destruction of Max's Claude login and keep the CC council reviewer dispatchable without any human credential. Owns: how CC authenticates, how the key rotates, and how to diagnose credential failures on the CC path.
- Owner: `unassigned`
- Last verified: `2026-08-27`
- Aliases: none
- Error signatures: none
- Status: current

## Celery Infrastructure Deployment
- Path: `celery-infrastructure-deployment.md`
- Purpose: Production Celery for `ai-market-backend` runs as a three-service Railway topology from one shared Docker image:
- Owner: `unassigned`
- Last verified: `2026-04-19`
- Aliases: none
- Error signatures: none
- Status: current

## Chrome Browser Use on Titan 1
- Path: `runbooks/chrome-browser-use.md`
- Purpose: This runbook covers the normal authorized operator Chrome identity used for internal operations such as `https://ops.ai.market/build-queue`. The `kdbrowser` account and its browser profile are only for isolated ai.market synthetic customer journeys. Never use a `kdbrowser` identity or profile for internal operations, and never move an internal operator tab into that identity.
- Owner: `vulcan`
- Last verified: `2026-08-28`
- Aliases: browser-use, chrome-extension-native-host, chrome-native-messaging, codex-desktop-chrome, ops-ai-market-browser, titan-1-browser-use, kdbrowser-identity-boundary
- Error signatures: The admin-enforced policy could not be verified, Cannot communicate with the ChatGPT browser extension, Browser service/config bridge stale or unavailable, Native host manifest does not exist, Browser is not available: chrome, Google Chrome running: no, installed false or enabled false, correct false, config_read_ok false, config_requirements_read_ok false, Exact operator tab not found
- Status: current

## Cloudflare and DNS
- Path: `cloudflare-and-dns.md`
- Purpose: Canonical runbook for everything Cloudflare-fronted at ai.market and vectoraiz.com — DNS records, Workers, the live mcp.ai.market tunnel, and the API access patterns. Supersedes the prior `cloudflare-worker.md` (now Worker-detail subsection of this doc) and the partial Cloudflare table in `ai-market-backend/docs/core/INFRASTRUCTURE.md`.
- Owner: `unassigned`
- Last verified: `2026-07-17`
- Aliases: none
- Error signatures: none
- Status: current

## Cloudflare Worker (get.vectoraiz.com)
- Path: `cloudflare-worker.md`
- Purpose: **⚠️ DEPRECATED — superseded 2026-04-29 by `cloudflare-and-dns.md` (S688), banner applied 2026-05-22 (S691)** — This runbook has been **fully subsumed** by `cloudflare-and-dns.md`, which is the canonical authority for all Cloudflare DNS, Tunnel, and Worker operations (including the four active Workers: `get-ai-market`, `allai-dead-man-switch`, `vectoraiz-installer`, `aim-node-installer`). **Content here is preserved for historical reference only and may contain stale claims.** Always consult `cloudflare-and-dns.md` first. Cross-references to this file in `vz-release-process.md`, `aim-data-release-process.md`, and `aim-node-release-process.md` will be updated separately.
- Owner: `unassigned`
- Last verified: `2026-05-22`
- Aliases: none
- Error signatures: none
- Status: current

## Codex / MP — Council Primary Builder
- Path: `codex-mp.md`
- Purpose: **MP** is the Council name for OpenAI **Codex** (model `gpt-5.6-sol`, ChatGPT OAuth). It is the **mandatory builder for all BQ/development code builds**. Since the S1213 roster change (CORE 9.8) MP is NOT a gate voter — the gate panel is CC/Kimi/GLM — though explicit MP review dispatch remains available outside gate voting. All code and spec builds — BQ development work AND trouble-ticket fixes that require code — route to MP; CC is never a build path (S1213/CORE 9.8 supersedes the S1148 MP-vs-CC build split for code work; CC's role is gate voting via its read-only review path). MP never reviews its own builds (builder ≠ reviewer is a hard rule). Canonical roster and quirks: `infra:council-comms`; gate mechanics: `agent-dispatch.md`.
- Owner: `vulcan`
- Last verified: `2026-08-30`
- Aliases: none
- Error signatures: gateway timeout on foreground dispatch >30s, RepairExhaustedError: schema repair exhausted, silent past 300s with status still running, dispatches 4xx/hang after swap
- Status: current

## Connectivity Layer
- Path: `connectivity.md`
- Purpose: **Status:** CURRENT — live-verified 2026-05-31 (S738.w, Mars) against Titan-1 incl. serials + `tailscale whois`. **Owner:** SysAdmin agent / Council instances. **Last updated:** 2026-05-31.
- Owner: `SysAdmin agent / Council instances.`
- Last verified: `2026-05-31`
- Aliases: none
- Error signatures: none
- Status: current

## Constitution Amendment — changing CORE.md
- Path: `constitution-amendment.md`
- Purpose: **The rule (CORE footer, v9.13; Max directives S1242 and S1370; voter roster updated S1319):** every amendment to CORE.md — including editorial changes — normally requires a **unanimous Council gate (CC, Kimi, GLM — 3/3 valid verdicts per CORE §5 decision rules) AND Max's direct approval**. The only alternative is Max explicitly stating that he supersedes the Council for the exact matter named; that statement stands in place of Council approval and must be recorded in the Event Ledger. No agent may infer supersession from urgency or a general instruction. Either instance may then apply the authorized exact change. No reduced quorum, voter substitution, or builder vote is permitted.
- Owner: `mars`
- Last verified: `2026-07-28`
- Aliases: none
- Error signatures: missing / malformed / model-mismatched verdict, any non-APPROVE-class verdict, Max declines or amends, version_conflict on the patch, GUARDRAIL refusal text on the push, entity and file differ
- Status: current

## Constitution History
- Path: `runbooks/constitution-history.md`
- Purpose: **Fetch trigger:** amendment, provenance, or historical audit.
- Owner: `max`
- Last verified: `2026-07-27`
- Aliases: none
- Error signatures: constitution_source_drift
- Status: current

## Corpus Capture Policy - What We Keep
- Path: `runbooks/corpus-capture-policy.md`
- Purpose: **Governing principle (Max, 2026-07-30, decision event d0052189-43c2-4251-9684-501ecc8daaf0):** capture only data that is necessary to operate the market, filter repetitive data, and treat metadata about customer data as the most important data. Target: reduce Google embedding API calls and new capture database writes by more than 95% against the 2026-07-21..07-28 baseline (roughly 55,000 rows and 32,000 embeddings per day, measured 100% internal-operations content).
- Owner: `sysadmin`
- Last verified: `2026-08-28`
- Aliases: allai-corpus-policy
- Error signatures: thousands of rows per day for one target_type, open count grows without review, the fixed-subject ticket is absent or duplicated because its query or persistence failed, pending or dead_letter rows deleted, decision returns HTTP 403, trust returns HTTP 409, decision returns HTTP 422, any semantic row contains a redacted placeholder or has no current trust lineage, no deployed allowlist/ceiling, any non-pilot row, any raw data or sentinel placeholder, a correction without its generation interaction, or any projection row
- Status: current

## Council
- Path: `runbooks/council.md`
- Purpose: This runbook is maintained by Vulcan. Neither instance is senior to the other.
- Owner: `vulcan`
- Last verified: `2026-08-29`
- Aliases: Council dispatch, review transport, glm-codex-transport, glm-profile-isolation
- Error signatures: Error occurred during tool execution, Not logged in, OAuth session expired and could not be refreshed, is not set; source the credential first, no response written after, required reviewer missing from the live tool schema
- Status: current

## Council Gate Process
- Path: `runbooks/council-gate-process.md`
- Purpose: This runbook documents the stable gate-process slice: Build Queue entity shape, Gate 1 through Gate 4 transitions, author/reviewer provenance, and the cross-review completion gate.
- Owner: `mp`
- Last verified: `2026-07-27`
- Aliases: none
- Error signatures: authoring_distinction_trap, break_glass_left_enabled, chunk_scope_gap, cross_review_block, directional_evidence_missing, fabricated_line_reference, gate1_status_trap, harness_bound_to_stale_code, missing_design_artifact, unresolved_mandates
- Status: current

## Council Hall Deliberation
- Path: `runbooks/council-hall-deliberation.md`
- Purpose: This runbook documents the Council Hall deliberation pattern: independent assessment, collection/synthesis, and cross-pollination for decisions where one review pass is insufficient.
- Owner: `vulcan`
- Last verified: `2026-08-20`
- Aliases: none
- Error signatures: biased_synthesis, duplicate_deliberation, late_arriver, open_response_schema_mismatch, participant_config_missing, premature_cross_poll
- Status: current

## Council Review Collection, Gate Recording, and Lane Coordination
- Path: `runbooks/council-review-collection.md`
- Purpose: Backing-code paths are relative to the koskadeux-mcp repository root.
- Owner: `mars`
- Last verified: `2026-07-30`
- Aliases: council-verdict-collection, gate-recording
- Error signatures: cc_verdict_parse_failure, completion_truncated, dispatch_sha_invalid, gate_status_not_flipped, glm_page_path_hallucination, mp_lane_held, peer_msg_silent_dedupe, review_preload_unresolved
- Status: current

## Council Roster and Quirks
- Path: `runbooks/council-roster-quirks.md`
- Purpose: **Fetch trigger:** before Council dispatch or voter validation.
- Owner: `vulcan`
- Last verified: `2026-07-27`
- Aliases: none
- Error signatures: stale_roster_snapshot
- Status: current

## Council session gate, gateway deploy, and fold dispatch — operations
- Path: `council-session-gate-and-fold-ops.md`
- Purpose: Owner: Vulcan/Mars (either instance). Last verified live: 2026-06-12 (S830). Covers the session arming lifecycle post-S812-fix, the gateway deploy/restart procedure, and how to run spec-fold dispatches through author-mode — including the credential mechanics and the known middleware gaps.
- Owner: `Vulcan/Mars (either instance)`
- Last verified: `2026-06-12`
- Aliases: none
- Error signatures: none
- Status: current

## CRM
- Path: `runbooks/crm.md`
- Purpose: This runbook replaces three archived documents (`crm-architecture.md`, `crm-pipeline.md`, `crm-target-state.md`) that were last accurate in early July 2026. All three described a fourteen-table `crm_*` data model as "Active (production)". Those fourteen tables were deliberately deleted from production on 2026-07-03. An agent working from the superseded documents writes queries against tables that do not exist and, worse, concludes that a migration failed and tries to recreate them. Do not do that. See H.1 Invariant 1.
- Owner: `vulcan`
- Last verified: `2026-08-26`
- Aliases: crm-architecture, crm-pipeline, crm-steward, crm-target-state, party-model
- Error signatures: UndefinedTable, empty contact_id on upsert, pipeline stages feature is not yet fully set up, relation "crm_entities" does not exist, relation "crm_people" does not exist, relation "crm_pipeline_stages" does not exist, the pipeline stages migration may not have been run, empty array, gateway timeout, unknown entity_id, interaction_type rejected, ok true with prose describing a missing table, ok false with error_code, 404, 403, relationship write requested
- Status: current

## CRM Architecture
- Path: `archive/legacy-crm-s1490/crm-architecture.md`
- Purpose: **SUPERSEDED 2026-08-09 (S1490). DO NOT USE.** Replaced by `runbooks/crm.md`. This document describes fourteen `crm_*` tables as active in production. All fourteen were deleted on 2026-07-03 by migration `s1113_drop_legacy_crm_tables` under an explicit Max GO and unanimous Council approval. Queries written from this document will fail with `UndefinedTable`, and its diagnostic advice leads to recreating retired tables. Retained for history only.
- Owner: `unassigned`
- Last verified: `2026-08-09`
- Aliases: none
- Error signatures: none
- Status: archived

## CRM Pipeline
- Path: `archive/legacy-crm-s1490/crm-pipeline.md`
- Purpose: **SUPERSEDED 2026-08-09 (S1490). DO NOT USE.** Replaced by `runbooks/crm.md`. This document describes fourteen `crm_*` tables as active in production. All fourteen were deleted on 2026-07-03 by migration `s1113_drop_legacy_crm_tables` under an explicit Max GO and unanimous Council approval. Queries written from this document will fail with `UndefinedTable`, and its diagnostic advice leads to recreating retired tables. Retained for history only.
- Owner: `unassigned`
- Last verified: `2026-08-09`
- Aliases: none
- Error signatures: none
- Status: archived

## CRM Target-State Runbook — System Standard
- Path: `archive/legacy-crm-s1490/crm-target-state.md`
- Purpose: **SUPERSEDED 2026-08-09 (S1490). DO NOT USE.** Replaced by `runbooks/crm.md`. This document describes fourteen `crm_*` tables as active in production. All fourteen were deleted on 2026-07-03 by migration `s1113_drop_legacy_crm_tables` under an explicit Max GO and unanimous Council approval. Queries written from this document will fail with `UndefinedTable`, and its diagnostic advice leads to recreating retired tables. Retained for history only.
- Owner: `unassigned`
- Last verified: `2026-08-09`
- Aliases: none
- Error signatures: none
- Status: archived

## Daily CRM Briefing — First Real-Content Verification
- Path: `archive/evidence/briefing-verification-2026-04-25.md`
- Purpose: **Date**: 2026-04-25 07:00 UTC (first delivery after S499 data backfill + S501/S502 Chunk A fixes) **Owner**: Max / Vulcan next-session **Gate**: BQ-CRM-USER-SCOPING-BACKFILL-AND-FALLBACK AC11 — contact_count > 0 for 7 consecutive days starts today
- Owner: `Max / Vulcan next-session`
- Last verified: `2026-07-31`
- Aliases: none
- Error signatures: none
- Status: archived

## data-requests — Buyer-initiated Data Request Surface
- Path: `data-requests.md`
- Purpose: The data-request feature lets a buyer post a "I'm looking for X kind of data" listing and receive responses from sellers. Lifecycle: a buyer drafts a request, submits it for publication, eligible requests become public, sellers reply with proposals, the buyer picks a winning response and the flow proceeds to payment + fulfillment via the standard listing/order pipeline.
- Owner: `unassigned`
- Last verified: `2026-08-29`
- Aliases: none
- Error signatures: none
- Status: current

## Dataset-Card Publishing (HuggingFace / Kaggle / data.world)
- Path: `dataset-card-publishing.md`
- Purpose: Every published or updated ai.market listing gets a metadata dataset card pushed to external data platforms, each carrying a backlink to `https://ai.market/listings/{slug}`. This is core AI-discoverability work (CORE §2, ai.market pillar): buyers asking an LLM anywhere in the world should surface our customers' listings. Cards are metadata-only by default; actual sample rows publish only to HuggingFace and only with a seller-approved disclosure snapshot.
- Owner: `vulcan`
- Last verified: `2026-07-10`
- Aliases: none
- Error signatures: job status dead with 401/403 in last_error, job status dead with 400 in last_error (Kaggle), row stays pending > 10 min, status dead, first job dead with 4xx
- Status: current

## Dev Trouble-Ticket Lifecycle Runbook
- Path: `dev-tickets.md`
- Purpose: Owner: both instances. Scope: dev-class support tickets (T-YYYY-NNNNNN) — issues in existing systems. Created S1164 discharging debts S1164-D1/D2/D3. Not for BQs (new development) or customer tickets.
- Owner: `both instances`
- Last verified: `2026-08-30`
- Aliases: none
- Error signatures: none
- Status: current

## Disaster Recovery — ai.market (what is in S3 and how to rebuild)
- Path: `disaster-recovery.md`
- Purpose: A copy of this file lives at `s3://aimarket-backups-prod/RESTORE-README.md` so the recovery map survives even if GitHub and Titan-1 are gone. This document is the **map**; `backup-and-recovery.md` (same repo) is the full **manual**.
- Owner: `unassigned`
- Last verified: `2026-06-08`
- Aliases: none
- Error signatures: none
- Status: current

## Docker Testing (VZ Local)
- Path: `docker-testing.md`
- Purpose: Tests vectorAIz Docker images locally on Titan-1 via OrbStack before promoting to stable.
- Owner: `unassigned`
- Last verified: `2026-03-06`
- Aliases: none
- Error signatures: none
- Status: current

## Durable Runtime State Relocation (S1456)
- Path: `runbooks/durable-runtime-state.md`
- Purpose: This page describes the Gate 4 remediation accepted live at exact `koskadeux-mcp` SHA `dd23191057ed2a8b2eefc3fd1de5675cedbec27b`. The locked Gate 1 design is `specs/BQ-DURABLE-STATE-RELOCATION-S1456-CURRENT.md` at exact SHA `fb1802cdca61946ea25fb28bc0dd965e29e3bcf4`; Gate 2 is `specs/BQ-DURABLE-STATE-RELOCATION-S1456-GATE2.md` in that exact code candidate. The separately reviewed live runbooks identity was published runbooks main `4cece4cbb7d42b314855a658546a9f2ddf411f03`.
- Owner: `vulcan`
- Last verified: `2026-08-25`
- Aliases: none
- Error signatures: none
- Status: current

## E2E Browser Runner
- Path: `e2e-browser-runner.md`
- Purpose: The missing heart of the E2E programme, shipped in phases. Before S1196 the harness had a queue, redaction, retention, ticket filing, a webhook emitter and a nightly schedule - but no browser. `browser_journey` is the charter kind that opens a real Chromium and walks the product. Phase 1 (live since S1196) is the anonymous public walk: it signs into nothing, declares no accounts and writes nothing. Phase 4 recorded replay is live since S1622 for committed, human-approved journeys; the first promoted recording is the production-read-only `anonymous-allai-s1294.v1`. The signed-in buyer and mutating seller journeys remain later phases. Owner BQ: `BQ-E2E-BROWSER-RUNNER-S1194`, child of `BQ-E2E-TESTING-FRAMEWORK-S1152`.
- Owner: `mars`
- Last verified: `2026-08-27`
- Aliases: none
- Error signatures: browser_journey refused: E2E_PROD_FRONTEND_URL is required, status harness_error, summary browser_journey requires params.mode, preflight refusal (404, 403, 401, non-200, allowed=false, timeout), Production targeting refused: E2E_INTERNAL_API_KEY is required for preflight, no screenshot present, one attempt remains on Submitting or no persistent held result is visible, held audit exists but an inquiry row was created, buyer-01 reaches Listings, sees no create control or incomplete seller onboarding, and the run reports a product blocker, recording manifest or artifact refusal before Playwright launch, flaky_pass_after_retry
- Status: current

## E2E Programme Integrity
- Path: `runbooks/e2e-programme-integrity.md`
- Purpose: Max, S1315: "This is the crucial test of our system. If we solve this we have a business. If not we have a gigantic pile of crap." This runbook exists because of a single recurring pattern: **every failure this programme has had looked exactly like success**. The nightly died at startup for weeks and the page simply showed nothing. Runs completed while coverage sat at zero. Findings were published as a bare count with no text. Tickets were silently never filed. When ticketing was finally connected it pointed at a decommissioned host, which would have looked like it was working. A dead charter was mapped to a real journey, which would have shown a permanent false red. A charter claimed a whole journey while walking one page, which would have shown a false green. A charter was written that could not perform its own steps and would have improvised password guesses against our only enabled production account. None of those announced themselves. A future instance CANNOT assume this programme is healthy because it is running. Run How to operate-01 and prove it.
- Owner: `mars`
- Last verified: `2026-07-23`
- Aliases: none
- Error signatures: newest run finished in under a second, or is days old, runs complete but every coverage item still reads never_run, findings_count above zero but no finding text and no ticket refs, the goal instructs an action the harness has no primitive for, covers claims a whole item for a partial walk, a queued charter has no file in charters/, a queued entry has covers null while its committed file declares ids
- Status: current

## E2E Test-Status Publisher
- Path: `runbooks/e2e-test-status-publisher.md`
- Purpose: The reporting seam of the E2E programme. A harness run already produces a report on disk and files tickets; this is the piece (c6, shipped S1314) that also writes a single redacted, bounded coverage record to Living State so Max has one honest place to see how much of the product is actually proven. The record lives at `infra:e2e-test-status`; the ops.ai.market Test page reads it read-only and renders it. The publisher is deliberately fail-soft: it never changes a run's outcome and never blocks a run, and it stays dormant unless the sanctioned harness runtime activates it. Owner BQ: `BQ-E2E-TESTING-FRAMEWORK-S1152` (c6 Test page); coverage catalog from `BQ-E2E-BROWSER-RUNNER-S1194`.
- Owner: `mars`
- Last verified: `2026-07-23`
- Aliases: none
- Error signatures: entity not found (404 / null), last_run banner shows a failed staging-health run, last_run_id did not change and a warning was logged, publish stops writing after the manifest edit
- Status: current

## E2E Video Review
- Path: `runbooks/e2e-video-review.md`
- Purpose: Max, S1315: "I feel like this is a mine field that can only be crossed in the moment." The browser agent runs headless and leaves only text behind. Video is being added so a human, and a video model, can see what the run actually looked like. This runbook is NOT an operating manual for a shipped system - very little of it is built. It is the DESIGN RECORD, kept in the runbooks on Max's instruction so that whoever improves this process next can see the reasoning and the rejected alternatives instead of rediscovering them. Read the H.6 decision log first. It is the decision log, and it is the reason this file exists. Owner BQ `BQ-E2E-RUN-VIDEO-AND-GEMINI-REVIEW-S1315`.
- Owner: `mars`
- Last verified: `2026-07-23`
- Aliases: none
- Error signatures: you cannot find the reasoning for an existing choice, both reviewers agree with everything, the question is settled by argument instead of measurement
- Status: current

## Email Drafting
- Path: `email-drafting.md`
- Purpose: Prepares outreach and follow-up emails as HTML files with pre-filled `mailto:` links. Gmail adds Max's signature automatically.
- Owner: `unassigned`
- Last verified: `2026-03-06`
- Aliases: none
- Error signatures: none
- Status: current

## Gate Procedure
- Path: `runbooks/gate-procedure.md`
- Purpose: **Fetch trigger:** authoring, review, build dispatch, or gate recovery.
- Owner: `vulcan`
- Last verified: `2026-07-27`
- Aliases: none
- Error signatures: gate_eligibility_unknown
- Status: current

## Gateway V2 Rollback
- Path: `gateway_v2_rollback.md`
- Purpose: Disable Gateway V2 surfaces without corrupting canonical backend records. Rollback changes traffic, flags, DIST channels, and eligibility gates; it does not rewrite listings, quotes, billing sessions, access grants, accepted meter events, receipts, settlement records, or governance decisions.
- Owner: `unassigned`
- Last verified: `2026-06-06`
- Aliases: none
- Error signatures: none
- Status: current

## Gateway V2 Rollout
- Path: `gateway_v2_rollout.md`
- Purpose: Roll out AIM Node Gateway V2 in staged gates without changing the accepted thesis: Gateway V2 is the runtime gateway for the existing ai.market marketplace, and ai.market backend remains the canonical system of record.
- Owner: `unassigned`
- Last verified: `2026-06-06`
- Aliases: none
- Error signatures: none
- Status: current

## GCP Auth
- Path: `gcp-auth.md`
- Purpose: GCP authentication for ai.market spans four independent auth paths. Gmail OAuth uses long-lived refresh tokens stored in the `gmail_tokens` Railway Postgres table; these stay valid only while the GCP OAuth consent screen for project `aimarket-prod` is set to User Type Internal (External/Testing apps expire refresh tokens after 7 days and silently break briefings, the drop pipeline, and draft sending). The gcloud CLI holds a separate interactive session used for Pub/Sub and GCP admin; it requires a browser login and cannot be driven headlessly. Vertex AI Gemini uses a Vertex Express API key (prefix `AQ.`) held in Infisical as `VERTEX_GEMINI_KEY`. The Trust Channel KMS runtime separately uses `GCP_SERVICE_ACCOUNT_JSON`, canonical in Infisical `ai-market-backend`/`prod` and synchronized to Railway production; application credentials are configured before the shared KMS client is initialized. The KMS credential is not a Gemini credential.
- Owner: `vulcan`
- Last verified: `2026-08-30`
- Aliases: Vertex authentication, Gmail OAuth, gcloud credentials, Trust Channel KMS
- Error signatures: RefreshError: Reauthentication is needed. Please run gcloud auth application-default login, 401 UNAUTHENTICATED ACCESS_TOKEN_TYPE_UNSUPPORTED, Reauthentication failed
- Status: current

## GitHub → Reconciliation Webhook
- Path: `reconciliation-github-webhook.md`
- Purpose: The single GitHub webhook that drives build-queue reconciliation and CI-failure deploy monitoring for `ai-market-backend`. One endpoint, one secret, event-type routing. Pillar: Council/Koskadeux orchestration. Origin: BQ-GITHUB-WEBHOOK-ROUTE-COLLISION-RECONCILE-VS-CIFAILURE-S933 (shipped S942, PR #181, squash 52693064).
- Owner: `unassigned`
- Last verified: `2026-06-18`
- Aliases: none
- Error signatures: none
- Status: current

## Gmail Drop Pipeline
- Path: `gmail-drop-pipeline.md`
- Purpose: **Doc status:** content current as of S1162 (party model + T-2026-000200 restore). Full Overview–K structural retrofit (BQ-RUNBOOK-STANDARD.md) still pending.
- Owner: `unassigned`
- Last verified: `2026-07-09`
- Aliases: none
- Error signatures: none
- Status: current

## Infisical Secrets Management
- Path: `infisical-secrets.md`
- Purpose: **Deployed**: S357 (2026-03-30) **URL**: https://secrets.ai.market **Railway Project**: `fe02d729-5921-4199-8e6a-2e026acc1326` **Replaces**: Doppler (demoted to archive-only, see `doppler-secrets.md`)
- Owner: `unassigned`
- Last verified: `2026-08-28`
- Aliases: none
- Error signatures: none
- Status: current

## Infrastructure Discovery
- Path: `runbooks/infrastructure-discovery.md`
- Purpose: **Fetch trigger:** locating any repository, service, secret, config, or deploy surface.
- Owner: `sysadmin`
- Last verified: `2026-07-17`
- Aliases: none
- Error signatures: credential_exposed, infrastructure_locator_guessed, secret_disclosure
- Status: current

## Issue Channel
- Path: `issue-channel.md`
- Purpose: The production Railway service `issue-channel-watcher` runs one replica. It reads GitHub, Railway, and Cloudflare, sanitizes provider data before persistence, stores canonical issues in the backend Postgres `issue_channel` schema, and publishes a safe snapshot. The snapshot is mirrored to `/Users/max/koskadeux-state/issue-channel/snapshot.json` for local operations and the open-items board.
- Owner: `mars`
- Last verified: `2026-08-30`
- Aliases: infrastructure failure channel, CI health board, issue channel watcher, issue channel poller
- Error signatures: observation_complete":false, executor_busy_no_lease, malformed_output, expired_unleased, duplicate_cardinality
- Status: current

## Issue-Channel Gate 2 Receipts Runbook
- Path: `issue-channel-gate2-receipts.md`
- Purpose: Owns the Gate-2 receipt (evidence) process for BQ-CI-HEALTH-VISIBLE-AT-SESSION-OPEN-S1511: the receipt environment lifecycle, credential identities, probe procedures, evidence package layout, and the failure modes met while producing receipts. Authority for WHAT must be proven is the Gate 2 spec `specs/BQ-CI-HEALTH-VISIBLE-AT-SESSION-OPEN-S1511-GATE2.md` at koskadeux-mcp commit `cdb8e50e` (section 8, V-1 through V-5b); this page never overrides it.
- Owner: `unassigned`
- Last verified: `2026-08-29`
- Aliases: none
- Error signatures: none
- Status: current

## Koskadeux Gateway Transport Runbook
- Path: `gateway-transport.md`
- Purpose: **Repo:** aidotmarket/koskadeux-mcp · **Local path:** `/Users/max/koskadeux-mcp` · **Entry:** `gateway_server.py` **Public:** `https://mcp.ai.market`, fronted by Cloudflare via the `cloudflared` tunnel `koskadeux` (launchd `com.koskadeux.cloudflared`; MUST-KEEP, do not decommission). A parallel Tailscale Funnel surface exists at `https://koskadeux-10.tail30cd96.ts.net` (also proxies `:8767`) but no DNS record points to it; it is a documented fallback, not the live path for `mcp.ai.market`. See `cloudflare-and-dns.md` (transport source of truth) and `mcp-gateway.md`. · **Local:** `:8767` **Process mgmt:** launchd `com.koskadeux.gateway` (wrapped by `infisical run`). The upstream tool server is a SEPARATE service: launchd `com.koskadeux.mcp`, `koskadeux_server.py` on `:8765`. Restarting the gateway does NOT restart the upstream.
- Owner: `mars`
- Last verified: `2026-06-15`
- Aliases: none
- Error signatures: kickstart non-zero / no fresh pid
- Status: current

## Koskadeux MCP — Gateway, Server, Transport & Session Lifecycle
- Path: `mcp-gateway.md`
- Purpose: Canonical operations runbook for the **internal Koskadeux MCP** that the two Claude instances (Vulcan + Mars, peers) drive Titan-1 through. For the **public/customer** MCP that exposes marketplace tools to external LLM clients, see `aimarket-mcp-server.md` — that is a different system. Consolidates the former `session-lifecycle.md` (now a stub pointing here). A future Overview–§K-conformant, possibly repo-local edition is tracked by the runbook-decentralization and autonomous-operations BQs; the central-vs-service location + final name are decided there. Until then this central runbook is authoritative. Filename kept as `mcp-gateway.md` deliberately so that gated relocation owns the rename.
- Owner: `unassigned`
- Last verified: `2026-08-25`
- Aliases: none
- Error signatures: none
- Status: current

## Lifecycle Emails
- Path: `runbooks/lifecycle-emails.md`
- Purpose: This page records the verified state and remaining evidence gaps for Build Queue item `build:bq-signup-lifecycle-emails-s1548`. It is grounded in exact `aidotmarket/ai-market-backend` revision `77dae96fd8a80fe768091061bc3846fb1b5e8d55`. The backend deployment `480d2fdc-c1c1-46a5-a915-3986c04ab84c` completed with status `SUCCESS` and image `sha256:8c9e1ffb594e90197447aebfbda3850216771210a3cbf9f4c1d06af4f9b75fd4`. The same deployed service set records beat deployment `3b46d1e6-5385-486f-a7f2-c2a99895f839` with image `sha256:fdc8443f9fa9c8291630c39ec5e246547a45b42953c0ddaaf1f864f5a62050f4` and worker deployment `8ae9b906-3a48-44d1-9783-bf029e6f055b` with image `sha256:d965f4cd1452ff6eba1b71236547d3901f2628df1ff829a984c31ac3455642ad`.
- Owner: `vulcan`
- Last verified: `2026-08-20`
- Aliases: none
- Error signatures: operator does not exist: userstatus = character varying
- Status: current

## Local SecOps Assistant (Titan-1)
- Path: `local-secops.md`
- Purpose: **Built**: S1115 (2026-07-04) **Host**: Titan-1 / `Koskadeux.local` (Mac Studio, M3 Ultra / 256GB) **Location on disk**: `/Users/max/local-secops/` **Purpose**: Rotate / update / expire / generate credentials with a fully-local model, so secret values never leave Titan-1 and no human has to type them. **Owner**: Vulcan/Mars (operator-invoked); registered in Living State at `infra:local-secops`.
- Owner: `unassigned`
- Last verified: `2026-07-10`
- Aliases: none
- Error signatures: none
- Status: current

## Marketing Tab (ops.ai.market)
- Path: `marketing-tab.md`
- Purpose: The Marketing tab in ops.ai.market displays the marketing plan with tasks, timelines, and progress. Seeded from real Excel data (March 2026 plan).
- Owner: `unassigned`
- Last verified: `2026-03-06`
- Aliases: none
- Error signatures: none
- Status: current

## Max Reporting — the End-of-Round Summary Discipline
- Path: `max-reporting.md`
- Purpose: The system-enforced comms contract: between the start of a round and its single end-of-round summary, an instance emits nothing Max-facing, with exactly two carve-outs. CORE §3 is the canonical statement; `infra:opening-prompt` carries the longer elaboration and points back to CORE §3. This runbook is the operator page: how to compose the summary, when a carve-out applies, how to diagnose violations, and how the rule may change.
- Owner: `mars`
- Last verified: `2026-07-31`
- Aliases: none
- Error signatures: summary contains codes/jargon or narrates process steps, continuing to improvise after reporting the stop, bundling status updates into the question, boot-contract test failure on the marker text
- Status: current

## Meet Records → CRM Pipeline
- Path: `meet-records-pipeline.md`
- Purpose: **LIVE / operational.** Google Meet "Gemini Notes" docs dropped into a watched Drive folder are auto-ingested and logged as `meeting` interactions against CRM contacts. Replaces the deprecated Fireflies.ai integration (S342). Party-native contacts are supported (S1078): a meeting attaches to any contact whether it has an old-style `crm_entity` id or only a `party_id`.
- Owner: `unassigned`
- Last verified: `2026-06-30`
- Aliases: none
- Error signatures: none
- Status: current

## Morning Briefing
- Path: `morning-briefing.md`
- Purpose: Sends a daily CRM briefing email to max@ai.market at 08:00 CET (07:00 UTC). Contains overdue tasks, pending tasks, recent activity, and action links per contact.
- Owner: `unassigned`
- Last verified: `2026-05-22`
- Aliases: none
- Error signatures: none
- Status: current

## Operator Telegram Notifications Runbook
- Path: `operator-telegram-notifications.md`
- Purpose: Both are distinct bot accounts (verified via `getMe`): the daemon token resolves to `@koskadeux_bot`, the backend to `@allai_agent_bot`.
- Owner: `unassigned`
- Last verified: `2026-07-31`
- Aliases: none
- Error signatures: none
- Status: current

## ops.ai.market — Ins{ai}ts Operations Dashboard
- Path: `ops-ai-market.md`
- Purpose: Internal operations dashboard for ai.market. Single-page React app at `https://ops.ai.market`, deployed on Railway as a static site.
- Owner: `unassigned`
- Last verified: `2026-08-26`
- Aliases: none
- Error signatures: none
- Status: current

## Peer Instance Discipline
- Path: `runbooks/peer-instance-discipline.md`
- Purpose: This runbook supersedes the retired Primary/Worker discipline: `vulcan` and `mars` are two cooperating instances of the same frontier model with equal authority over shell, git, dispatch, and Living State.
- Owner: `mars`
- Last verified: `2026-08-30`
- Aliases: peer-bus, peer-message-bus
- Error signatures: duplicate_claim_on_one_item, over_escalation_to_max, peer_message_silently_deduped, stale_handoff_trusted_at_open, unread_request_or_alert_at_dispatch, unrecognized_instance_attributed_artifact
- Status: current

## Policy Kernel Enforcement Gate
- Path: `runbooks/policy-kernel-enforcement.md`
- Purpose: As of 2026-07-27, enforcement is **ON**, `main` is `6b03e99e`, and the handler was restarted at `09:56:32`. The committed switch default remains the literal string `off`.
- Owner: `vulcan`
- Last verified: `2026-07-27`
- Aliases: none
- Error signatures: deployed_sha_stale, dispatch_terminal_state_missing_after_restart, policy_kernel_enforcement_setting_invalid, policy_kernel_not_evaluable, policy_kernel_preflight_indeterminate, dispatch_in_flight, dispatch_indeterminate, task_inventory_unreadable, policy_kernel_preflight_not_ready, policy_kernel_new_refusal, wrong_emergency_lever
- Status: current

## Product Elaboration
- Path: `runbooks/product-elaboration.md`
- Purpose: **Fetch trigger:** product design, positioning, or customer-surface decision.
- Owner: `max`
- Last verified: `2026-07-17`
- Aliases: none
- Error signatures: product_boundary_conflict
- Status: current

## Publish Paths Runbook
- Path: `publish-paths.md`
- Purpose: How a dataset becomes a marketplace listing. There is exactly one product publish route; everything else is management or a separately gated programmatic surface.
- Owner: `vulcan`
- Last verified: `2026-08-23`
- Aliases: none
- Error signatures: none
- Status: current

## Qdrant Sync Outbox
- Path: `qdrant-sync-outbox.md`
- Purpose: Production deploy sequence for S1194 P1: merge the feature branch, deploy the backend, let Alembic run the online migration at container start, and let the new claimed consumer start draining. The migration adds only nullable/defaulted columns and no CHECK/NOT NULL constraint, so old containers can continue writing `qdrant_sync_outbox` rows during Railway rolling deploy overlap. The S1194 pending-entity dedup script is optional afterwards; it is Max-gated maintenance to accelerate backlog catch-up, not a deploy prerequisite.
- Owner: `sysadmin`
- Last verified: `2026-07-16`
- Aliases: none
- Error signatures: stale/critical lag, rows return to dead_letter, 429/5xx from Vertex or Qdrant, confirmed missing point, source_version mismatch, or orphan count above threshold, confirmation query or Qdrant retrieval raises, processing rows remain stale, duplicate_rows remains nonzero
- Status: current

## Qdrant — Vector Database (hosting, auth, backups)
- Path: `qdrant.md`
- Purpose: Qdrant stores **derived** data only. It is NOT a system of record. Every collection is an embedding index rebuilt from Postgres:
- Owner: `sysadmin`
- Last verified: `2026-06-30`
- Aliases: none
- Error signatures: unauth returns 200, backend qdrant calls 401 after rotation, HTTP 401
- Status: current

## Queue-Overlay Archival Cutover (Reform WS11)
- Path: `queue-overlay-archival-cutover.md`
- Purpose: Retires the 8 sub-surfaces accreted on `config:parallel-worker-queue.body` (S577–S626) and moves Worker-pickup / Primary-replenish reads onto the dashboard + build-entity query path. Workstream 11 of 11 of the S621 single-source-of-truth reform. **EXECUTED AND COMPLETE through Gate 4 (S1117, 2026-07-04)** via the Max-approved zero-traffic archive-and-close path (How to operate.4). The live-traffic machinery in How to operate.2 remains documented for any future re-cutover of a surface that has real traffic.
- Owner: `unassigned`
- Last verified: `2026-07-04`
- Aliases: none
- Error signatures: none
- Status: current

## Reload when idle (T-2026-000602)
- Path: `runbooks/reload-when-idle.md`
- Purpose: One shell script runs on a timer/trigger. It first sources `scripts/runtime_state_paths.sh`. The S1456 candidate fixes its CC task, deployment-marker, and secret-refresh-request paths beneath the one `KOSKADEUX_DURABLE_STATE_DIR` root (default `/Users/max/koskadeux-state`), exporting `KD_CC_TASKS_DIR`, `KD_DEPLOYED_SHA_FILE`, and `KD_SECRET_REFRESH_REQUEST_FILE`. Legacy `KOSKADEUX_STATE_DIR`, `KOSKADEUX_CC_TASKS_DIR`, and `KOSKADEUX_PROBE_STATE_DIR` cannot redirect those records. The independent reload lock remains `/var/tmp/koskadeux/reload_when_idle.lock.d`; only an explicit isolated-test contract can override it.
- Owner: `mars`
- Last verified: `2026-08-14`
- Aliases: mcp-server-reload, reloader
- Error signatures: background build(s) running/queued; deferring, background-build check failed
- Status: current

## RTK Token Optimization
- Path: `rtk-token-optimization.md`
- Purpose: CLI proxy that reduces LLM token consumption by 60-90% on common dev commands. Intercepts shell commands from Council agents (CC, AG, MP) and compresses output before it hits their context windows.
- Owner: `unassigned`
- Last verified: `2026-07-15`
- Aliases: none
- Error signatures: none
- Status: current

## Runbook: Dual-Brand System — vectorAIz / AIM Channel
- Path: `dual-brand-vectoraiz-aim-channel.md`
- Purpose: **RETIRED (S996):** AIM Channel has been retired and replaced by **AIM Data** (de-skinned S751; standalone `aidotmarket/aim-data` repo + `ghcr.io/aidotmarket/aim-data` image). vectorAIz remains a separate, active product. This runbook is kept for historical brand-system context only — do not treat AIM Channel as a live product.
- Owner: `unassigned`
- Last verified: `2026-06-22`
- Aliases: none
- Error signatures: none
- Status: current

## Schema Migration Runbook
- Path: `schema-migration.md`
- Purpose: Alembic-based database schema migration procedures across ai-market-backend, koskadeux-mcp (Living State database), and any other service with versioned schema. Owned by **BQ-PROCESS-BUILD-QUEUE-INTEGRITY-S612** (P1, delegated migration-discipline section). Filed S612 per DS mandate that the runbook set was missing dedicated schema-migration coverage.
- Owner: `unassigned`
- Last verified: `2026-08-28`
- Aliases: none
- Error signatures: none
- Status: current

## Schema Rationalization / Quarantine / Drop
- Path: `schema-rationalization.md`
- Purpose: S1163 reduces the production Postgres schema by classifying every `public` table, moving empty unused tables to `quarantine`, watching for live misses, then dropping only after a quiet window and a unanimous Council gate. The hard safety invariant is execution-time empty-only enforcement under an exclusive table lock.
- Owner: `vulcan`
- Last verified: `2026-07-12`
- Aliases: none
- Error signatures: Set AUTHOR_DISPATCH_DATABASE_URL, DATABASE_PUBLIC_URL, or DATABASE_URL, status=PRELIMINARY or reason=stats_reset_changed, is an operator-controlled one-shot migration, empty-only quarantine invariant failed, external dependencies on quarantine tables, quarantine table has n_live_tup > 0 or n_tup_ins/upd/del > 0, relation '<quarantined_table>' does not exist or UndefinedTable for a quarantined table, relation 'orders' does not exist or crm_* does not exist, empty-only drop invariant failed, view or dependency blocker
- Status: current

## Seller SEO Validation Runbook
- Path: `seo-seller-validation.md`
- Purpose: Discovery health checks and readiness scoring for marketplace listings.
- Owner: `unassigned`
- Last verified: `2026-04-01`
- Aliases: none
- Error signatures: none
- Status: current

## SEO Infrastructure Runbook
- Path: `seo-infrastructure.md`
- Purpose: Internal infrastructure for search engine indexing and AI crawler discovery.
- Owner: `Max Robbins (max@ai.market)`
- Last verified: `2026-08-29`
- Aliases: none
- Error signatures: none
- Status: current

## Session Close Protocol
- Path: `session-close-protocol.md`
- Purpose: Vulcan and Mars are equal-authority peers. Each session is keyed by instance and opens, plans, operates, and closes independently; there are no role-based lanes, lifecycle slots, parent-session dependency, or peer close ordering.
- Owner: `unassigned`
- Last verified: `2026-07-31`
- Aliases: none
- Error signatures: none
- Status: current

## Session Lifecycle — consolidated into `mcp-gateway.md`
- Path: `session-lifecycle.md`
- Purpose: **Consolidated (S734).** The Koskadeux session lifecycle — `kd_session_open` / `kd_session_plan` / `kd_session_close`, the equal-authority two-instance peer model (independent open/close, with no lanes, slots, or close ordering), per-instance handoff, the boot gate (PLANNING → OPERATIONAL), the local SQLite registry, and recovery — now lives in the canonical Koskadeux MCP runbook: ## → see `mcp-gateway.md`, section **"Session lifecycle"** This stub is kept so existing links resolve. The eventual Overview–§K-conformant / relocated edition is tracked by the runbook-decentralization and autonomous-operations BQs.
- Owner: `unassigned`
- Last verified: `2026-07-17`
- Aliases: none
- Error signatures: none
- Status: current

## Session Open Protocol
- Path: `session-open-protocol.md`
- Purpose: The canonical Koskadeux session-open flow for the two trusted peers, `vulcan` and `mars`: handoff load, planning gate, and briefing review. Owned by **BQ-PROCESS-SESSION-LIFECYCLE-RELIABILITY-S612** (P0). Absorbs the prior `session_open_standup.md` per AG S612 mandate to eliminate two-file fragmentation.
- Owner: `unassigned`
- Last verified: `2026-08-30`
- Aliases: Koskadeux boot, kd_session_open, session planning gate, boot envelope
- Error signatures: PLANNING_GATE, BOOT_NON_TRUNCATABLE_OVER_BUDGET
- Status: current

## Session Registry Recovery
- Path: `session-registry-recovery.md`
- Purpose: **Model note.** As of CORE v9.2 (S811) Koskadeux runs **symmetric peers** (vulcan, mars) with no primary/worker lock slots. The session registry is an **instance-keyed `sessions` table** (one row per instance, plus a non-human `scratch` row) carrying a **durable monotonic high-water mark** (`session_seq` + Living State anchor `config:session-seq`), shipped S867. The older `infra:active-session-lock` primary/worker slot model and the iCloud lock-pointer are retired; recovery procedures here target the current model.
- Owner: `vulcan`
- Last verified: `2026-08-10`
- Aliases: none
- Error signatures: integrity_check_not_ok, schema_version_below_7, next_value_below_anchor, number_reused_or_regressed, restart_did_not_fire, migration_rollback_in_logs
- Status: current

## Stripe Connect Identity Bridge
- Path: `runbooks/stripe-connect-identity.md`
- Purpose: **Why this runbook exists.** On 2026-08-07 our first real seller was found to be live at Stripe with payouts enabled while our own seller record said his verification had not started. The diagnosis took two sessions and two operators because no document said which of our stores was supposed to be right. This runbook is that document. Ticket: T-2026-000572.
- Owner: `vulcan`
- Last verified: `2026-08-07`
- Aliases: connect-identity-bridge, seller-stripe-linkage
- Error signatures: kyc_status_absent_defaults_not_started, seller_profiles_connect_id_never_written, stripe_connect_user_update_zero_rows, two_connect_onboarding_endpoints_disagree, webhook_predicate_column_mismatch
- Status: current

## Support Ticket System — operations
- Path: `support-ticket-system.md`
- Purpose: **Owner surface:** ai.market support/trouble ticket engine (ai-market-backend `app/api/v1/endpoints/support.py`, `app/services/support_ticket_service.py`, `app/api/v1/dependencies/support_ticket_auth.py`, `app/tasks/scheduled.py`). One ticket system for dev, ops, and customer issues, operated by agents with human escalation on risk. **Spec source of truth:** `specs/BQ-SUPPORT-TICKET-SYSTEM-S811-GATE1.md` (Gate 1 design + Gate 2 R1 changelog + **Amendment A1 / S819** schema reconciliation). Do not relitigate the decision record in §2/§14 of that spec. **Last verified live:** 2026-06-22 (S987 — added agent management MCP tools `support_ticket_list/get/patch/message`, backend-shape verified vs `support.py`; S851 added dev-ticket/BQ taxonomy; engine MVP verified 2026-06-11/S819). Production deploy signal: the alembic fields on `api.ai.market/health` show the support + email-durability migrations at head.
- Owner: `unassigned`
- Last verified: `2026-06-22`
- Aliases: none
- Error signatures: none
- Status: current

## SysAdmin Operating Model (S1086)
- Path: `sysadmin.md`
- Purpose: spec plus live backend code; this page is the operator map.
- Owner: `sysadmin`
- Last verified: `2026-07-12`
- Aliases: none
- Error signatures: 401 or 403, last_result missing or stale, Not Authorized
- Status: current

## Task Spooler Build Queue
- Path: `runbooks/task-spooler-build-queue.md`
- Purpose: S1456 does not relocate any Task Spooler socket, slot marker, job spec, report, builder/test transcript, or `bridge_outcomes.db`: those defaults are already durable and have their own `KD_TS_*` / `KD_BRIDGE_*` contracts. It also does not make Task Spooler's queue server state a member of the five-record migration.
- Owner: `vulcan`
- Last verified: `2026-08-10`
- Aliases: build-queue-runner, codex-queue
- Error signatures: Codex FIFO unavailable, dispatch refused before model execution, queued row with idle slot, tsp command not found, no such job, builder output artifact missing or incomplete, cannot remove a running job, minimal_bridge_repo_unresolved, minimal_bridge_base_unresolved, jobs lost on kill
- Status: current

## Ticket-Probe Auto-Close (Two-Track Enforcement, Slice 1)
- Path: `ticket-probe-autoclose.md`
- Purpose: koskadeux-mcp tools/lifecycle/ticket_probe_reconciler.py (reconciler), tools/ticket_probe_runner.py (runner); ai-market-backend app/schemas/support_ticket.py + app/api/v1/endpoints/support.py (probe contract).
- Owner: `vulcan`
- Last verified: `2026-07-05`
- Aliases: none
- Error signatures: 422 http probe target host is not in TICKET_PROBE_HTTP_ALLOWLIST, 422 P0/P1 support tickets require a valid machine probe, {enabled:false}, {lock_acquired:false}, job runs but stats.enabled=false
- Status: current

## Titan-1 — the Mac Studio (dev workstation + local AI council + MCP host)
- Path: `titan-1.md`
- Purpose: Canonical map of the physical machine the whole operation runs from. Live source of the same data: `state_get("infra:titan-1")` (kept in sync with this doc). Related: `connectivity.md` (network), `mcp-gateway.md` (gateway/tunnel detail), `backup-and-recovery.md` (the scheduled jobs), `infisical-secrets.md` (machine-identity creds).
- Owner: `unassigned`
- Last verified: `2026-07-17`
- Aliases: none
- Error signatures: none
- Status: current

## two-factor-auth — TOTP Two-Factor Authentication Reference
- Path: `two-factor-auth.md`
- Purpose: Reference for the customer-facing TOTP (authenticator-app) two-factor flow in `ai-market-backend`: how a user enrolls, how the secret is stored, the server-side encryption key it depends on, and the failure modes and fixes. This is the runbook to read first whenever 2FA enable/verify returns a 500 on `ai.market/dashboard/settings`.
- Owner: `unassigned`
- Last verified: `2026-07-10`
- Aliases: none
- Error signatures: none
- Status: current

## Vulcan Configuration — Context Hydration & Memory Architecture
- Path: `vulcan-configuration.md`
- Purpose: Vulcan (Claude Opus) operates in Claude.ai with a Koskadeux MCP server connection. Context is hydrated through multiple layers at different stages. This runbook defines **what goes where** to prevent memory bloat and duplication.
- Owner: `unassigned`
- Last verified: `2026-03-24`
- Aliases: none
- Error signatures: none
- Status: current

## VZ Release Process
- Path: `vz-release-process.md`
- Purpose: Builds and publishes new vectorAIz versions. Creates GitHub releases, triggers GHCR Docker multi-arch builds. Also covers the Railway `vectoraiz-backend` production service deploy (auto-deploys from `aidotmarket/vectoraiz` main).
- Owner: `unassigned`
- Last verified: `2026-07-17`
- Aliases: none
- Error signatures: none
- Status: current

## Website Copy Standard
- Path: `website-copy-standard.md`
- Purpose: **Owner surface:** ai.market public website (aidotmarket/ai-market-frontend) and all customer-facing marketing copy. **Companion:** the write-like-max skill (Max's voice profile). This runbook is the site-copy addendum to it, approved by Max S811. **Last verified:** 2026-06-11 (S811 content refresh, PR #28 / main ebcf0ae).
- Owner: `unassigned`
- Last verified: `2026-06-11`
- Aliases: none
- Error signatures: none
- Status: current

## Work Checkout (Enforced Ownership)
- Path: `work-checkout.md`
- Purpose: Built under BQ-WORK-CHECKOUT-ENFORCED-OWNERSHIP-S1214 (Max directive S1214). The queue row is the checkout: `body.lifecycle.pickup_ownership = {"instance", "session_id", "claimed_at"}`. The peer bus remains notification-only, never the record. Specs: `koskadeux-mcp/specs/BQ-WORK-CHECKOUT-ENFORCED-OWNERSHIP-S1214-GATE1.md` and `-GATE2.md`.
- Owner: `mars`
- Last verified: `2026-08-09`
- Aliases: none
- Error signatures: owner_conflict 409 naming another live holder, not_claimable naming a terminal status, release reports success=true released=false reason=session_owner_changed, invalid_assignment_query
- Status: current
