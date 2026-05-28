# AWS S3 — ai.market  *(sub-runbook of [aws.md](./aws.md))*

> Parent: **[aws.md](./aws.md)** (account-wide identity, access tiers, guardrails, billing). This sub-runbook is the source of truth for S3 buckets, their lockdown settings, lifecycle/cost, and the S3-connector assume-role.

## §A. Header
- **system_name:** AWS S3 — ai.market (`948749907373`)
- **purpose_sentence:** Create, secure, and operate ai.market's S3 buckets (node-served data + backups) and the connector assume-role, so a human or agent can provision storage that is private, encrypted, correctly-regioned, and cost-aware.
- **owner_agent:** Vulcan-Primary
- **escalation_contact:** Max → parent runbook `aws.md`
- **lifecycle_ref:** §J
- **authoritative_scope:** Source of truth for S3 bucket naming/settings, lockdown baseline, lifecycle/cost policy, and the S3 STS connector role. Inherits account identity + guardrails from `aws.md` (§H.1 there is authoritative for non-custodial / least-privilege / confirm-first).
- **linter_version:** see §K.0 (lint not yet run)

## §B. Capability Matrix
| Feature/Capability | Status | Backing Code | Test Coverage | Last Verified |
|---|---|---|---|---|
| `aimarket-aimdata-staging` (node staging bucket, eu-north-1) | SHIPPED | created S720 via `s3api create-bucket`; lockdown commands §E-01 | put/get/list/delete round-trip (S720) | 2026-05-28 |
| Bucket lockdown baseline (BPA + BucketOwnerEnforced + SSE-S3) | SHIPPED | §E-01 command sequence; `aimarket-s3-svc` policy | verified on staging bucket (S720) | 2026-05-28 |
| `aimarket-backups-prod` (versioned + Object Lock COMPLIANCE/35d) | SHIPPED | created S723 (§E-05); see §E-06 backup-writer | first ai.market PG dump uploaded + size-matched; write/delete probe (S723) | 2026-05-28 |
| `aimarket-backup-writer` IAM identity (write-only backups) | SHIPPED | inline policy `backup-write-only` = `s3:PutObject`+`s3:ListBucket` only | PutObject OK / DeleteObject AccessDenied verified (S723) | 2026-05-28 |
| S3 connector assume-role (`role_arn` + `external_id`) | PLANNED | backend `app/models/s3_connection.py:S3Connection`; trust+permission policy §E-04 | — | — |
| Object lifecycle → Glacier Deep Archive (backups) | PLANNED | §E-03 | — | — |

## §C. Architecture & Interactions
| Component | Component Entry Point | State Stores | Integrates With | Notes |
|---|---|---|---|---|
| Bucket | `s3api create-bucket` (CLI, profile `aimarket`) | S3 (eu-north-1) | AIM Data node / backups / connector | Name per `aws.md` §H.1; one purpose per bucket. |
| Lockdown baseline | `put-public-access-block` + `put-bucket-ownership-controls` + (default SSE-S3) | S3 bucket config | — | Applied immediately after create. New buckets get BPA + SSE-S3 by AWS default; this makes it explicit + disables ACLs. |
| Lifecycle policy | `put-bucket-lifecycle-configuration` | S3 bucket config | Glacier Deep Archive | Backups age cold copies to Glacier (~$0.00099/GB vs $0.023). |
| Connector assume-role | IAM role `aimarket-connector-*` (trust + permission policy) | IAM | backend `S3Connection` (`role_arn`+`external_id`) | Node assumes role via STS w/ `ExternalId` condition; grants read-only on the one bucket. |
| Versioning + Object Lock | `put-bucket-versioning` + Object Lock at create | S3 bucket config | backups only | Protects backups from delete/overwrite/ransomware. |

