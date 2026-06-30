# Meet Records → CRM Pipeline

## Status
**LIVE / operational.** Google Meet "Gemini Notes" docs dropped into a watched Drive folder are
auto-ingested and logged as `meeting` interactions against CRM contacts. Replaces the deprecated
Fireflies.ai integration (S342). Party-native contacts are supported (S1078): a meeting attaches to
any contact whether it has an old-style `crm_entity` id or only a `party_id`.

> Scope note: this runbook is accurate to current reality (S1078). It predates the §A–K runbook
> standard (`specs/BQ-RUNBOOK-STANDARD.md`); promotion to the full linter-enforced §A–K form
> (capability matrix, §I harness scenarios, lifecycle metadata) is a tracked follow-up, not yet done.

## Owner / escalation
Owner agent: CRM Steward (interaction writes) + SysAdmin (Drive watch / GCP). Escalation: Max.

## Architecture (current)

```
Google Meet call ends
  -> Gemini generates a Notes doc, saved to the "Meet Records" Drive folder
  -> PRIMARY: Drive push channel (changes.watch) fires
       -> POST /api/v1/webhooks/drive-notifications  (validates Google source IP + channel id/token)
       -> DriveWatchService.process_changes()
  -> SAFETY-NET: scheduled poll (drive_changes_poll) also calls process_changes() on an interval,
     so a missed push notification still gets picked up
  -> For each changed file in DRIVE_WATCH_FOLDER_ID whose name matches the Gemini-Notes pattern:
       MeetNotesIngestService.ingest_drive_file()
         -> fetch_document() (Drive export as text)  -> parse_notes() -> ParsedMeetingNotes
         -> writes a MeetNotesProcessed row (idempotency: no-ops if drive_file_id already processed)
         -> MeetNotesCRMService.process_parsed_note()
              -> for each participant: skip internal (self / internal domains),
                 match to a CRM person (party-first read, legacy fallback),
                 log a `meeting` interaction + a MeetNotesInteraction association row
```

Two interaction "shapes" are written depending on the matched person:
- `crm_party_interaction` — party-native person (party_id set, legacy ids null). This is the default
  in current prod (CRM_V2_WRITE_MODE=party_authoritative).
- `legacy_crm_interactions` — legacy person with a `crm_entity` id.

## Components (entry points)
- Webhook: `app/api/v1/endpoints/drive_webhooks.py:drive_notifications_webhook` (POST `/api/v1/webhooks/drive-notifications`)
- Drive watch + change processing: `app/services/drive_watch_service.py:DriveWatchService`
  (`register_channel`, `ensure_channel`, `renew_channel`, `process_changes`; meet-notes filename regex `MEET_NOTES_FILENAME_RE`)
- Ingest + parse: `app/services/meet_notes_ingest_service.py:MeetNotesIngestService`
  (`ingest_drive_file`, `parse_notes`, `fetch_document`)
- CRM attach: `app/services/meet_notes_crm_service.py:MeetNotesCRMService.process_parsed_note`
  (participant match `_match_participant`; write `_write_interaction_and_association`)
- Interaction write: `app/services/crm_service.py:CRMInteractionService.log_interaction`
- Scheduler jobs: `app/core/scheduler.py` — `drive_watch_renewal` (daily cron, calls `ensure_channel`)
  and `drive_changes_poll` (every `DRIVE_POLL_INTERVAL_MINUTES`, calls `process_changes`)
- Daily briefing (separate, reads meet-notes): `app/services/crm_briefing_service_gmail.py:CRMBriefingService.send_daily_briefing`
- Models: `app/models/meet_notes.py` (`MeetNotesProcessed`, `MeetNotesUnmatched`, `MeetNotesInteraction`)

## Configuration (env / Settings)
- `DRIVE_WATCH_FOLDER_ID` (alias `DRIVE_MEET_RECORDS_FOLDER_ID`) — watched Drive folder.
- `DRIVE_WEBHOOK_URL` — public webhook URL registered with the channel.
- `DRIVE_WEBHOOK_CHANNEL_TOKEN` — shared secret; webhook rejects mismatches. Required to register.
- `DRIVE_WATCH_CHANNEL_ID` — optional fixed channel id (otherwise a uuid is generated).
- `DRIVE_WATCH_EXPIRY_HOURS` — channel lifetime (default 24); renewed daily for safety.
- `DRIVE_WEBHOOK_IP_ALLOWLIST_ENABLED` — verify Google source IPs (default true).
- `DRIVE_POLL_INTERVAL_MINUTES` — safety-net polling interval.
- `MEET_NOTES_SELF_EMAIL` (default `max@ai.market`) and `MEET_NOTES_INTERNAL_DOMAINS`
  (default `["ai.market"]`) — participants skipped as internal (no self-interactions).
- `MEET_NOTES_CREATE_TASKS_ENABLED` (default false) — whether next-steps become CRM tasks.
- `MEET_NOTES_BRIEFING_WINDOW_DAYS` / `MEET_NOTES_BRIEFING_LIMIT` — daily briefing surface.
- CRM read/write routing (shared): `CRM_V2_WRITE_MODE=party_authoritative`,
  `CRM_V2_READ_PERSON=party_first` (must be party-enabled for party-native contacts to match).

