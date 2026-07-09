# Gmail Drop Pipeline

> **Doc status:** content current as of S1162 (party model + T-2026-000200 restore). Full §A–K structural retrofit (BQ-RUNBOOK-STANDARD.md) still pending.

## What it does

Emails cc'd or sent to `drop@ai.market` are automatically ingested into the CRM. Each sender/CC address is resolved to a CRM **party** (created if new, matched if existing), the email is logged as an interaction against each party, and an LLM generates a summary. Ingestion is **idempotent per Gmail `message_id`** via the `email_ingest_receipt` table, so redeliveries and retries never double-log.

## Gmail Filter (in max@ai.market settings)

There is a Gmail filter rule that must remain in place:

| Matches | Action |
|---------|--------|
| `to:(drop@ai.market)` | Skip Inbox, Apply label "CRM-Drop" |

This filter ensures drop emails don't clutter the inbox. The pipeline still picks them up because the Gmail watch monitors ALL mailbox changes (no `labelIds` filter), not just inbox changes.

**IMPORTANT:** If this filter is deleted, drop emails will land in the inbox instead of being labeled. The pipeline will still work, but the inbox will get noisy.

## How it works

```
Email arrives at drop@ai.market (cc or direct)
  → Gmail filter: skip inbox, apply "CRM-Drop" label
  → Gmail watch (users.watch, NO labelIds filter) detects mailbox change
  → Gmail publishes to GCP Pub/Sub topic: projects/aimarket-prod/topics/gmail-crm-drop
  → Push subscription POSTs to: https://api.ai.market/api/v1/webhooks/gmail
  → Backend webhook handler:
    1. Decodes Pub/Sub message (base64 historyId)
    2. Fetches new messages via Gmail API (historyTypes=messageAdded)
    3. Skips messages with DRAFT label (Apple Mail IMAP auto-saves)
    4. Checks if drop@ai.market is in To/CC addresses
    5. Routes to EmailIngestService for CRM processing
    6. Idempotency check: if this Gmail message_id already has an email_ingest_receipt, no-op (exactly-once; does NOT roll back the session)
    7. Resolve-or-create a party for the sender + each CC'd address (race-safe PartyIdentity on provider + external id)
    8. Log ONE interaction (type: email) per distinct email against each resolved party (force_create bypasses the time-window dedup so each real email is recorded once)
    9. LLM summarizes the email content (computed outside the DB transaction)
    10. Store summary + write email_ingest_receipt(message_id) to mark processed
```

## Key files

| File | Purpose |
|------|---------|
| `app/api/v1/endpoints/gmail_webhook.py` | Webhook endpoint |
| `app/services/gmail_watch_service.py` | Gmail watch setup, renewal, and notification processing |
| `app/services/gmail_service.py` | Gmail API client (auth, fetch, send) |
| `app/services/email_ingest_service.py` | Party resolve + interaction logging (sender + all CC) with per-`message_id` idempotency receipt |
| `app/models/email_ingest_receipt.py` + `alembic/versions/20260709_001_email_ingest_receipt.py` | Idempotency receipt table (unique `message_id`); migration is `has_table`-guarded (idempotent) |
| `app/domains/crm/core/service.py` | `resolve_or_create_party()` — race-safe party identity (ON CONFLICT DO NOTHING on `ix_party_identity_provider_ext`) |
| `app/domains/crm/operations/service.py` | `create_interaction(..., force_create)` — forwards the dedup-bypass flag |
| `app/services/crm_service.py` | Interaction logging + `last_interaction_at` update; `log_interaction(..., force_create)` honors the dedup bypass |
| `app/services/draft_service.py` | Email draft CRUD (uses `reviewed_at`, `sent_at`, `reviewer_notes`) |
| `app/api/webhooks.py` | Webhook routing |
| `app/core/config.py` | `GMAIL_TOPIC_NAME`, `GCP_PROJECT_ID` |

## Configuration

