# AWS Account — ai.market

> Parent runbook for ai.market's AWS account. Per-service detail lives in sub-runbooks: **[aws-s3.md](./aws-s3.md)**.

## §A. Header
- **system_name:** AWS Account — ai.market (`948749907373`)
- **purpose_sentence:** Operate ai.market's AWS account safely — the identity/credential model, access tiers and guardrails, billing controls, and per-service sub-runbooks — so a human or a stateless agent can take a correct, reversible first action.
- **owner_agent:** Vulcan-Primary
- **escalation_contact:** Max (account root owner)
- **lifecycle_ref:** §J (authoritative)
- **authoritative_scope:** Source of truth for *how ai.market operates AWS account 948749907373*: IAM identities used by agents/services, credential-delivery path (Infisical / Titan `~/.aws`), the access-tier + guardrail model, and billing/cost controls. NOT the source of truth for the AIM Data product's S3-connector code (backend repo) or for S3 bucket specifics (see sub-runbook `aws-s3.md`).
- **linter_version:** see §K.0 (lint not yet run)

## §B. Capability Matrix
| Feature/Capability | Status | Backing Code | Test Coverage | Last Verified |
|---|---|---|---|---|
| Scoped S3 service identity `svc-titan-vulcan` | SHIPPED | IAM policy `arn:aws:iam::948749907373:policy/aimarket-s3-svc`; Titan `~/.aws` profile `aimarket` | Manual: `sts get-caller-identity` + S3 round-trip (S720) | 2026-05-28 |
| S3 bucket/object ops on `aimarket-*` | SHIPPED | `aimarket-s3-svc`; AWS CLI `~/Library/Python/3.13/bin/aws` on Titan-1 | put/get/list/delete round-trip (S720) | 2026-05-28 |
| Broad operational access (PowerUser-class) for agent | SHIPPED | AWS-managed `PowerUserAccess` + customer `aimarket-guardrail-deny`, attached to `svc-titan-vulcan` | Verified S720: broad allow works; Org/CloudTrail/IAM denies refused | 2026-05-28 |
| Connector assume-role (`role_arn` + `external_id`) | SHIPPED (staging/dogfood) | IAM role `aimarket-connector-aimdata-staging`; trust principal `ai-market-backend-sts` + ExternalId; read-only on `aimarket-aimdata-staging` | trust policy verified S740; assume+list green S722 | 2026-05-31 |
| Billing budget + cost alarm | SHIPPED | AWS Budgets `aimarket-monthly-guardrail` ($50/mo; alerts 50/80/100% to max@ai.market) | created S720 | 2026-05-28 |
| Backend STS identity `ai-market-backend-sts` | SHIPPED (identity); creds NOT yet wired to any deployed service | IAM user (backend-owned). Creds in Infisical `ai-market-backend`/prod: `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` / `AWS_REGION` / `AI_MARKET_AWS_ACCOUNT_ID`. Runtime delivery: Railway env (see §E-07) | Titan profile `aimarket` resolves identity, verified S740 | 2026-05-31 |

## §C. Architecture & Interactions
| Component | Component Entry Point | State Stores | Integrates With | Notes |
|---|---|---|---|---|
| Agent identity | IAM user `svc-titan-vulcan` | IAM (users/policies); Titan `~/.aws/credentials` profile `aimarket` | Titan-1 shell (`~/Library/Python/3.13/bin/aws`) | Long-lived access key, scoped by `aimarket-s3-svc`. Vulcan acts through it via the Koskadeux shell. |
| Credential delivery | `aws configure --profile aimarket` / Infisical | Titan `~/.aws`; Infisical (secrets.ai.market) | Titan-1 | Keys NEVER transit chat. Infisical is the canonical vault for service secrets. |
| Object storage | S3 buckets `aimarket-*` | S3 (eu-north-1) | AIM Data node; backups → sub-runbook `aws-s3.md` | Per-purpose buckets; naming convention in §H.1. |
| Product S3 connector | backend `app/models/s3_connection.py` (`S3Connection`) | DB tables `s3_connection`, `s3_scan_job`, `s3_object_metadata` | Assumes an IAM role (`role_arn`+`external_id`): seller-side in prod, ai.market-side for the staging/dogfood node | Non-custodial: in production a seller's AWS creds never leave their node. |
| Billing / cost | AWS Budgets + Cost Explorer | AWS billing | Telegram/email alerts (PLANNED) | Guardrail against runaway spend. |

