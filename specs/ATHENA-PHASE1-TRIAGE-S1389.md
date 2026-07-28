# ATHENA-PHASE1-TRIAGE-S1389

Status: DRAFT FOR MAX SIGNATURE  
Owner: Athena  
Session: S1389  
Repository: `aidotmarket/runbooks` only  
Base: `origin/main` at `876b2bde6aad003f271e8f42bc8d76e94e0f7465`  
Binding charter: `specs/ATHENA-CHARTER-S1387.md` at the same SHA  
Programme authority consulted: `specs/RUNBOOK-ORGANIZATION-PLAN-S1387.md` at `9c025c529822d60349257de6e3a695501730984b` and `specs/BQ-RUNBOOK-STANDARD.md` in full

## 1. Purpose and result

This is the Phase 1 triage record required by Athena's charter. It freezes the first promotion chunks, gives Max a recoverable archive kill list to sign, and records the part Athena cannot decide because her charter forbids protected-domain work.

Ground truth at the base SHA is 98 runbook documents in the repository root plus `runbooks/`, 17 ACTIVE catalog members, and 81 unindexed documents. The 81-file set was derived from Git paths and `CATALOG.json`, not from README prose. Of those 81 documents:

| Outcome | Count | Meaning |
|---|---:|---|
| Rewrite | 15 | Preserve as an independent authority and promote to the A-through-K standard. |
| Merge | 6 | Fold into the named surviving authority with machine-verified content containment; retire the source only after containment and link checks pass. |
| Archive | 3 | Proposed recoverable retirement, subject to Max's signature and the pre-move controls below. |
| Protected-domain owner triage required | 57 | No Athena recommendation. The file may cover auth, security, payments, production data, or customer data; Mars or Vulcan must triage it. |
| **Total** | **81** | Exact unindexed estate at the base SHA. |

This is deliberately conservative. A false archive decision costs more than carrying a document for another round.

## 2. Load-bearing provenance findings

1. The Athena charter is on `origin/main` exactly where the handoff says it is, at `876b2bde6aad003f271e8f42bc8d76e94e0f7465`.
2. The approved organization plan is not on `origin/main`, despite the handoff saying it is. Git ground truth places it on the remote-equal branch `spec/runbook-organization-plan-s1387` at `9c025c529822d60349257de6e3a695501730984b`. The Athena handoff and the s1229 assignment record identify that document as the approved Gate 1 amendment. This triage cites the exact branch SHA and does not claim the file exists on main.
3. The opening tool misrouted Athena to Vulcan's handoff, exactly as the Athena seed warned. The correct handoff was read from `infra:handoff:instance=athena`; no Vulcan work was claimed or used.
4. An early metadata/read batch exposed protected-surface content in `aimarket-mcp-server.md`, `allai-agents.md`, `marketing-tab.md`, and `seo-infrastructure.md`. Athena stopped using those reads, placed those files in the protected hold, and made no content recommendation from them. This record does not hide that boundary error.

## 3. Decision rules

- **Rewrite** when the document has a distinct continuing operational subject and no proven surviving authority can absorb it without becoming a catch-all.
- **Merge** when the source substantially overlaps a surviving authority or is a legacy fragment of a planned consolidation. Every non-blank source line must be accounted for in the destination; any drop must be enumerated and justified.
- **Archive** only when the source declares itself retired, consolidated, or non-authoritative and a pre-move reference scan shows no unresolved live dependency. Archive is recoverable: move, do not delete.
- **Protected hold** when the title, headings, or known scope may enter a charter-forbidden domain. Athena does not break the tie by reading deeper.
- A rewrite may not invent operational detail. Unsupported fields remain explicitly unknown. Conflicts are carried and flagged for the owner rather than silently resolved.

## 4. Archive kill list for Max's signature

No archive move is authorized by this draft. Max's signature approves the proposed disposition, not an immediate delete.

| ID | Source | Proposed disposition | Evidence | Execution prerequisite |
|---|---|---|---|---|
| K1 | `dual-brand-vectoraiz-aim-channel.md` | Move to `archive/` | The document says AIM Channel is retired and that the runbook is historical only. | Preserve any still-current vectorAIz material in the Phase 2 product chunk; reference scan clean; catalog/router regenerate clean. |
| K2 | `session-lifecycle.md` | Move to `archive/` | It is a 12-line redirect stub that says the content was consolidated into `mcp-gateway.md`. | A stable redirect/tombstone must exist before the root stub moves; reference scan clean. |
| K3 | `runbooks/boot-kernel-companion-crosswalk.md` | Move to `archive/` | It declares itself evidence-only and not a catalog authority; its recorded CORE source is v9.11 while the current boot constitution is v9.13. | Confirm no current audit depends on the exact file path; preserve provenance in archive; reference scan clean. |

