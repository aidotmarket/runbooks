# Dev Trouble-Ticket Lifecycle Runbook

## §A. Header
Owner: both instances. Scope: dev-class support tickets (T-YYYY-NNNNNN) — issues in existing systems. Created S1164 discharging debts S1164-D1/D2/D3. Not for BQs (new development) or customer tickets.

## §B. Triage & ground-truth verification (D1)
Before acting on any dev ticket: (1) `support_ticket_get(public_ref, include_messages=true)`; (2) verify every claim against ground truth — open the cited source at file:line, reproduce the symptom live where safe (curl the endpoint, query prod read-only via `scripts/test-db-dsn.sh` + psql), check prod schema/env rather than trusting the ticket text; (3) confirm the root cause yourself before dispatching a fix. A ticket is a lead, not a spec.

## §C. Fix routing (D2)
Trouble-ticket-class fixes route to MP (Codex) or CC — never instance-authored beyond trivial mechanical pre-merge fixes (e.g. migration re-parent). Dispatch `council_request mode=build` with: verified root cause at file:line, required fix, explicit scope bounds, test requirements, branch name, "push, do NOT merge". Runbook refs required by the gate. This applies to koskadeux-mcp self-fixes too (e.g. the S1164 close-gate fix): same build path, same review; the only extra step is that koskadeux-mcp code changes go live on gateway kickstart at a session boundary, never mid-session.

## §D. Review & merge
Reviewer ≠ builder, minimum one round scaled by risk (Design Charter). KNOWN GAP T-2026-000206: review-mode base/dispatch_sha does NOT inline diffs to DS/GLM — inline the diff manually in the task text, or use AG. Merge with `KD_ALLOW_MAIN_PUSH=1` after conflict-check; backend merges: run `alembic heads` on the branch first (single head or the deploy fails).

## §E. Status updates & closure (D3)
Every material step gets `support_ticket_message(action=post, direction=internal)` with: what/root cause/fix/commits/review verdicts/deploy+verify evidence. Status via `support_ticket_patch`: in_progress when work starts or fix awaits activation; resolved only after live verification (Gate-4). Mirror the outcome to Living State (`state_request action=event`) and peer-notify Mars if shared surfaces moved. Ticket not resolved = say what observation resolves it.

## §F. Failure table
- Fix merged but behavior unchanged → check activation path (Railway deploy for backend; gateway kickstart for koskadeux-mcp).
- Job/probe dead after fix → read job.last_error verbatim first; reproduce the exact call manually before re-dispatching.