## §D. Agent Capability Map  *(the access model for delegated AWS work)*
| Agent | Operation | Skill/Tool | Auth Scope | Coverage Status |
|---|---|---|---|---|
| Vulcan | S3 bucket+object ops on `aimarket-*` | AWS CLI (Titan, profile `aimarket`) | `aimarket-s3-svc`: S3 on `aimarket-*` + `CreateBucket`/`ListAllMyBuckets` + `sts:GetCallerIdentity` | COMPLETE |
| Vulcan | Broad AWS operational actions ("just do it") | AWS CLI | AWS-managed **PowerUserAccess** + customer **aimarket-guardrail-deny** (denies Organizations/account/billing-write, IAM identity+key creation & AttachUserPolicy, CloudTrail StopLogging/DeleteTrail, KMS DisableKey/ScheduleKeyDeletion, Config/GuardDuty disable) | COMPLETE — verified S720 |
| Vulcan | Create the connector assume-role | AWS CLI | scoped `iam:CreateRole`+`PutRolePolicy` on `aimarket-connector-*` only | GAP — closes via console walk-through OR a narrow IAM add-on policy |
| Vulcan | Destructive / IAM / billing / out-of-footprint | — | CONFIRM-FIRST (operating agreement, §H.1) | N/A — never auto; always surfaced to Max |

**Operating agreement (the human guardrail behind "just do it").** With `aimarket-ops` attached, Vulcan auto-executes reversible, low-cost operational actions (create/configure/read S3, budgets, tagging, lifecycle rules, read-only across services). Vulcan CONFIRMS WITH MAX FIRST before: deleting buckets/objects holding data; terminating or deleting any resource holding state; any action with material recurring cost; anything touching IAM identities/policies or security/logging config (CloudTrail, KMS); or any action outside the ai.market footprint. Mirrors the §3 ASK-Max discipline in the session contract.

**Verification (S720).** Broad allow confirmed (`ec2:DescribeRegions`, `s3 ls`). Deny-guardrail confirmed refusing `organizations:*`, `cloudtrail:StopLogging`, `iam:AttachUserPolicy`. The KMS deny is present (same policy statement as the confirmed CloudTrail deny) but is not positively testable with a nonexistent key — KMS returns `NotFoundException` for absent keys regardless of allow/deny. No customer-managed KMS keys are in use (S3 uses SSE-S3), so current exposure is nil; re-verify against a real key if/when CMKs are introduced.

## §E. Operate — Serving Customers
**E-01 — Verify which AWS identity the agent is acting as.**
- trigger: before any AWS action, or on AccessDenied
- pre_conditions: `titan_aws_profile_configured`
- tool_or_endpoint: `aws sts get-caller-identity --profile aimarket`
- argument_sourcing: profile literal `aimarket`
- idempotency: IDEMPOTENT
- expected_success: JSON with `Account=948749907373`, `Arn=.../user/svc-titan-vulcan`
- expected_failures: `InvalidClientTokenId` (key bad/rotated) → §F-03
- next_step_success: proceed with intended action
- next_step_failure: §G-03 (rotate/reconfigure key)

**E-02 — Create a new project bucket.** (full procedure in `aws-s3.md` §E-01)
- trigger: new node/backup storage need
- pre_conditions: name follows §H.1 convention; region chosen = where consuming node runs
- tool_or_endpoint: `aws s3api create-bucket --bucket aimarket-<purpose>-<env> --region <r> --create-bucket-configuration LocationConstraint=<r>`
- argument_sourcing: name from §H.1; region from §H.1 rule
- idempotency: IDEMPOTENT_WITH_KEY (idempotency_key = bucket name; re-create on owned bucket → `BucketAlreadyOwnedByYou`)
- expected_success: bucket ARN returned; then lock down per `aws-s3.md` §E-01
- expected_failures: `IllegalLocationConstraint` (missing/!match LocationConstraint) → §F-02; `BucketAlreadyExists` (global name taken) → §F-05
- next_step_success: apply BPA + ownership + tags (aws-s3.md §E-01)
- next_step_failure: §G-02