| Variable | Location | Value |
|----------|----------|-------|
| `GMAIL_TOPIC_NAME` | Railway env var | `projects/aimarket-prod/topics/gmail-crm-drop` |
| `GCP_PROJECT_ID` | Railway env var | `aimarket-prod` |
| Gmail OAuth tokens | Database (`gmail_tokens` table) | Refresh token auto-refreshes access token |
| Gmail filter | Gmail settings > Filters | `to:(drop@ai.market)` → Skip Inbox, label "CRM-Drop" |

## GCP Resources

| Resource | Details |
|----------|---------|
| Project | `aimarket-prod` |
| Topic | `gmail-crm-drop` |
| Subscription | `gmail-crm-drop-sub` (push to `https://api.ai.market/api/v1/webhooks/gmail`, 60s ack) |
| Auth account | `max@ai.market` |

## Gmail watch renewal

Gmail watches expire after 7 days. The scheduler (`app/core/scheduler.py`) calls `renew_all_watches()` daily to keep them alive. The watch is also renewed on app startup (`_gmail_watch_startup` in `main.py`).

## OAuth tokens and the GCP "Testing" problem

The GCP OAuth app (`aimarket-prod`) may still be in "Testing" mode. In testing mode, **refresh tokens expire after 7 days**. This silently kills both this pipeline AND the morning briefing.

