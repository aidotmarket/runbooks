# Meet Records → CRM Pipeline

## Overview
Google Meet's Gemini Notes feature saves meeting summaries to a "Meet Records" folder in Google Drive. This pipeline automatically logs those notes to CRM contacts.

**Replaces:** Fireflies.ai integration (deprecated S342)
**BQ:** BQ-MEET-RECORDS-CRM
**Status:** Planned (S342)

## Architecture

```
Google Meet call ends
  → Gemini generates notes
  → Saved to Google Drive "Meet Records" folder
  → Drive push notification fires (changes.watch)
  → Backend webhook receives notification
  → Fetches file content via Drive API (export as text/plain)
  → Parses Gemini Notes format
  → Matches participants to CRM contacts (email-first, name fallback)
  → Creates missing contacts
  → Logs interaction as "call" type with summary + next steps
```

## Gemini Notes Format (Parsed Fields)

```
[Date]                          → meeting date
[Title]                         → meeting title / interaction summary
Invited [emails] [names]        → participant identification (EMAIL-FIRST matching)
Summary [paragraph]             → CRM interaction body
[Topic headers + body]          → detailed notes
Details [• bullets w/ timestamps] → enrichment
Suggested next steps            → action items per person
```

### Key Parsing Rules
- `Invited` line contains participant emails inline with names (e.g. `david.rabuka@acrigen.com Max Robbins`)
- Summary is always the first paragraph after "Summary" header
- Next steps are structured as `{Person} will {action}` — map to CRM tasks
- Timestamps in Details bullets are `(HH:MM:SS)` format

## CRM Integration

### Contact Matching (Priority Order)
1. **Email match:** Extract emails from `Invited` line → query `CRMPerson.email`
2. **Name fallback:** Extract names → fuzzy match on `CRMPerson.full_name`
3. **Auto-create:** If no match, create new contact with name + email + meeting date

### Interaction Logging
- **Type:** `call`
- **Content:** Summary + topic highlights + suggested next steps
- **Summary field:** Meeting title

## Dependencies
- Google Drive API (readonly scope) — uses same GCP OAuth tokens as Gmail
- Same GCP Internal consent screen (no 7-day expiry)
- Same Pub/Sub infrastructure (new topic or shared with Gmail)

## Related Services
- `gmail_watch_service.py` — pattern this mirrors
- `fireflies_service.py` — being replaced (soft-deprecated)
- `email_ingest_service.py` — CRM contact matching patterns
- `com.koskadeux.fireflies-sync` LaunchAgent — unloaded in S342

## Troubleshooting

### Drive watch not receiving notifications
1. Check Drive API scope is enabled in GCP Console
2. Verify `DRIVE_TOPIC_NAME` in Doppler/settings
3. Check Drive watch channel hasn't expired (7-day lifecycle, renewed daily)
4. Verify webhook endpoint is accessible: `POST /api/v1/webhooks/drive-notifications`

### Files not being parsed
1. Check file is in "Meet Records" folder (folder ID in config)
2. Verify file is a Google Doc (Gemini Notes are Google Docs, not PDFs)
3. Export as `text/plain` via Drive API — check for format changes

### Contact not matched
1. Check CRM for existing contact by email
2. Verify email format in Gemini Notes hasn't changed
3. Check logs for parsing errors on `Invited` line