Auth: Drive readonly via the shared Google OAuth tokens (same GCP internal consent screen as Gmail;
token in `GmailToken`). No separate 7-day expiry on the consent screen.

## Operate

### Activate / register the Drive watch (first time or after token/folder change)
1. Ensure `DRIVE_WATCH_FOLDER_ID`, `DRIVE_WEBHOOK_URL`, `DRIVE_WEBHOOK_CHANNEL_TOKEN` are set in the
   ai-market-backend Railway env (see `config:resource-registry`).
2. Registration happens automatically: the `drive_watch_renewal` scheduled job calls
   `DriveWatchService.ensure_channel()`, which registers a channel if none exists and renews before expiry.
   To force immediately, trigger that job (or call `ensure_channel()` / `register_channel()` once via a
   one-off in the prod env). `register_channel` also bootstraps the Drive `startPageToken`.

### Normal steady state
- Pushes hit the webhook -> process_changes. The poll job is the safety net for missed pushes.
- New Gemini-Notes files in the folder are ingested once (idempotent on `drive_file_id`) and attached.

### Backfill / re-attach unmatched meetings
When contacts are added *after* their meetings were first processed, the original run recorded the
participant in `meet_notes_unmatched` (reason `no_crm_person_match`). `ingest_drive_file` no-ops on an
already-processed file, so DO NOT re-ingest — instead reconstruct and re-run the attach step:
1. Confirm the contact now exists and is matchable (party person with the participant's email; party
   read route party-enabled).
2. For each target `drive_file_id`: delete its `meet_notes_unmatched` rows, rebuild a
   `ParsedMeetingNotes` from the stored `MeetNotesProcessed` JSON columns
   (`participants_json` / `topics_json` / `next_steps_json` / `details_json` + `title` / `summary` /
   `meeting_date`; `raw_text` is not needed by the attach step), then call
   `MeetNotesCRMService.process_parsed_note(processed, parsed, file_metadata={"id": drive_file_id, "name": ...})`.
   The party-native person now matches and a `meeting` interaction + association is written.
3. Reference one-off: `scripts/reattach_meet_notes_s1078.py` (DB-only; ran against prod via the public
   DB proxy with prod CRM_V2 read/write env mirrored). It dry-runs by default; `REATTACH_APPLY=1` commits.
There is no dedicated reprocess endpoint/agent tool yet — building one is a reasonable future capability
if backfills recur.

## Isolate / Repair (troubleshooting)

### No interactions appearing at all
- Drive watch channel expired or never registered: check `drive_watch_state` (channel_id, channel_expiry).
  The `drive_watch_renewal` job renews daily; if it's failing, check its logs and the Drive scope/token.
- Webhook rejecting pushes: source-IP allowlist (`DRIVE_WEBHOOK_IP_ALLOWLIST_ENABLED`) or channel
  id/token mismatch. Confirm `DRIVE_WEBHOOK_CHANNEL_TOKEN` matches the registered channel.
- Poll job (`drive_changes_poll`) is the safety net; if pushes are flaky, confirm it is scheduled and running.

### A file is not parsed
- File must be in `DRIVE_WATCH_FOLDER_ID` and match the Gemini-Notes filename pattern.
- It must be a Google Doc (exported as text). Parse failures record a `MeetNotesProcessed` row with
  status `skipped`/`failed` and an `error_message`.

### A participant is not attached (lands in meet_notes_unmatched)
- `no_crm_person_match`: no CRM person for that email at processing time. If the contact exists now,
  run the backfill/re-attach above. Party-native contacts only match when the internal/person read
  route is party-enabled (`CRM_V2_READ_PERSON=party_first`); a legacy-only read route will not find them.
- `ambiguous_crm_person_match`: more than one CRM person for the email — de-duplicate the contact.
- `missing_email`: participant had no email; name-only matching is not used for attach.
- Internal participants (self email / internal domains) are intentionally skipped, not attached.

### Agent reports a meeting/note "failed" but the row exists
- Read-model coercion (fixed S1078): `CrmPartyInteractionRead.key_takeaways` now tolerates a NULL
  value (coerced to `[]`). If a similar false-failure on read recurs, look for a non-nullable read-model
  field that the DB stores as NULL.

## Invariants (do not change without re-architecting)
- Non-custodial / metadata-only still holds — meeting summaries are CRM interactions, not customer data.
- allAI/CRM is the system of record meetings attach to; the briefing reads from it.
- A meeting attaches to a contact via `party_id` OR a legacy `crm_entity` id — never neither
  (`CRMInteractionCreate` requires at least one target; the legacy write path requires `entity_id`).

## Related
- Runbook router entry: `TOPIC-ROUTER.md` (Email / pipelines -> Meet records → CRM).
- CRM target state: `crm-target-state.md`. Gmail drop pipeline: `gmail-drop-pipeline.md`.
- Resource/secret locations: `config:resource-registry` (Living State).