**Permanent fix:** Publish the GCP OAuth app to "Production" in the [GCP Console OAuth consent screen](https://console.cloud.google.com/apis/credentials/consent?project=aimarket-prod). Production apps get refresh tokens that don't expire (unless manually revoked).

**If tokens expire (manual re-auth required):**
```bash
cd ~/Projects/ai-market/ai-market-backend
python3 scripts/setup_gmail_auth.py  # secrets loaded from Railway env vars
```
This opens a browser for Google consent. The script saves the new refresh token, but it connects to `postgres.railway.internal` which isn't reachable from Titan-1. Push the token to Railway DB manually:
```bash
echo "UPDATE gmail_tokens SET refresh_token = '<NEW_TOKEN>', updated_at = NOW() WHERE email_address IN ('max@ai.market', 'ally@ai.market');" | railway connect Postgres
```
Then redeploy to renew the watch:
```bash
railway redeploy --yes
```

## Auto-follow-up on new contacts

When the email drop pipeline creates a **new** contact (not an upsert of existing), a CRM task is automatically created:

- **Type:** `follow_up`
- **Due date:** 7 days from contact creation
- **Description:** "Follow up with {name} — new contact, check if outreach needed"
- **Surfaces in:** Morning CRM Briefing (pending tasks section)
- **Non-blocking:** If task creation fails, the contact is still created

This applies to ALL contact creation paths: email drop pipeline, CRM steward manual adds, and API creates — they all go through `CRMEntityService.create_person()`.

**Code:** `app/services/crm_service.py` → `_create_new_contact_follow_up()`  
**Shipped:** S364 — commit `ce36fb8`

## Party model, idempotency & the T-2026-000200 restore

The pipeline uses the CRM **party** model, not the legacy contact model. Each participant (sender + every CC) is resolved via `resolve_or_create_party()`, keyed on a `PartyIdentity` (provider + external id). It is **race-safe**: concurrent arrivals for the same address use `INSERT ... ON CONFLICT DO NOTHING` on `ix_party_identity_provider_ext`, then re-resolve the winning party and delete any orphan party created on the losing branch. Interactions are `CrmPartyInteraction` rows.

**Exactly-once ingestion.** Every processed Gmail message writes an `email_ingest_receipt(message_id UNIQUE)`. On (re)delivery the service checks for an existing receipt and no-ops if present — it does NOT roll back the session, so the no-op path stays idempotent. The LLM summary is computed outside the DB transaction.

**One interaction per real email.** `log_interaction()` normally applies a short time-window dedup. The drop pipeline passes `force_create=True` (plumbed `email_ingest_service → operations.create_interaction → crm_service.log_interaction`) so each distinct inbound email is recorded exactly once, without the window collapsing two genuinely-separate emails into one.

**T-2026-000200 (restore).** The drop pipeline had regressed (emails silently not landing). Restored S1160, Gate-3 closed S1162. Two HIGH fixes: HIGH-1 = the `force_create` dedup bypass above; HIGH-2 = the race-safe party identity above.

### Migration idempotency lesson (S1162 incident)

The first prod deploy of this work FAILED with `asyncpg DuplicateTableError: relation "email_ingest_receipt" already exists`. Root cause: an earlier partial deploy of the same revision created the table (and processed a few real emails) in prod but never stamped `alembic_version`, so every later deploy re-ran `CREATE TABLE` and died. **Prod stayed up the whole time on the prior build.** Fix: the migration's `upgrade()`/`downgrade()` are now guarded with `sa.inspect(bind).has_table(...)`, so the revision stamps cleanly when the table already exists. General rule: on a `DuplicateTableError` during deploy, compare the physical schema against `alembic_version` before touching anything — the object may exist from a partial run while alembic has no record of the revision. Do NOT drop the table; it may hold real rows.

## How to verify

1. **Check Pub/Sub subscription exists:**
   ```bash
   gcloud config set account max@ai.market
   gcloud config set project aimarket-prod
   gcloud pubsub subscriptions list
   ```

2. **Check webhook endpoint is live:**
   ```bash
   curl -s https://api.ai.market/health
   ```

3. **Test the pipeline:** CC `drop@ai.market` on an email and check CRM for new contact/interaction within 1-2 minutes.

4. **Check Gmail watch is active:** Look at scheduler logs or trigger a redeploy (watch renews on startup).

5. **Check Gmail filter:** Gmail settings > Filters > verify `to:(drop@ai.market)` → Skip Inbox, Apply label "CRM-Drop".

## When it breaks

| Symptom | Likely cause | Fix |
|---------|-------------|-----|
| Emails not appearing in CRM | Gmail OAuth refresh token expired (7-day expiry in Testing mode) | Re-run `setup_gmail_auth.py`, push token to Railway DB, redeploy |
| Emails not appearing in CRM | Gmail watch expired | Redeploy backend (watch renews on startup) |
| Emails not appearing in CRM | Gmail filter deleted | Re-create filter in Gmail settings: `to:(drop@ai.market)` → Skip Inbox, Apply "CRM-Drop" |
| Pub/Sub 403 errors | GCP auth token expired | `gcloud auth login --account=max@ai.market` |
| Webhook returning 500 | Railway deploy issue | Check Railway logs for ai-market-backend |
| "GMAIL_TOPIC_NAME not configured" | Railway env var missing | Check Railway service variables |
| New emails not detected | historyId gap | Stop and re-create watch (redeploy) |
| CC'd contacts missing interactions | Bug in `email_ingest_service.py` — only primary contact logged | Fixed in S364 (`aee7796`). If regresses, check `process_email()` step 4 CC fan-out loop |
| Emails silently dropped, no errors in logs | `db.begin()` inside active transaction kills ingest | Fixed in S370 (`ef36f82`). Use `begin_nested()` instead. Check `email_ingest_service.py` transaction handling |
| Gmail labelAdded events ignored | Webhook only handled messageAdded historyType | Fixed in S370 (`8bf4b87`). Gmail filter applies label → triggers labelAdded, not messageAdded. Both must be handled |
| Duplicate PROCESSED drafts in Gmail | Apple Mail IMAP auto-saves trigger messageAdded events for drafts | Fixed in S372 (`eb26181`). `_process_single_message` and `_reprocess_for_crm` now skip messages with DRAFT label |
| `last_interaction_at` always null | `crm_service.py` not updating entity after interaction insert | Fixed in S364 (`aee7796`). Check `CRMInteractionService.log_interaction()` |
| `column "reviewed_at" does not exist` | `email_drafts` table missing columns | Run pending migration or: `ALTER TABLE email_drafts ADD COLUMN IF NOT EXISTS reviewed_at TIMESTAMPTZ` (also `sent_at`, `reviewer_notes`) |
| Same email logged as duplicate interactions, or two different emails collapsed into one | Time-window dedup applied to ingest | `force_create=True` must flow email_ingest_service → operations.create_interaction → crm_service.log_interaction (T-200 HIGH-1) |
| Party/interaction lost when the same address arrives on concurrent emails | Party-identity race | `resolve_or_create_party()` must use ON CONFLICT DO NOTHING on `ix_party_identity_provider_ext` + orphan cleanup (T-200 HIGH-2) |
| Deploy fails: `DuplicateTableError: relation "email_ingest_receipt" already exists` | Table created by an earlier partial deploy; `alembic_version` never stamped | Migration is `has_table`-guarded (idempotent) — redeploy self-heals. If it recurs, compare physical schema vs `alembic_version`; do NOT drop the table (holds real receipts) |

## History of breakage

- **S222:** Built. Verified S223 (Pub/Sub subscription confirmed).
- **S341:** Pipeline down for days. Root cause: GCP OAuth refresh token expired (app in Testing mode). Fixed by re-running setup_gmail_auth.py and pushing token to Railway DB. Runbook updated to document Gmail filter, OAuth expiry, and manual token refresh procedure.
- **S361:** Topic renamed from `gmail-push` to `gmail-crm-drop`. GMAIL_TOPIC_NAME set in Railway. Watch activated S360.
- **S372:** Apple Mail IMAP draft auto-saves creating duplicate PROCESSED drafts. Root cause: `_process_single_message` processed all messageAdded events including drafts. Fix: DRAFT label check added to skip draft messages in both `_process_single_message` and `_reprocess_for_crm`.
- **T-2026-000200 (S1160/S1162):** Drop pipeline regressed (emails not landing). Restored on the party model with a per-`message_id` idempotency receipt. Gate-3 closed S1162 (HIGH-1 `force_create` dedup bypass, HIGH-2 race-safe party identity). First prod deploy failed on `DuplicateTableError` (receipt table existed from an earlier partial deploy, alembic unstamped); resolved by making the migration idempotent (`has_table` guard). Live in prod S1162 (merge `ccaf91a3`); prod alembic head advanced to `t200_email_ingest_receipt`, existing 4 receipt rows preserved.

## Built

S222 — commit `f85c77e`. Verified S223 (Pub/Sub subscription confirmed).
Updated S341 — documented Gmail filter, OAuth token expiry, and recovery procedure.
Updated S364 — Fixed 4 bugs: (1) CC contacts now get interactions logged, (2) `last_interaction_at` updates on CRM entities, (3) Oren@electrified.net added manually, (4) `email_drafts` missing columns migration added. Commits: `aee7796` (bugs 1-2), `2f0b9b1` (bug 4 migration), `ce36fb8` (auto-follow-up).
Updated S360 — corrected topic/subscription names to `gmail-crm-drop`.
Updated S370 — Fixed 2 bugs: (1) `db.begin()` inside active transaction silently killed all CRM ingest (`ef36f82`, `begin_nested()` fix), (2) Gmail `labelAdded` events not handled (`8bf4b87`). Verified E2E: email → contact created + interaction logged.
Updated S372 — Fixed DRAFT duplication bug: Apple Mail IMAP auto-saves triggered messageAdded events, handler processed drafts as real emails. DRAFT label check added (`eb26181`).
Updated S1162 — T-2026-000200 restore: party-model ingest + `email_ingest_receipt` idempotency. Gate-3 closed; deploy-drift incident (`DuplicateTableError`) fixed via an idempotent `has_table`-guarded migration. Merges: `9515df7f` (restore) + `ccaf91a3` (idempotent migration). Verified: prod deploy SUCCESS, `/health` 200, alembic head = `t200_email_ingest_receipt`, receipt data preserved, 10/10 real-PG integration suite. NOTE: content-accuracy update only — full §A–K structural retrofit still pending.
