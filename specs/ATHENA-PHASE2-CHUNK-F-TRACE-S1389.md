# ATHENA-PHASE2-CHUNK-F-TRACE-S1389

Status: DRAFT ARCHIVE AND RETIREMENT EXECUTION  
Owner: Athena  
Session: S1389  
Branch: `docs/athena-phase2-chunk-f-s1389`  
Exact base ref: local `main`  
Exact base SHA: `5f968f167661dcac669dd42910037e05a50221ed`  
Phase 1 triage source: `0945124c5abc4fd20173b89135c32fc94460ae34:specs/ATHENA-PHASE1-TRIAGE-S1389.md`  
Max decision event: `17df8171` on `build:bq-runbook-catalog-validator-s1229`, 2026-07-29

## 1. Scope and authority

Max signed archive rows K1-K3 and retirement rows M1-M6 verbatim. The Event
Ledger API exposed to Athena can append events but cannot query an event by ID,
so this branch records the signed event exactly as supplied in the round
directive; it does not fabricate an independent read-back.

This chunk executes only those nine rows. It does not rewrite the three
protected-domain candidates, modify a catalog surface, promote any runbook,
perform a build, push, merge, or close the session.

## 2. House procedure used

The repository organization plan requires recoverable `archive/` moves,
exclusion of retired documents from active resolution, an inbound-reference
scan before removal, and rollback by restoring from the prior commit. It also
forbids treating tombstones as a second authority.

The exact local-main base still has live references to several old paths and
does not contain every signed destination. Catalog regeneration and alias
changes are explicitly reserved for the operator lane. Therefore this chunk
uses a transition-safe two-part action for every row:

1. preserve the complete historical source under `archive/`, preceded only by
   a two-line archival provenance header; and
2. replace the former path with a short `status: RETIRED` tombstone naming the
   signed destination or retirement rationale.

The tombstones contain no operational procedure and create no competing
authority. They exist only so current references resolve until the operator
lane lands the destination/catalog transition and proves that the old paths can
disappear.

## 3. Exact-base exceptions

Two signed sources are absent from local `main` but present on the named
`origin/main` ref:

| Row | Source | Exact imported blob |
|---|---|---|
| K3 | `runbooks/boot-kernel-companion-crosswalk.md` | `77033124c3c460e18fea07732f8fa543a68b8506` |
| M5 | `work-checkout.md` | `2bcc46c387efe76a9e99d895247b3d0eb6e0923a` |

Those exact blobs were preserved directly in `archive/`; they were not
rewritten or represented as exact-base files.

## 4. Signed row execution ledger

| Row | Document | Action taken | Evidence action matches signed row |
|---|---|---|---|
| K1 | `dual-brand-vectoraiz-aim-channel.md` | Historical source moved to `archive/dual-brand-vectoraiz-aim-channel.md`; RETIRED tombstone left at the old path | Signed K1 says recoverably archive the document because AIM Channel is retired while current product authority survives elsewhere; tombstone repeats only that rationale |
| K2 | `session-lifecycle.md` | Redirect stub moved to `archive/session-lifecycle.md`; stable RETIRED redirect left at the old path | Signed K2 requires a stable redirect before the root stub moves and names `mcp-gateway.md`; tombstone points only to `mcp-gateway.md` |
| K3 | `runbooks/boot-kernel-companion-crosswalk.md` | Exact origin blob preserved at `archive/boot-kernel-companion-crosswalk.md`; RETIRED evidence tombstone created at the historical path | Signed K3 classifies it as evidence-only, not catalog authority; tombstone states exactly that and points to current companions/generated catalog |
| M1 | `codex-mp.md` | Full source moved to `archive/codex-mp.md`; RETIRED tombstone left | Signed M1 names `runbooks/agent-dispatch.md` as survivor; tombstone points only there |
| M2 | `council-session-gate-and-fold-ops.md` | Full source moved to `archive/council-session-gate-and-fold-ops.md`; RETIRED tombstone left | Signed M2 names `runbooks/council-gate-process.md` and `runbooks/gate-procedure.md`; tombstone names both without resolving their content |
| M3 | `session-open-protocol.md` | Full source moved to `archive/session-open-protocol.md`; RETIRED tombstone left | Signed M3 names new `runbooks/session-operations.md`; tombstone points only there |
| M4 | `session-close-protocol.md` | Full source moved to `archive/session-close-protocol.md`; RETIRED tombstone left | Signed M4 names the same session authority; tombstone points only there |
| M5 | `work-checkout.md` | Exact origin blob preserved at `archive/work-checkout.md`; RETIRED tombstone created at the historical path | Signed M5 routes ownership discipline to `runbooks/peer-instance-discipline.md` and landed proof to `runbooks/branch-landed-verification.md`; tombstone names both |
| M6 | `vulcan-configuration.md` | Full source moved to `archive/vulcan-configuration.md`; RETIRED tombstone left | Signed M6 routes durable peer rules to `runbooks/peer-instance-discipline.md` and boot material to the companion set; tombstone repeats only those destinations |

