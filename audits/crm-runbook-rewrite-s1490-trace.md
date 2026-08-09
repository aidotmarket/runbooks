# CRM runbook rewrite, S1490 — trace matrix

Retrofit trace for `runbooks/crm.md`, which supersedes three legacy root-level documents.

**Source documents (superseded).**

| File | Words | Last real update | Indexed in CATALOG/TOPIC-ROUTER/README |
|---|---|---|---|
| `crm-architecture.md` | 2,868 | 2026-07-10 (`1795431`) | No |
| `crm-pipeline.md` | 1,093 | 2026-07-02 (`b447a07`) | No |
| `crm-target-state.md` | 7,010 | 2026-07-03 (`0c1d397`) | No |
| **Total** | **10,971** | | |

**Result.** `runbooks/crm.md`, 6,406 words, minus 41.6 percent. Conformant to
BQ-RUNBOOK-STANDARD §A–§K, `runbook-lint --mode strict` fail=0 warn=0.

## Trace: where each source topic landed

| Source topic | Source location | Destination | Disposition |
|---|---|---|---|
| V1 data model, 14 `crm_*` tables described as "Active (production)" | `crm-architecture.md` §Data model | `crm.md` §C.1 "Deleted tables" | **CORRECTED.** All 14 dropped 2026-07-03 by `s1113_drop_legacy_crm_tables`. Verified absent in production. |
| `crm_persons` table name | `crm-architecture.md` §Data model | `crm.md` §C.1 naming-trap note | **CORRECTED.** Never existed. The real, now-deleted, name was `crm_people`. |
| V2 domain layer "emerging, partial" | `crm-architecture.md` §Data model V2 | `crm.md` §C, §C.1, §C.2 | **PROMOTED.** The party model is the sole live read and write path, not an emerging one. |
| Service file map with line counts | `crm-target-state.md` Appendix A | `crm.md` §C architecture table | **CORRECTED.** 3 of 15 files no longer exist. `crm_service.py` was listed at 794 lines against roughly 4,000 actual; `crm_steward_skills.py` at 1,711 against a file 80x larger than that figure implies. Line counts dropped rather than restated, because they rot. |
| Steward skill list, "28 `@skill`-decorated" | `crm-target-state.md` §3 | `crm.md` §D | **CORRECTED.** 29 registered in `CRM_SKILLS`: 9 read, 19 write, 1 health. |
| Pipeline capability, documented as working | `crm-architecture.md`, `crm-pipeline.md` | `crm.md` §B (BROKEN), §F-01, §G-01 | **CORRECTED.** Backing tables deleted. Live `crm_request` call reproduced the failure. |
| Accounting interface | `crm-target-state.md` §4.1 | `crm.md` §C, §E-04, §H.1 Invariant 3 | **RETAINED.** Strongest section of the source. Canonical Stripe Connect identity claim re-verified: 7 `stripe_connect` rows in `party_identity`. |
| Support interface, "Ticket ↔ CRM linkage: No" | `crm-target-state.md` §4.2 | `crm.md` §C, §F-04, §G-04 | **CORRECTED.** The linkage was built. `support_ticket.requester_party_id` and `org_party_id` are real indexed FKs to `party.id`. Populated on 0 of 580 rows. |
| Sales interface | `crm-target-state.md` §4.3 | `crm.md` §B, §D | **FOLDED.** Per-capability status now carries evidence and a last-verified date. |
| "When it breaks" tables | `crm-architecture.md`, `crm-pipeline.md` | `crm.md` §F | **RETAINED AND EXTENDED.** Shape was sound. Rebuilt on verified causes, with §G repair back-references. |
| External MCP endpoint removal (S1099) | `crm-architecture.md` §CRM Access And Auth | `crm.md` §B (DEPRECATED), §F-11, §H.1 Invariant 4 | **RETAINED.** Still accurate. |
| Phase D cutover narrative, status blocks R7–R17 | `crm-target-state.md` §7 and header | Not carried forward | **RETIRED.** Migration history, superseded by the outcome. Recoverable from git history of the archived file. |
| BQ-CRM-* programme tracking, gate transcripts | `crm-target-state.md` throughout | Not carried forward | **RETIRED.** Build Queue state belongs in Living State, not a runbook. |
| Test standard and acceptance matrix | `crm-target-state.md` §5 | Not carried forward | **RETIRED.** Superseded by §B Test Coverage column carrying per-capability evidence. |

## New content with no source antecedent

| Content | `crm.md` location | Why it is new |
|---|---|---|
| Field-level data dictionary, 7 tables, every column typed with nullability and meaning | §C.2 | Max directive S1490: a new AI must be able to diagnose without system access. No source document contained a single column-level specification. |
| Production row counts for all 30 live tables | §C.1 | Lets a reader tell an empty-by-design table from a defect without querying. |
| Live enumerated values (party types, identity providers, roles, task statuses, interaction types) | §C.2 | Source documents listed 6 interaction types; production carries 8. |
| Dead model-class inventory and the 33 legacy select sites | §C.1 | The landmine map. Distinguishes unreachable dead code from the three reachable pipeline sites. |
| §H.1 Invariant 1, deleted tables stay deleted | §H.1 | Directly prevents the failure mode the superseded documents caused. |
| §H.1 Invariant 5, no runtime table creation | §H.1 | Carried across from the T-2026-000580 money-path finding. |

## Evidence

All production figures measured 2026-08-09 against the live database (Alembic head
`s1299_c1_corpus_control_plane`). Live behavioural checks: `crm_search_interactions` returned
the expected party record; `crm_request` with a pipeline question reproduced §F-01.

## Open items raised by this rewrite

1. Pipeline skills are broken in production. Delete or rebuild on `crm_opportunity` — Max decision, see §G-01.
2. Support ticket party link never populated, 0 of 580 — see §G-04.
3. 33 legacy select sites remain in four live files. Dead but present.