Signature decision:

- [ ] APPROVE K1-K3 as a recoverable archive list, subject to each prerequisite.
- [ ] REVISE — Max names the row and required disposition.

## 5. Merge-source retirement list for Max's signature

These sources are not archived now. They become retirement candidates only after their content is contained in the named destination and independently checked.

| ID | Source | Surviving authority | Reason |
|---|---|---|---|
| M1 | `codex-mp.md` | `runbooks/agent-dispatch.md` | Both govern the primary builder and dispatch path; two authorities invite drift. |
| M2 | `council-session-gate-and-fold-ops.md` | `runbooks/council-gate-process.md` and `runbooks/gate-procedure.md` | It is a short legacy operations fragment overlapping the indexed Council gate authorities. Any gateway-only material routes to the gateway owner, not into Council docs. |
| M3 | `session-open-protocol.md` | New `runbooks/session-operations.md` | Planned session-operations consolidation; current source is a protocol fragment rather than A-through-K authority. |
| M4 | `session-close-protocol.md` | New `runbooks/session-operations.md` | Same lifecycle authority as M3; historical blocks remain explicitly historical. |
| M5 | `work-checkout.md` | `runbooks/peer-instance-discipline.md`, with landed-proof material in `runbooks/branch-landed-verification.md` | Ownership and checkout discipline belongs with peer coordination; landed verification already has its own indexed authority. |
| M6 | `vulcan-configuration.md` | `runbooks/peer-instance-discipline.md` plus the boot companion set | The source is instance-specific and predates the registered third instance; durable rules must be instance-neutral. |

Signature decision:

- [ ] APPROVE M1-M6 as post-containment retirement candidates.
- [ ] REVISE — Max names the row and required destination.

## 6. Frozen Phase 2 manifests

A manifest is frozen by exact path. A file can move between chunks only through a written amendment to this spec. Protected-hold files are not silently added to any Athena chunk.

### Chunk A — session and peer operations (6 files)

| Source | Phase 2 action | Destination |
|---|---|---|
| `session-open-protocol.md` | Merge | New `runbooks/session-operations.md` |
| `session-close-protocol.md` | Merge | New `runbooks/session-operations.md` |
| `session-registry-recovery.md` | Rewrite | `runbooks/session-registry-recovery.md` |
| `peer-instance-discipline.md` | Rewrite and absorb M5/M6 | `runbooks/peer-instance-discipline.md` |
| `work-checkout.md` | Merge | M5 destinations |
| `vulcan-configuration.md` | Merge | M6 destinations |

Exit: non-blank-line containment for all merge sources; conflicts enumerated; all surviving authorities pass strict lint; no source retirement until Max's signature and reference checks are both present.

### Chunk B — governance, build, and operator discipline (10 files)

| Source | Phase 2 action | Destination |
|---|---|---|
| `bq-124-retro-verification.md` | Rewrite | `runbooks/bq-124-retro-verification.md` |
| `build-queue-lifecycle.md` | Rewrite | `runbooks/build-queue-lifecycle.md` |
| `codex-mp.md` | Merge | `runbooks/agent-dispatch.md` |
| `constitution-amendment.md` | Rewrite | `runbooks/constitution-amendment.md` |
| `council-session-gate-and-fold-ops.md` | Merge | M2 destinations |
| `dev-tickets.md` | Rewrite | `runbooks/dev-tickets.md` |
| `max-reporting.md` | Rewrite | `runbooks/max-reporting.md` |
| `rtk-token-optimization.md` | Rewrite | `runbooks/rtk-token-optimization.md` |
| `runbook-first-gates.md` | Rewrite | `runbooks/runbook-first-gates.md` |
| `ticket-probe-autoclose.md` | Rewrite | `runbooks/ticket-probe-autoclose.md` |

Exit: truth-preservation review; exact source-to-destination trace matrices; strict lint green; generated catalog surfaces current. Any constitutional conflict is flagged, never resolved by Athena.

### Chunk C — product release, test, and public-copy operations (5 files)