## §D. Agent Capability Map
| Agent | Operation | Skill/Tool | Auth Scope | Coverage Status |
|---|---|---|---|---|
| Vulcan | Create/configure/tag `aimarket-*` buckets; put/get/list/delete objects | AWS CLI (profile `aimarket`) | `aimarket-s3-svc` (S3 on `aimarket-*`) | COMPLETE |
| Vulcan | Set lifecycle / versioning / encryption config | AWS CLI | `aimarket-s3-svc` (s3 perms-mgmt on `aimarket-*`) | COMPLETE |
| Vulcan | Create the connector assume-role | AWS CLI | needs `iam:CreateRole`+`PutRolePolicy` (NOT in `aimarket-s3-svc`) | GAP — closes via console walk-through OR narrow IAM add-on (parent §D) |
| Vulcan | Delete a bucket/objects holding data | — | CONFIRM-FIRST (parent §H.1 #5) | N/A — never auto |

## §E. Operate — Serving Customers
**E-01 — Create + lock down a bucket.** *(the canonical procedure; staging bucket created this way S720)*
- trigger: new storage need (node or backup)
- pre_conditions: name per `aws.md` §H.1; region = consuming node's region; identity verified (`aws.md` §E-01)
- tool_or_endpoint / argument_sourcing (region literal, e.g. `eu-north-1`; bucket from §H.1):
```
P="--profile aimarket"; R=eu-north-1; B=aimarket-<purpose>-<env>
aws s3api create-bucket --bucket $B --region $R --create-bucket-configuration LocationConstraint=$R $P
aws s3api put-public-access-block --bucket $B --public-access-block-configuration BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true $P
aws s3api put-bucket-ownership-controls --bucket $B --ownership-controls 'Rules=[{ObjectOwnership=BucketOwnerEnforced}]' $P
aws s3api put-bucket-tagging --bucket $B --tagging 'TagSet=[{Key=project,Value=ai.market},{Key=purpose,Value=<purpose>},{Key=env,Value=<env>},{Key=managed-by,Value=svc-titan-vulcan}]' $P
```
- idempotency: IDEMPOTENT_WITH_KEY (key = bucket name)
- expected_success: bucket ARN; BPA all-true; `BucketOwnerEnforced`; SSE-S3 (AES256) on by default; tags present. Verify: `get-bucket-location`, `get-public-access-block`, `get-bucket-encryption`.
- expected_failures: `IllegalLocationConstraint` → §F-01; `BucketAlreadyExists` → §F-02; `AccessDenied` → parent §F-01
- next_step_success: for backups, continue E-05 (versioning+lock) + E-03 (lifecycle)
- next_step_failure: §G-01

**E-02 — Put / get / list / delete objects.**
- tool_or_endpoint: `aws s3 cp <local> s3://$B/<key> $P` / `aws s3 cp s3://$B/<key> <local> $P` / `aws s3 ls s3://$B/<prefix>/ $P` / `aws s3 rm s3://$B/<key> $P`
- idempotency: cp IDEMPOTENT_WITH_KEY (object key); rm IDEMPOTENT
- expected_success: object round-trips; list shows key
- expected_failures: `AccessDenied` (parent §F-01); `NoSuchBucket` (parent §F-04)

**E-03 — Add a lifecycle rule (backups → Glacier Deep Archive).**
- tool_or_endpoint: `aws s3api put-bucket-lifecycle-configuration --bucket $B --lifecycle-configuration file://lifecycle.json $P` where rule transitions objects under `backups/` to `DEEP_ARCHIVE` after N days, expires noncurrent versions after M days
- idempotency: IDEMPOTENT (replaces config)
- expected_success: `get-bucket-lifecycle-configuration` returns the rule
- expected_failures: malformed JSON → validation error

**E-04 — Create the S3-connector assume-role.** *(GAP — needs IAM-write; confirm-first / console)*
- trigger: wiring the AIM Data node's S3 connector to a bucket
- pre_conditions: bucket exists; `external_id` chosen (random, per connection); IAM-write available (Max/console — parent §D)
- procedure: create role `aimarket-connector-<bucket>` with
  - **trust policy:** principal = the node's identity (for the dogfood node, `arn:aws:iam::948749907373:user/ai-market-backend-sts`); action `sts:AssumeRole`; `Condition.StringEquals."sts:ExternalId" = <external_id>`
  - **permission policy:** `s3:ListBucket` on `arn:aws:s3:::$B` + `s3:GetObject` on `arn:aws:s3:::$B/*` (read-only; add `PutObject` only if the node writes)
- argument_sourcing: `role_arn` → into backend `S3Connection.role_arn`; `external_id` → `S3Connection.external_id`
- idempotency: IDEMPOTENT_WITH_KEY (role name)
- expected_success: node assumes role via STS; connector lists/reads the bucket
- expected_failures: `AccessDenied` on AssumeRole (trust principal or ExternalId mismatch) → §F-03
- next_step_success: configure the connection in the AIM Data app with `role_arn` + `external_id`

**E-05 — Enable versioning + Object Lock (backups bucket).** *(DONE for `aimarket-backups-prod` S723)*
- note: Object Lock must be enabled at create-time (`--object-lock-enabled-for-bucket`); versioning is auto-on with it. **Mode is permanent at creation** — cannot be changed/added later.
- tool_or_endpoint: `aws s3api create-bucket ... --object-lock-enabled-for-bucket $P`; then `put-object-lock-configuration`
- **DECIDED (S723, Max):** `aimarket-backups-prod` = **COMPLIANCE / 35-day** default retention. Compliance (not Governance) so backups survive a compromised credential — no principal incl. root can delete/shorten a locked object within 35 days. SSE-S3 AES256 + bucket key; BPA all-true. acct 948749907373, eu-north-1.
- idempotency: config IDEMPOTENT
- expected_success: versioning Enabled; object-lock = COMPLIANCE/35

**E-06 — Write a backup object (write-only identity).** *(the path the nightly job uses)*
- identity: IAM user `aimarket-backup-writer`, inline policy `backup-write-only` (`s3:PutObject` on `aimarket-backups-prod/*` + `s3:ListBucket`). **No** Delete / PutObjectRetention / BypassGovernanceRetention — a stolen writer key cannot destroy or alter existing backups.
- creds: Infisical project `ai-market-backend` (bd272d48-...), env prod: `AWS_BACKUP_WRITER_ACCESS_KEY_ID` / `AWS_BACKUP_WRITER_SECRET`.
- layout: `s3://aimarket-backups-prod/postgres/ai-market/<date>/` and `/postgres/infisical/<date>/`.
- verified S723: PutObject OK, ListBucket OK, DeleteObject → AccessDenied (least-privilege holds). First ai.market PG dump (~987MB, custom format) uploaded + S3 size matched byte-for-byte; restore-readiness confirmed via `pg_restore --list` (2,100 TOC entries), no restore against any live DB.

## §F. Isolate — Diagnosing Deviations
| ID | Symptom | Probable Causes | Verification Procedure | Repair Ref | Confidence |
|---|---|---|---|---|---|
| F-01 | `IllegalLocationConstraint` on create | missing/`!=`region `--create-bucket-configuration LocationConstraint` (only us-east-1 omits it) | inspect command | §G-01 | CONFIRMED |
| F-02 | `BucketAlreadyExists` | global name taken by another account | name not in `s3 ls --profile aimarket` | §G-02 | CONFIRMED |
| F-03 | Connector `AccessDenied` on AssumeRole | trust-policy principal or `sts:ExternalId` mismatch | check role trust policy vs node identity + `external_id` | §G-03 | CONFIRMED |
| F-04 | `AccessDenied` on object op despite role | permission policy lacks the action or bucket ARN | inspect role permission policy | §G-03 | CONFIRMED |
| F-05 | Bucket policy `put` blocked | `RestrictPublicBuckets`/`BlockPublicPolicy` rejects a public statement | review BPA vs intended policy | §G-04 | HYPOTHESIZED |
| F-06 | High egress/latency reading bucket | bucket region != node region | `get-bucket-location` vs node region | §G-05 | HYPOTHESIZED |

## §G. Repair — Fixing Problems
**G-01** symptom_ref F-01 · component_ref Bucket · root_cause: region/LocationConstraint · repair_entry_point: `s3api create-bucket` · change_pattern: add `--create-bucket-configuration LocationConstraint=<region>` matching `--region` · rollback: delete empty mis-region bucket · integrity_check: `get-bucket-location` == intended region.
**G-02** symptom_ref F-02 · component_ref Bucket · root_cause: global name collision · repair_entry_point: bucket name · change_pattern: append a short distinguishing suffix within §H.1 convention (e.g. `-eun1`) · rollback: n/a · integrity_check: create succeeds.
**G-03** symptom_ref F-03/F-04 · component_ref Connector assume-role · root_cause: trust/permission mismatch · repair_entry_point: IAM role `aimarket-connector-*` (confirm-first) · change_pattern: align trust principal + `ExternalId` with the node; ensure permission policy lists `s3:ListBucket` on bucket ARN and `s3:GetObject` on `/*` · rollback: restore prior policy version · integrity_check: node assumes role + lists bucket.
**G-04** symptom_ref F-05 · component_ref Lockdown baseline · root_cause: BPA blocks a public statement · change_pattern: do NOT relax BPA — connector access is via STS role, never public; if a genuinely public object is needed, that is a §H/parent change-class REVIEW, confirm-first · integrity_check: required access works via role, BPA stays all-true.
**G-05** symptom_ref F-06 · component_ref Bucket · root_cause: cross-region · change_pattern: create a new bucket in the node's region (E-01) and migrate objects (`aws s3 sync`); retire the old · rollback: keep old until sync verified · integrity_check: `get-bucket-location` == node region.

## §H. Evolve — Extending the System
### §H.1 Invariants  *(inherits parent aws.md §H.1; S3-specific additions)*
1. Every bucket: **Block Public Access all-true**, **ACLs disabled (BucketOwnerEnforced)**, **SSE-S3 (AES256) at rest**.
2. Bucket access is via **STS role assumption only** — never public, never long-lived keys handed to the node.
3. **Naming** `aimarket-<purpose>-<env>`; **node-data and backups in separate buckets**; **region = consuming node**.
4. **Backups** buckets: versioning ON + Object Lock + Glacier lifecycle (node-served buckets: versioning optional/off).
**Change-class tree.** BREAKING: relaxing BPA to allow public access; making the connector custodial; removing encryption. REVIEW: new bucket class; changing the connector role's permission scope; a cross-account trust principal. SAFE: create a bucket per convention; tagging; a lifecycle rule; a versioning toggle on a backups bucket. Restrictive wins; unresolved → Max (append here).

## §I. Acceptance Criteria
**§I scenario set (10, equal-weight 0.1; sum 1.0).**
1. (E) "Create a private, encrypted node bucket in Stockholm." → E-01 full sequence (create w/ LocationConstraint + BPA + ownership + tags).
2. (E) "Upload a test file then remove it." → E-02 `s3 cp` then `s3 rm`.
3. (E) "Wire the connector to read the staging bucket." → E-04: create assume-role (trust w/ ExternalId + read-only permission policy), put role_arn/external_id into S3Connection — confirm-first (IAM-write).
4. (F) "create-bucket fails IllegalLocationConstraint." → F-01.
5. (F) "Connector can't assume the role (AccessDenied)." → F-03: trust principal / ExternalId mismatch.
6. (F) "Reads from the bucket are slow and pricey." → F-06: region != node region.
7. (G) "Fix the LocationConstraint error." → G-01 add `--create-bucket-configuration`.
8. (G) "Connector AccessDenied even after assuming role." → G-03 permission policy missing `s3:GetObject` on `/*`.
9. (H) Classify: "Make one object publicly downloadable by URL." → BREAKING/REVIEW (violates §H.1 #1-2; confirm-first) — NOT a casual BPA relax.
10. (ambiguous) "The connector stopped reading the bucket." → acceptable first actions: check role trust/ExternalId (F-03) OR check permission policy actions (F-04) OR `get-bucket-location` vs node region (F-06). Key lists all three.

*(Equal weight. Harness + MP/AG answer-key sign-off pending — see §K.)*

## §J. Lifecycle
- **last_refresh_session:** S723 (backups-prod went live; was S720 authoring)
- **last_refresh_commit:** S723 backup-bucket-live update
- **last_refresh_date:** 2026-05-28
- **owner_agent:** Vulcan-Primary
- **refresh_triggers:** new bucket; connector-role change; lockdown-baseline change; incident; scheduled cadence
- **scheduled_cadence:** 90 days
- **last_harness_pass_rate:** not yet run
- **last_harness_date:** null
- **first_staleness_detected_at:** null

## §K. Conformance
- **§K.0 linter_version:** unverified — `runbook-lint` not yet run against this file
- **last_lint_run:** not yet run
- **last_lint_result:** NOT_RUN — authored to the §A–§K standard in S720; lint + harness + MP/AG answer-key sign-off (§I) pending as a follow-up Gate pass
- **trace_matrix_path:** n/a (greenfield)
- **word_count_delta:** n/a (greenfield)