**E-03 — Rotate the agent access key.**
- trigger: scheduled (≤90d) or suspected exposure
- pre_conditions: console or `iam:CreateAccessKey` access (Max action by default — IAM-write is confirm-first)
- tool_or_endpoint: console IAM → user → create new key; `aws configure --profile aimarket` on Titan; then deactivate+delete old key
- argument_sourcing: new key from console
- idempotency: NOT_IDEMPOTENT
- expected_success: `sts get-caller-identity` returns same user with new key; old key deleted
- expected_failures: lockout if old key deleted before new verified → keep both active until verified
- next_step_success: record rotation date in §J
- next_step_failure: re-add prior key from .csv

**E-05 — Expand agent access to operational tier (`aimarket-ops`).** *(implements §D row 2; requires Max approval)*
- trigger: Max approves broader delegated AWS work
- pre_conditions: `max_approved`; guardrail (§H.1 confirm-first) acknowledged
- tool_or_endpoint: console IAM → create policy `aimarket-ops` (PowerUserAccess + deny-guardrail JSON, see §G-05) → attach to `svc-titan-vulcan`; create a Budget alarm (E-06)
- argument_sourcing: policy JSON from §G-05
- idempotency: IDEMPOTENT
- expected_success: `svc-titan-vulcan` can act broadly except IAM/Org/account/billing-write; deny-guardrail blocks dangerous actions
- expected_failures: privilege-escalation attempts denied (by design)
- next_step_success: record in §B/§D, set budget alarm
- next_step_failure: detach policy; revert to `aimarket-s3-svc` only

**E-06 — Set a billing budget + alarm.**
- trigger: before broad access is granted
- tool_or_endpoint: `aws budgets create-budget` (monthly cost budget + SNS/email at 50/80/100%)
- idempotency: IDEMPOTENT_WITH_KEY (budget name)
- expected_success: budget visible; alert on threshold
- next_step_failure: §F-01 (AccessDenied — budgets require billing perms; Max action)