## 5. Byte-preservation evidence

For every archived file, removing the two-line archival provenance prefix
reconstructs the exact source blob:

| Row | Source blob | Reconstructed archive blob | Result |
|---|---|---|---|
| K1 | `8b52dfaa81193e7589b8bfa134e600240d8f9794` | `8b52dfaa81193e7589b8bfa134e600240d8f9794` | Exact |
| K2 | `caf85609471f9489b7beff3db39d2cd0bfaafc1e` | `caf85609471f9489b7beff3db39d2cd0bfaafc1e` | Exact |
| K3 | `77033124c3c460e18fea07732f8fa543a68b8506` | `77033124c3c460e18fea07732f8fa543a68b8506` | Exact |
| M1 | `92dd323600e17c2903cb4ae4bb8774705d44fd67` | `92dd323600e17c2903cb4ae4bb8774705d44fd67` | Exact |
| M2 | `fde219a230df9595c1ad1d77b2ac8b4f5213bb82` | `fde219a230df9595c1ad1d77b2ac8b4f5213bb82` | Exact |
| M3 | `ddd1b42644505f84f5a29515bcd9f25bc16eeb66` | `ddd1b42644505f84f5a29515bcd9f25bc16eeb66` | Exact |
| M4 | `8bbddc2faeed1b95dda1e71a903432615e851f2f` | `8bbddc2faeed1b95dda1e71a903432615e851f2f` | Exact |
| M5 | `2bcc46c387efe76a9e99d895247b3d0eb6e0923a` | `2bcc46c387efe76a9e99d895247b3d0eb6e0923a` | Exact |
| M6 | `f948463ef1c9a4094db121c82947b6922361dfaa` | `f948463ef1c9a4094db121c82947b6922361dfaa` | Exact |

This is the truth-preservation guarantee: no source line is discarded, and
the only added archive text is the signed row/date/event provenance.

## 6. Reference-scan result

The pre-move scan found active old-path references in generated
`TOPIC-ROUTER.md`, current runbooks, historical audits, and specs. Because this
chunk is forbidden to modify generated catalog surfaces or unrelated documents,
the old paths remain resolvable through tombstones.

Operator-lane completion must:

1. land or confirm every named destination;
2. regenerate catalog/router/README surfaces through tooling;
3. migrate or classify non-generated inbound references;
4. verify aliases and destinations at the final SHA; and
5. remove transition tombstones only when zero live old-path consumer remains.

Until then this branch is a recoverable retirement transition, not authority
promotion and not permission to merge without the operator follow-up.

## 7. Strict-check applicability

The nine archived files are deliberately excluded from active catalog and
resolver selection. The nine tombstones are short retirement redirects, not
A-through-K runbooks. Running the 21 runbook-conformance checks on either class
would be category error.

- Modified files to which A-through-K strict checks apply: 0.
- Direct strict-check invocations: 0.
- Result: `NOT_APPLICABLE`, never reported as a vacuous pass.
- `git diff --check`: required clean.

## 8. File manifest

Created archive records:

- `archive/dual-brand-vectoraiz-aim-channel.md`
- `archive/session-lifecycle.md`
- `archive/boot-kernel-companion-crosswalk.md`
- `archive/codex-mp.md`
- `archive/council-session-gate-and-fold-ops.md`
- `archive/session-open-protocol.md`
- `archive/session-close-protocol.md`
- `archive/work-checkout.md`
- `archive/vulcan-configuration.md`

Transition tombstones remain at the nine signed historical paths. This trace is
the nineteenth changed document.

## 9. Constraints observed

- Docs only, runbooks repository only.
- Exactly K1-K3 and M1-M6; no protected rewrite.
- No catalog, topic-router, or README inventory write.
- No ACTIVE promotion.
- No push, merge, build, or `kd_session_close`.
- Author and committer: `athena <athena@ai.market>`.
