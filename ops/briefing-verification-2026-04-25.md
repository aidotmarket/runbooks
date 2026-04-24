# Daily CRM Briefing — First Real-Content Verification
**Date**: 2026-04-25 07:00 UTC (first delivery after S499 data backfill + S501/S502 Chunk A fixes)
**Owner**: Max / Vulcan next-session
**Gate**: BQ-CRM-USER-SCOPING-BACKFILL-AND-FALLBACK AC11 — contact_count > 0 for 7 consecutive days starts today

## Pre-delivery state (verified S503)

- Backend HEAD: `32688f2` (all Chunk B commits on main)
- 550 CRM rows owned by Max's user_id `0a3eb2e1-8cc1-4ea9-84ce-542491784be3` (369 people + 26 orgs + 54 tasks + 101 interactions)
- 28 overdue tasks owned by Max (verified via direct SQL, S501)
- Scheduler: `app/core/scheduler.py:223` → `crm_briefing_service_gmail.CRMBriefingService` → fires 07:00 UTC
- Recipient hardcoded: `max@ai.market`
- Known matching content from April 15 PDF: Richard Yu ×4 tasks, Sridhar Iyengar ×2, Perttu Jalkanen ×4, Marvin Thiele ×1, Alexej Ziegler ×1

## BLOCKER (ongoing S503)

**GitHub Actions billing suspended on `aidotmarket/ai-market-backend`.** CI cannot verify any pushes after `3e5222b`. Does NOT block the briefing itself — Railway auto-deploys on push and does not depend on GH Actions passing. Briefing will fire regardless.

## Verification steps (tomorrow 07:00 UTC+)

### Step 1 — Did the scheduler job fire?
```bash
railway logs --service ai-market-backend --tail 500 2>&1 | grep -E "morning_briefing|send_daily_briefing"
```
Expected: `"Running scheduled job: morning_briefing"` at ~07:00 UTC,
followed within ~30s by `"Morning briefing sent successfully (message_id=...)"` or
`"Morning briefing completed successfully: ..."`.

### Step 2 — Did Max actually receive it?
Max checks Gmail inbox at max@ai.market around 07:00 UTC / 09:00 CEST.
Subject line pattern (from briefing service): `"CRM Daily Briefing — YYYY-MM-DD"` or similar.
Expected content: ≥ 20 overdue task cards, Richard Yu's 4 tasks present, Sridhar present.

### Step 3 — If briefing is empty/missing, manual trigger
```bash
# On Railway production
curl -X POST https://ai-market-backend-production.up.railway.app/api/v1/briefing/trigger \
  -H "Authorization: Bearer $INTERNAL_API_KEY"
```
Then re-check Gmail + logs. If still empty, the data layer is not the issue (already verified);
check (a) Gmail send credentials, (b) scheduler.py import path, (c) BRIEFING_RECIPIENT env var.

### Step 4 — Did B3's fallback engage? (should NOT fire)
```bash
railway logs --service ai-market-backend --tail 500 2>&1 | grep "crm_briefing_scoping_fallback_engaged"
```
Expected: **no log lines**. Max's user has real owned rows, so the scoped query returns content and
the fallback is dormant. If fallback engages today, something is wrong with S499 backfill integrity.

### Step 5 — Record evidence
Screenshot the Gmail inbox (not the full body) + paste the 3-line-summary from Railway logs into
this file as an evidence block. This is Day 1 of the AC11 7-consecutive-day window.

## Rollback path if briefing delivers wrong/empty content

S499 backfill rollback is documented in Living State `body.revised_three_tracks.track_1_emergency_data_restoration.rollback_path_if_needed`. Do NOT roll back unless a subsequent bug is traced to the backfill itself.

If B3 fallback logic is traced as the cause of wrong content:
```bash
cd /Users/max/Projects/ai-market/ai-market-backend
git revert 0ac547e 32688f2  # revert B3 + B3-fix, keeps B1+B2+B4
git push origin main
```

## Follow-up (Day 2–7)

Each day 2026-04-25 through 2026-05-01, record briefly in this file:
- Date
- Delivered? (Y/N)
- Overdue task count
- Any fallback log lines
- Any anomalies

Day 7 = AC11 satisfied.