| Source | Phase 2 action | Destination |
|---|---|---|
| `aim-data-release-process.md` | Rewrite | `runbooks/aim-data-release-process.md` |
| `aim-node-release-process.md` | Rewrite | `runbooks/aim-node-release-process.md` |
| `alphafold-publish-scale-up.md` | Rewrite | `runbooks/alphafold-publish-scale-up.md` |
| `docker-testing.md` | Rewrite | `runbooks/docker-testing.md` |
| `website-copy-standard.md` | Rewrite | `runbooks/website-copy-standard.md` |

Exit: documentation claims checked against read-only Git ground truth or marked unverified; strict lint green; catalog surfaces current. If a source opens into customer data, production data, auth, payments, or security during Phase 2, Athena stops that file and transfers it to the protected hold.

### Archive-only manifest (3 files)

`dual-brand-vectoraiz-aim-channel.md`, `session-lifecycle.md`, and `runbooks/boot-kernel-companion-crosswalk.md` are governed only by K1-K3. They are not Phase 2 rewrite work unless Max revises the kill list.

## 7. Protected-domain owner-triage hold (57 files)

Athena records paths only so the 81-file accounting is complete. She makes no rewrite, merge, archive, priority, or truth claim about these documents. Mars or Vulcan must classify them under the applicable protected-domain review rules.

- `account-capability-onboarding.md`
- `account-teardown.md`
- `acl-sole-writer-enforcement.md`
- `activation-verification.md`
- `ai-market-backend.md`
- `ai-market-frontend.md`
- `aim-data-seller-publish-journey.md`
- `aim-data.md`
- `aim-node.md`
- `aimarket-mcp-server.md`
- `allai-agents.md`
- `allai-escalation-safety-spine.md`
- `auth-signup-flow.md`
- `aws-s3.md`
- `aws.md`
- `backup-and-recovery.md`
- `browser-session-auth.md`
- `celery-infrastructure-deployment.md`
- `cloudflare-and-dns.md`
- `cloudflare-worker.md`
- `connectivity.md`
- `crm-architecture.md`
- `crm-pipeline.md`
- `crm-target-state.md`
- `data-requests.md`
- `dataset-card-publishing.md`
- `disaster-recovery.md`
- `e2e-browser-runner.md`
- `email-drafting.md`
- `gateway-transport.md`
- `gateway_v2_rollback.md`
- `gateway_v2_rollout.md`
- `gcp-auth.md`
- `gmail-drop-pipeline.md`
- `infisical-secrets.md`
- `local-secops.md`
- `marketing-tab.md`
- `mcp-gateway.md`
- `meet-records-pipeline.md`
- `morning-briefing.md`
- `operator-telegram-notifications.md`
- `ops-ai-market.md`
- `publish-paths.md`
- `qdrant-sync-outbox.md`
- `qdrant.md`
- `queue-overlay-archival-cutover.md`
- `reconciliation-github-webhook.md`
- `schema-migration.md`
- `schema-rationalization.md`
- `seo-infrastructure.md`
- `seo-seller-validation.md`
- `support-ticket-system.md`
- `sysadmin.md`
- `titan-1.md`
- `trust-channel.md`
- `two-factor-auth.md`
- `vz-release-process.md`

This hold is a scope control, not a judgement that every line in every file is protected. The whole file is held because Athena is not authorized to decide the boundary by reading further.

## 8. Validation and execution controls

Before this triage can drive moves or promotion:

1. Recompute the 98/17/81 inventory at the branch base and fail if any path differs.
2. Max signs K1-K3 and M1-M6, or amends them explicitly.
3. A non-author reviews each promotion chunk before merge.
4. Every merge uses machine-verified non-blank-line containment; permitted drops are enumerated.
5. Every archive move is preceded by a full-repository reference scan and produces no unresolved active reference.
6. Generated `CATALOG.json`, `TOPIC-ROUTER.md`, and README surfaces are changed only through existing tooling, never by hand.
7. No file in section 7 enters an Athena chunk without explicit scope transfer from Max.

## 9. What this round does not claim

- It does not claim the 57 held files are safe to archive, merge, or rewrite.
- It does not claim the organization plan is on main; it is not at the verified base SHA.
- It does not move, rewrite, archive, or promote a runbook.
- It does not change code, tooling, CI, the resolver, the boot pin, or protected-domain documentation.
- It does not close the s1229 programme. It creates the signed decision surface needed before Phase 2 can safely start.