**E-07 — Use / wire the backend STS broker (`ai-market-backend-sts`).** *(the identity the backend assumes seller/connector roles AS, at fulfillment time)*
- what_it_is: `app/services/sts_assumer.py:assume_seller_role()` calls `boto3.client("sts").assume_role(...)` using the **default credential chain** (no keys passed in code) — so the running process MUST have `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` / `AWS_REGION` in its environment. `order_service.py` is the caller (buyer-delivery path).
- credentials (source of truth): Infisical project `ai-market-backend` (`bd272d48-c5a1-4b52-9d24-12066ae4403c`), env `prod`: `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_REGION` (`eu-north-1`), `AI_MARKET_AWS_ACCOUNT_ID` (`948749907373`). Read via the SysAdmin machine-identity token at Titan `/Users/max/.config/infisical/sysadmin-token` (see `infisical-secrets.md` → "Accessing Secrets"; the CLI must be pointed at `--domain=https://secrets.ai.market` or it silently tries Infisical Cloud and fails).
- runtime_injection: per `infisical-secrets.md`, **Railway env vars are the deploy-time injection source.** A secret in Infisical is NOT live in a service until it is ALSO set in that service's Railway variables.
- **CURRENT GAP (S740):** these AWS vars exist in Infisical prod but are **NOT set on any Railway service** (`ai-market-backend` and `ai-market-celery-worker` both lack them). Until synced onto the service that runs fulfillment, production (non-Titan) S3 delivery fails at `assume_role` with `NoCredentialsError`. Titan-local dogfooding works only because the workstation `~/.aws` profile `aimarket` supplies creds; the deployed service has none.
- seller_principal: the ARN a seller (or our dogfood connector role) grants `sts:AssumeRole` to is `arn:aws:iam::948749907373:user/ai-market-backend-sts`. In AIM Data connected-mode config this is pinned via `AI_MARKET_ASSUME_ROLE_PRINCIPAL_ARN`; unset → safe default of account-root + ExternalId.
- to_wire: read the three values from Infisical prod (token above), then `railway variables --service <svc> --set AWS_ACCESS_KEY_ID=… --set AWS_SECRET_ACCESS_KEY=… --set AWS_REGION=eu-north-1`. CONFIRM-FIRST (production credential change, §H.1 #5).
- idempotency: IDEMPOTENT_WITH_KEY (var name)
- expected_success: from the service, identity resolves to `…/user/ai-market-backend-sts`; `assume_seller_role` returns short-lived creds instead of `NoCredentialsError`.
- next_step_failure: §F-03 (InvalidClientTokenId → key bad/rotated)

## §F. Isolate — Diagnosing Deviations
| ID | Symptom | Probable Causes | Verification Procedure | Repair Ref | Confidence |
|---|---|---|---|---|---|
| F-01 | `AccessDenied` on an action | policy too narrow for the action/resource | re-run with `--debug`; check action vs `aimarket-s3-svc`/`aimarket-ops` | §G-01 | CONFIRMED |
| F-02 | `IllegalLocationConstraint` on create-bucket | `--create-bucket-configuration LocationConstraint` missing or != `--region` (only us-east-1 omits it) | inspect create command | §G-02 | CONFIRMED |
| F-03 | `InvalidClientTokenId` / `SignatureDoesNotMatch` | access key rotated, deleted, or mis-pasted | `sts get-caller-identity` fails | §G-03 | CONFIRMED |
| F-04 | `NoSuchBucket` | wrong name or wrong region/account | `aws s3 ls --profile aimarket` | §G-04 | CONFIRMED |
| F-05 | `BucketAlreadyExists` | bucket name taken globally by another account | name not in own `s3 ls` | aws-s3.md §G | CONFIRMED |
| F-06 | High transfer cost / latency | bucket region != consuming node region (cross-region egress) | compare bucket `get-bucket-location` vs node region | §G-02 (recreate in-region) | HYPOTHESIZED |

## §G. Repair — Fixing Problems
**G-01** symptom_ref F-01 · component_ref Agent identity · root_cause: scoped policy lacks the action/resource · repair_entry_point: console IAM policy `aimarket-s3-svc`/`aimarket-ops` · change_pattern: add the specific action on the specific `aimarket-*` resource (least-privilege) OR escalate to §E-05 if broad need; IAM-write is confirm-first · rollback: remove added statement · integrity_check: re-run the failed action.
**G-02** symptom_ref F-02/F-06 · component_ref Object storage · root_cause: region/LocationConstraint · repair_entry_point: `aws s3api create-bucket` · change_pattern: include `--create-bucket-configuration LocationConstraint=<region>` matching `--region`; for F-06 recreate bucket in the node's region and migrate objects · rollback: delete the mis-region bucket if empty · integrity_check: `get-bucket-location` == node region.
**G-03** symptom_ref F-03 · component_ref Credential delivery · root_cause: stale/bad key · repair_entry_point: `aws configure --profile aimarket` · change_pattern: reconfigure with a valid key (rotate per E-03; keep old active until new verified) · rollback: restore prior key from .csv · integrity_check: `sts get-caller-identity` returns `svc-titan-vulcan`.
**G-04** symptom_ref F-04 · component_ref Object storage · root_cause: wrong name/region/account · repair_entry_point: `aws s3 ls` · change_pattern: correct the bucket name or target region/profile · rollback: n/a · integrity_check: target op succeeds.
**G-05** symptom_ref F-01 (broad) · component_ref Agent identity · root_cause: agent needs operational breadth · repair_entry_point: console IAM `aimarket-ops` · change_pattern: attach AWS-managed `PowerUserAccess` PLUS an explicit deny statement: `Deny` on `organizations:*`, `account:*`, `iam:CreateUser/CreateAccessKey/DeleteUser/*LoginProfile`, `aws-portal:*Modify*`, `cloudtrail:StopLogging/DeleteTrail`, `kms:DisableKey/ScheduleKeyDeletion` · rollback: detach `aimarket-ops`, leave `aimarket-s3-svc` · integrity_check: a broad op (e.g. EC2 describe) succeeds while a denied op (e.g. `iam create-user`) fails.

## §H. Evolve — Extending the System
### §H.1 Invariants
1. **Non-custodial.** ai.market never holds a seller's AWS credentials; in production the seller's keys never leave their node. The connector uses short-lived STS role assumption only.
2. **Least privilege for agent identities.** No `AdministratorAccess` on any agent identity. Breadth via `PowerUserAccess` + explicit deny-guardrail (§G-05), never wildcards on IAM/Org/billing.
3. **Long-lived keys are managed.** Any long-lived access key is stored only in Infisical or Titan `~/.aws` (never in chat/repos), and rotated ≤ 90 days (§E-03).
4. **All service secrets via Infisical.**
5. **Confirm-first class.** Destructive (delete data/resources), IAM/policy changes, billing-write, security/logging changes, and any out-of-footprint action are confirmed with Max before execution.
6. **Bucket naming.** `aimarket-<purpose>-<env>`, lowercase/hyphens only, globally unique. Sub-divide with key prefixes, not extra buckets.
7. **Separation.** Node-served data and backups live in separate buckets (different lifecycle/retention/blast radius).
8. **Region = consuming node.** A bucket's region matches where the node that reads it runs (avoid cross-region egress/latency).

**Change-class tree.** BREAKING if: changes an invariant in §H.1; grants an agent identity IAM/Org/billing-write; removes the deny-guardrail; makes the connector custodial. REVIEW if: adds a new service to the agent's scope; creates a new long-lived identity; changes a budget threshold; adds a new bucket class. SAFE if: create/configure a bucket within convention; tagging; lifecycle rules; read-only exploration; rotating a key. Restrictive classification wins on dispute; unresolved → Max ruling appended here.

## §I. Acceptance Criteria
**§I scenario set (12, equal-weight 1/12 ≈ 0.0833; sum 1.0).**
1. (E) "Before acting, confirm who you are on AWS." → `sts get-caller-identity --profile aimarket`. 
2. (E) "Create a bucket for the prod backups in Stockholm." → `s3api create-bucket --bucket aimarket-backups-prod --region eu-north-1 --create-bucket-configuration LocationConstraint=eu-north-1` then lock down.
3. (E) "Rotate the agent's AWS key." → create new key (console/IAM, confirm-first), `aws configure --profile aimarket`, verify, delete old.
4. (E) "Give Vulcan broad AWS access to act directly." → §E-05: create+attach `aimarket-ops` (PowerUser + deny-guardrail), set budget — Max-approval gate.
5. (F) "Every S3 call returns AccessDenied." → F-01: compare action vs scoped policy; verify with `sts get-caller-identity`.
6. (F) "create-bucket fails with IllegalLocationConstraint." → F-02: missing/!match LocationConstraint.
7. (F) "AWS calls fail with InvalidClientTokenId." → F-03: key rotated/bad; reconfigure profile.
8. (G) "Fix: agent needs to read EC2 but policy is S3-only." → G-05 path (escalate to `aimarket-ops`, confirm-first) — NOT widen `aimarket-s3-svc` with EC2.
9. (G) "Fix the IllegalLocationConstraint." → G-02: add `--create-bucket-configuration LocationConstraint=<region>`.
10. (H) Classify: "Attach AdministratorAccess to svc-titan-vulcan." → BREAKING (violates §H.1 #2).
11. (H) Classify: "Add a lifecycle rule moving old objects to Glacier." → SAFE.
12. (ambiguous) "S3 writes started failing today." → acceptable first actions: `sts get-caller-identity` (F-03) OR check the specific AccessDenied action vs policy (F-01) OR `get-bucket-location`/`s3 ls` (F-04). Expected-answer key lists all three.

*(Equal weight. Harness + MP/AG answer-key sign-off pending — see §K.)*

## §J. Lifecycle
- **last_refresh_session:** S740
- **last_refresh_commit:** S740 broker-credential location + connector-role-shipped accuracy pass
- **last_refresh_date:** 2026-05-31
- **owner_agent:** Vulcan-Primary
- **refresh_triggers:** new IAM identity/policy change; new bucket class; access-tier change; incident; scheduled cadence
- **scheduled_cadence:** 90 days
- **last_harness_pass_rate:** not yet run
- **last_harness_date:** null
- **first_staleness_detected_at:** null

## §K. Conformance
- **§K.0 linter_version:** unverified — `runbook-lint` not yet run against this file
- **last_lint_run:** not yet run
- **last_lint_result:** NOT_RUN — authored to the §A–§K standard in S720; structural lint, harness, and MP/AG answer-key sign-off (§I) are pending as a follow-up Gate pass
- **trace_matrix_path:** n/a (greenfield, not a retrofit)
- **word_count_delta:** n/a (greenfield)
