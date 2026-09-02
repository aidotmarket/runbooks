# BQ-SELLER-WORKSPACE-W3-PROFILING-S1650 Gate 2 implementation specification

**Status:** Gate 2 candidate for independent review. **Implementation dispatch is forbidden until independent CC, GLM, and DeepSeek reviews all approve this exact file digest.** No earlier Gate 1 vote, earlier digest, reviewer substitute, wrapper status, or partial panel transfers to this candidate.

**Build Queue entity:** `build:bq-seller-workspace-w3-profiling-s1650`

**Expected branch:** `spec/bq-seller-workspace-w3-profiling-s1650`

**Revision:** round-4 consistency correction.

**Exact approved Gate 1 base:** commit `d65c11cbf1bccb8f5a98cb07b0f69983bdfe7b4b`, file `specs/BQ-SELLER-WORKSPACE-W3-PROFILING-S1650-GATE1.md`, SHA-256 `4ff20a4fd80038d572d22db599e3ca7aa9e8fed745bd5ef3efe793ec18d0aa9b`.

**Scope:** implementation instructions only. This document authorizes no code dispatch, merge, deployment, AWS/provider mutation, customer credential/data access, feature enablement, public capability claim, W4, W5, R2, AIM Data runtime import, publication, delivery, or `legacy_serial` change. All fixtures, identities, buckets, objects, VPCs, accounts, and browser journeys used by later proof are synthetic and explicitly authorized for that proof.

## 1. Read-only baseline and binding conflict rule

This Gate 2 candidate was written from the approved Gate 1 base above and read-only inspection of canonical ai-market backend `origin/main` at `31efd4c607ace06319bbbbc697834584952f7ed9`. If implementation begins later, the builder must rebase these named integration points onto then-current `origin/main` without changing the Gate 1 contract. Any architectural conflict returns to Gate 2 review; it is not resolved in code.

Round-2 review of candidate commit `062cc66e54d989ae7d205901e3b6a6020cccd747`, file SHA-256 `ffd048afc4a9c520a069811012bab61002544a6bf9f89dbc5e118fedfb0fd82d`, returned CC and GLM `APPROVE_WITH_NITS` and DeepSeek `REQUEST_CHANGES`, recorded in Panel Event Ledger event `db7bf298-5441-412d-bc76-1c4980cfd80e`. Round 3 removed the unapproved verifier calls and folded the nonblocking buildability nits. An implementation attempt against round-3 commit `397dd312b11ddb5d6063743048ba014c23fe880a`, file SHA-256 `761c5ba0fc84ec682fd5919c055916b28f7737a2e39c5e2c22c005a241d512da`, and backend base `229689c821022b2fe8f8901f7ca32eca6f685fcf` exposed the W2-test and pre-W3-schema consistency blockers recorded in implementation blocker Event `997aa75b-210a-4390-ba9a-451433cc575e`; its preserved builder report is `/Users/max/koskadeux-state/ts-sockets/jobs/b864637c65dc.report.json`. This round-4 correction changes only those consistency requirements and folds the prior clarity nits. No earlier-round verdict transfers to this digest.

The canonical W2 integration points are exact:

- `app/api/v1/router.py` already includes `app.api.v1.endpoints.seller_workspace.router`; do not add a second router or prefix.
- `app/api/v1/endpoints/seller_workspace.py` owns `/api/v1/seller-workspace`, `SellerWorkspaceNoStoreRoute`, `require_active_seller`, `require_idempotency_key`, `_seller_context`, `_raise_safe_http`, and dependency construction.
- `app/core/seller_workspace_config.py` owns the nine default-off Seller Workspace flags and `capability_payload`. Its `AWS_CONNECT_IMPLEMENTED=True` is W2-only; profile is currently hard-coded `implemented=False`.
- `app/models/seller_workspace.py` owns `CloudConnection`, encrypted `CloudConnectionCredential`, append-only `SellerWorkspaceAuditEvent`, and the unchanged `DeliveryAuthority`/`legacy_serial_id` contract.
- `app/schemas/seller_workspace.py` owns strict `extra="forbid"` HTTP schemas.
- `app/services/seller_workspace_connection.py` owns owner-scoped repositories, idempotency, ExternalId custody, and `BotoAWSConnectionVerifier._verify_sync`. That verifier currently grants `s3:GetObject` and calls `head_object`; W3 readiness must replace only that proof with bounded list-only proof.
- `app/services/seller_workspace_audit.py` owns the closed audit allowlists and canonical scope hashes.
- `app/services/seller_workspace_encryption.py` is the existing versioned application envelope boundary and must also encrypt source-key ARNs, selector object identities, runtime references, and task ARNs with record-specific AAD.
- `alembic/versions/20260831_001_s1647_seller_workspace_w2.py` is the W2 parent schema; canonical Alembic currently has the single head `s1648_issue_channel_repair`.
- `tests/test_s1647_seller_workspace_b1.py`, `tests/test_s1647_seller_workspace_b2a.py`, `tests/test_s1647_seller_workspace_b2b.py`, and `tests/test_s1647_seller_workspace_postgres.py` are the W2 safety suite and all four must pass. The B1, B2A, and PostgreSQL files remain byte-for-byte unchanged. In B2B, only `test_workspace_verifier_uses_exact_prefix_policy_and_900_second_session` changes as specified in Section 2; every other B2B test remains byte-for-byte unchanged.
- `app/core/celery_app.py` already uses JSON-only Celery, late acknowledgement, worker-lost rejection, prefetch 1, and explicit Kombu queues. `railway.worker.json` is the shared worker and must not receive W3 tasks.

There is no Seller Workspace CloudFormation, ECS, Lambda, ECR-runtime, profile queue, or W3 worker artifact on this canonical backend main. W2 returns a trust-policy document from `SellerWorkspaceConnectionService._build_authorization`; it does not deploy seller infrastructure. The new IaC below is therefore a concrete new artifact, not a claimed existing abstraction.

## 2. Exact implementation file manifest

This section is the closed, exhaustive 55-path repository manifest for the later implementation. Every change path has exactly one table or bullet entry, every entry has a binding requirement, and no later section may imply another create, modify, rename, or delete path. Gate 3 must compare the exact 55-path changed set to this manifest and fail on any missing or extra path. Generated build evidence is explicitly separated below because it is not a repository path.

The later builder modifies exactly these existing backend and W2-test files:

| File | Required change |
| --- | --- |
| `app/core/seller_workspace_config.py` | Add `AWS_PROFILE_IMPLEMENTED=True` only after the manifest path-set check, contracts, migration, packaging, and focused tests all pass; add fail-closed profile dependency checks while preserving every environment default as false. |
| `app/models/seller_workspace.py` | Add the W3 enums and ORM models in section 4; map `SellerWorkspaceAuditEvent.profile_job_id` as deferred or with an equivalently safe opt-in projection so pre-W3 W2 repository queries do not eagerly select it; do not change `DeliveryAuthority`, `DeliveryAuthorityKind`, `legacy_serial_id`, or existing W2 constraints. |
| `app/schemas/seller_workspace.py` | Add the exact W3 request/response, broker/verifier, task-output, and closed evidence schemas in sections 5 and 8 with `extra="forbid"`; add no allAI/LLM input schema. |
| `app/services/seller_workspace_connection.py` | Change `BotoAWSConnectionVerifier._verify_sync` to list-only proof; add no profiling behavior to the W2 lifecycle service. |
| `app/services/seller_workspace_encryption.py` | Reuse the existing versioned envelope primitive and add record-specific AAD purposes for source-key ARNs, selector object identities, runtime references, and task ARNs; do not change existing W2 ciphertext/AAD semantics. |
| `app/services/seller_workspace_audit.py` | Extend only the exact append-only operation/purpose/snapshot allowlists in section 10 and reject every non-allowlisted field. |
| `app/api/v1/endpoints/seller_workspace.py` | Add the owner-scoped routes in section 5 using the existing dependencies, error mapper, idempotency key, and no-store route class. |
| `app/core/celery_app.py` | Include `app.tasks.seller_workspace_profile`, declare only `seller_workspace_profile_control`, and add the two bounded sweeps in section 9. |
| `tests/test_s1647_seller_workspace_b2b.py` | Change only `test_workspace_verifier_uses_exact_prefix_policy_and_900_second_session`: retain its 900-second duration and `workspace-verify` purpose assertions; assert the exact list-only session policy and `ListObjectsV2` call required below; assert that no `s3:GetObject` statement exists and no `head_object` call occurs; and preserve every unrelated test byte-for-byte. |

The later builder creates exactly these backend/control files:

- `alembic/versions/20260902_001_s1650_seller_workspace_w3.py`, revision `s1650_seller_workspace_w3`, down revision `s1648_issue_channel_repair`;
- `app/services/seller_workspace_profile.py` for repository transactions, receipts, authorization, state transitions, leases, quotas, and evidence commit;
- `app/services/seller_workspace_profile_aws.py` for list-only discovery, STS session-policy construction, canonical verifier/broker envelopes, alias invocation, and response validation;
- `app/tasks/seller_workspace_profile.py` for control-task claim/reconcile/cancel/expiry/cleanup only;
- `app/core/seller_workspace_profile_metrics.py` for low-cardinality allowlisted metrics only; and
- `railway.profile-worker.json` for the dedicated control worker.

The later builder creates exactly these seller-account IaC, packaging, and runtime files:

- `infra/seller_workspace_profile/template.yaml` for the exact Section 3 resources, roles, policies, parameters, immutable package/image identities, and prohibited-resource absence;
- `infra/seller_workspace_profile/package.py` for deterministic broker/verifier ZIP creation, normalized file order/timestamps/modes, dependency hash checking, and the package/schema manifest;
- `infra/seller_workspace_profile/common/__init__.py` as a side-effect-free package marker exposing no runtime behavior;
- `infra/seller_workspace_profile/common/contracts.py` for the exact closed verifier/broker/task-output/result schemas and canonical projections copied into each isolated package;
- `infra/seller_workspace_profile/broker/__init__.py` as a side-effect-free package marker;
- `infra/seller_workspace_profile/broker/handler.py` for closed broker-envelope validation, deterministic request/start/reconcile/poll/cancel, result validation, attestation, and cleanup;
- `infra/seller_workspace_profile/broker/requirements.lock` with exact hashes;
- `infra/seller_workspace_profile/verifier/__init__.py` as a side-effect-free package marker;
- `infra/seller_workspace_profile/verifier/handler.py` for closed verifier-envelope validation, exact stack-resource, VPC/DNS-attribute, identity, DNS Firewall, Resolver association/rule, outbound-endpoint, and Route 53 Profile inventories using only the Gate 1-authorized calls, plus the exact five-key resolver hash and hash-only receipt;
- `infra/seller_workspace_profile/verifier/requirements.lock` with exact hashes;
- `infra/seller_workspace_profile/requirements-cfn-lint.lock` for the isolated `cfn-lint==1.50.1` Gate 3 tool environment, with every direct and transitive distribution pinned and SHA-256-hashed and no backend/runtime import path;
- `seller_workspace_profile_runtime/Dockerfile` for the digest-pinned CPython image, hash-locked production dependencies, non-root/read-only execution, and fixed entrypoint;
- `seller_workspace_profile_runtime/.dockerignore` closing the image build context to the runtime package and explicitly copied contract artifact;
- `seller_workspace_profile_runtime/requirements.lock` with exact production hashes for the pinned boto3, botocore, Pydantic, and PyArrow surface only;
- `seller_workspace_profile_runtime/requirements-test.lock` with exact hashes for the dedicated parser test environment only;
- `seller_workspace_profile_runtime/profile_task/__init__.py` as a side-effect-free package marker;
- `seller_workspace_profile_runtime/profile_task/main.py` for exact bootstrap-key/checksum retrieval, request validation, bounded parse orchestration, result upload, and stable safe exits;
- `seller_workspace_profile_runtime/profile_task/contracts.py` for the task-local closed request/output/evidence schemas and schema-digest assertion;
- `seller_workspace_profile_runtime/profile_task/canonical.py` for RFC 8785 canonical bytes and all Gate 1 hash preimages;
- `seller_workspace_profile_runtime/profile_task/limits.py` for the unchanged Section 7 numeric ceilings and limit accounting;
- `seller_workspace_profile_runtime/profile_task/supervisor.py` for child-process isolation, resource limits, signal/cancel handling, and cleanup;
- `seller_workspace_profile_runtime/profile_task/parsers/__init__.py` for a closed CSV/TSV, JSON/JSONL, and Parquet parser registry with no dynamic import;
- `seller_workspace_profile_runtime/profile_task/parsers/csv_parser.py` for the deterministic bounded CSV/TSV behavior in Section 7;
- `seller_workspace_profile_runtime/profile_task/parsers/json_parser.py` for the deterministic bounded JSON/JSONL behavior in Section 7; and
- `seller_workspace_profile_runtime/profile_task/parsers/parquet_parser.py` for the deterministic bounded locked-PyArrow Parquet behavior in Section 7.

The later builder creates exactly this build workflow:

- `.github/workflows/seller-workspace-profile-runtime.yml` to verify both Lambda locks, bootstrap the dedicated hash-locked `cfn-lint==1.50.1` tool in a CI temporary directory and run it, create the two deterministic ZIP packages through the packaging script, compare backend/Lambda/task schema SHA-256 values, build the runtime from only the closed Docker context, and emit the evidence artifacts below without deploying or mutating anything.

The later builder creates exactly these tests and committed fixture definitions:

- `tests/test_s1650_profile_contracts.py` for strict HTTP, verifier/broker/task-output/evidence schemas, canonical hashes, size ceilings, default-off capability, and the absence of any W3 allAI/LLM schema or call path;
- `tests/test_s1650_profile_authorization.py` for two-seller ownership, foreign/absent equivalence, cursor/idempotency/cache/token isolation, record-specific encryption AAD, and list-only W2 correction;
- `tests/test_s1650_profile_lifecycle.py` for every state/lease/death/retry/cancel/timeout/reconciliation/cleanup path;
- `tests/test_s1650_profile_postgres.py` for real PostgreSQL migration, constraints, composite ownership, append-only audit, immutable safe-field retention, and empty/nonempty downgrade;
- `tests/test_s1650_profile_aws.py` for STS policies, closed envelopes, IAM fixtures, broker/verifier calls, and complete multi-CIDR autodefined inventory using only the approved Gate 1 verifier API set;
- `tests/test_s1650_profile_iac.py` for parsed exact resources, policies, routes, endpoints, DNS rules, roles, task settings, packaging inputs, and prohibited-resource absence;
- `tests/test_s1650_profile_observability.py` for metric cardinality, the exact audit allowlist, forbidden-field rejection, and canary absence across every W3 sink;
- `seller_workspace_profile_runtime/tests/test_csv.py` for every CSV/TSV format, boundary, hostile-input, and deterministic-output case;
- `seller_workspace_profile_runtime/tests/test_json.py` for every JSON/JSONL format, boundary, hostile-input, and deterministic-output case;
- `seller_workspace_profile_runtime/tests/test_parquet.py` for every locked codec, footer/row-group limit, hostile metadata, and deterministic-output case;
- `seller_workspace_profile_runtime/tests/test_supervisor.py` for every resource, timeout, cancellation, signal, process-group, temporary-byte, and cleanup boundary;
- `seller_workspace_profile_runtime/tests/test_golden_evidence.py` for canonical semantic bytes/hashes, field-token scope, size budgets, and volatile-attestation separation;
- `tests/fixtures/seller_workspace_profile/generate.py` for deterministic in-test creation of all synthetic benign, boundary, bomb, malformed, and hostile bytes; and
- `tests/fixtures/seller_workspace_profile/expected.json` for the closed fixture case list plus expected canonical JSON and hashes.

`requirements.txt`, `requirements-dev.txt`, the W2 B1, B2A, and PostgreSQL safety-test files, `railway.worker.json`, and every delivery/serial/`legacy_serial` file remain byte-for-byte unchanged and are not manifest change paths. The B2B file is a manifest path solely for the named test correction; every other B2B test remains byte-for-byte unchanged, and all four W2 safety files must pass. The dedicated `requirements-cfn-lint.lock` is tooling-only and is never installed into the backend/web/control or runtime environments. The backend/web/control environment must contain no PyArrow or parser-only dependency.

The workflow outputs, outside the repository diff, are exactly: broker ZIP, verifier ZIP, package/schema digest manifest, OCI image manifest with immutable `sha256:` digest, SPDX JSON SBOM, and vulnerability report. Gate 3 binds each artifact digest to the implementation commit. The template entry above accepts only the exact Lambda package hashes and image digest as parameters. The workflow must not deploy a stack, update an alias, change a flag, push a mutable execution tag, or publish a capability.

No frontend file is in W3. No AIM Data repository or package is changed or imported.

## 3. Seller-account execution identity and exact IaC

One seller-deployed stack is bound one-to-one to one verified `CloudConnection`. ai.market may render the acknowledged template and verify it, but may never call CloudFormation create/update/delete. The seller deploys it under the seller's own AWS identity.

`infra/seller_workspace_profile/template.yaml` contains these exact resources and no long-lived compute:

1. `AWS::EC2::VPC` with DNS support and hostnames enabled, IPv4 only, primary CIDR `10.203.0.0/24`.
2. `AWS::EC2::VPCCidrBlock` adding exactly `10.203.1.0/24`. No parameter may override either CIDR. This deliberate two-CIDR layout is the required live multi-CIDR proof surface.
3. Two private `/26` task subnets in distinct available AZs, one from each VPC CIDR, with isolated route tables. The template and stack-resource set contain and reference no default route, NAT gateway, internet gateway, egress-only gateway, VPN, Direct Connect, IPv6 association, VPC peering connection, Transit Gateway attachment, or Transit Gateway route. Parsed-template and exact stack-resource closure prove this prohibition; it does not authorize or require peering or Transit Gateway verifier APIs, which are outside the Gate 1 Section 6.3 call set.
4. One task security group with no ingress. Egress is TCP 443 only to the interface-endpoint security group and the regional S3 managed prefix list, plus UDP/TCP 53 only to the VPC resolver. The endpoint security group accepts TCP 443 only from the task group.
5. Interface endpoints with private DNS for `ecr.api`, `ecr.dkr`, `logs`, `secretsmanager`, and `kms`, in both task subnets; one S3 gateway endpoint on both route tables. No other endpoint is allowed.
6. One control bucket with block-public-access, TLS-only bucket policy, SSE-KMS, versioning/replication/Object Lock/inventory/access logging disabled, incomplete multipart abort after one day, and expiry after one day. Its only object shapes are `requests/<connection-id>/<job-id>/<attempt>/request.json` and `results/<connection-id>/<job-id>/<attempt>/evidence.json`.
7. One customer-managed symmetric regional KMS key for the control bucket and Fargate ephemeral storage, with the exact broker/task/S3/Fargate and verifier read-only statements approved in Gate 1.
8. One Secrets Manager secret containing the seller-owned field-token HMAC key; only the task role can retrieve its value.
9. One ECS cluster whose `Configuration.ManagedStorageConfiguration.FargateEphemeralStorageKmsKeyId` is the control-key ARN, and one Fargate task definition pinned by image digest, Linux platform `1.4.0`, `awsvpc`, `1024` CPU units, `4096` MiB memory, `20` GiB ephemeral storage, read-only root filesystem, non-root UID/GID `65532`, no privilege/capability/host namespace/device, and `StopTimeout=30`.
10. Separate connection-control, verifier, broker, task, and task-execution identities. The stack creates only the verifier, broker, task, and task-execution roles; the existing connection-control role ARN is a parameter and is not replaced. No role combines two identities.
11. One broker Lambda and one verifier Lambda, each with a published immutable version and alias. Aliases, package hashes, code-signing config, environment, runtime, architecture, timeout, memory, role, and resource policy are verifier-bound. Neither Lambda is VPC-attached.
12. One task log group and one ECS-event audit log group, both metadata-only with seven-day retention; one EventBridge ECS task-state rule targeting only the audit group.
13. One DNS Firewall allow domain list, one `*` block list, one rule group, allow priority `100`, block priority `200`, and one association at priority `101` with `MutationProtection=ENABLED`. The allow rule uses `ALLOW` and `INSPECT_REDIRECTION_DOMAIN`; the block rule uses `BLOCK`, `NODATA`, and no override domain. CloudFormation relies on AWS's default fail-closed behavior, and the verifier additionally requires live `FirewallFailOpen=DISABLED` before every launch.

The S3 gateway endpoint policy contains only the verified source bucket/prefix, the two exact control-object shapes, and `s3:GetObject` for `arn:${AWS::Partition}:s3:::prod-${AWS::Region}-starport-layer-bucket/*`. Interface endpoint policies name the exact roles and required read/write actions. No endpoint policy contains `Principal: "*"` without simultaneous exact role, action, and resource/condition restriction.

### 3.1 Complete AWS autodefined multi-CIDR VPC inventory

The verifier must not reject all Resolver rules blindly and must not bless a vague `SYSTEM` class. It builds and compares a complete inventory for the exact stack VPC.

It calls `DescribeVpcs(VpcIds=[exact])`, `DescribeVpcAttribute` for DNS support/hostnames, and fully paginated `ListResolverRuleAssociations(Filters=[VPCId=exact])`. Every returned association is rechecked for the exact VPC with `GetResolverRuleAssociation`, and its rule is resolved with `GetResolverRule`; both calls are authorized by Gate 1 Section 6.3. Pagination is capped at 20 pages and 1,000 total records. This is a deliberate W3 control-plane inventory guardrail, not an AWS service-limit claim: an inventory that exceeds either bound, or exposes a next token after either bound, fails closed. Both CIDR associations must be `associated`; any third CIDR, IPv6 CIDR, pending/disassociating/failed CIDR association, or DNS-attribute drift fails. A directly associated private hosted zone is not rejected merely because it exists; its Resolver effects are accepted only through the closed rule predicate below.

The verifier constructs a canonical, sorted seller-local inventory containing every returned association/rule and separately requires the following deterministic trailing-dot domains:

- `0.203.10.in-addr.arpa.` for `10.203.0.0/24`; and
- `1.203.10.in-addr.arpa.` for `10.203.1.0/24`.

For every inventory member, the verifier requires association and rule `Status=COMPLETE`, no `ResolverEndpointId`, `ShareStatus=NOT_SHARED`, `OwnerId="Route 53 Resolver"`, and ARN namespace `arn:${partition}:route53resolver:${region}::autodefined-rule/rslvr-autodefined-rr-<safe-suffix>`. It does not use `RuleType` as an ownership or safety predicate. A seller-created `SYSTEM`, `FORWARD`, `DELEGATE`, or `RECURSIVE` rule never qualifies; an additional rule qualifies only under the same closed AWS-owned autodefined identity. Both CIDR-specific reverse domains must be present somewhere in the authenticated complete inventory, proving both VPC CIDRs were inventoried.

The verifier separately requires zero outbound endpoints from fully paginated `ListResolverEndpoints(Direction=OUTBOUND, HostVPCId=exact)` and zero Route 53 Profile associations from fully paginated `ListProfileAssociations(ResourceId=exact VPC ID)`. Omitted permission for one of these approved Gate 1 calls, filter drift, truncation, an unexhausted token, or a returned record that cannot be revalidated fails closed.

A directly associated private hosted zone may contribute only associations/rules that independently pass the complete AWS-owned autodefined owner, ARN namespace, `COMPLETE` status, `NOT_SHARED`, and no-`ResolverEndpointId` inventory predicate above. Any non-autodefined, endpoint-bearing, shared, malformed, foreign-owner, or nonterminal association fails. An allowed private hosted zone can alter seller-local answers, but the approved zero-outbound-endpoint and zero-Profile-association checks plus the exact S3 endpoint policy, task egress, DNS Firewall fail-closed state, and TLS resource identity remain authoritative. Missing IAM permission for an approved Gate 1 inventory call, service omission, duplicate association/rule ID, missing required CIDR reverse domain, or incomplete inventory makes the runtime ineligible.

The complete variable inventory remains only in seller-account verifier memory and the separately authorized synthetic Gate 4 harness. It does not enter the stable receipt. The `resolver_control_hash` preimage and canonical semantics are byte-identical to the approved Gate 1 five-key projection: `{non_autodefined_rule_associations:0, endpoint_bearing_rule_associations:0, outbound_endpoints:0, profile_associations:0, pagination_complete:true}`. No sixth or seventh key is permitted. Presence of both required CIDR-specific reverse rules, complete AWS service-owned inventory, and all other approved eligibility predicates above are fail-closed acceptance preconditions only and do not enter `resolver_control_hash`. Allowed AWS autodefined rule enumeration, names, domains, VPC-CIDR-dependent reverse rules, raw rule IDs/types, endpoint IDs, Profile details, CIDRs, and any VPC-specific inventory hash do not cross to ai.market.

The task DNS allowlist is separate from this service inventory. It contains only exact source/control S3 names, regional ECR API/Docker/layer names, exact Logs/Secrets Manager/KMS endpoint names, VPC endpoint DNS names, and every approved CNAME/DNAME target. Wildcard allow entries and ai.market/allAI names are forbidden.

## 4. Persistent models and state machines

`app/models/seller_workspace.py` adds these exact model classes/tables:

| Model | Table | Required contents |
| --- | --- | --- |
| `ProfileSourceKMSKeySet` | `seller_workspace_profile_source_kms_key_sets` | owner/connection, immutable version, zero-to-eight envelope-encrypted canonical ARNs, set hash, account, region, current/superseded time |
| `ProfileRuntimeVerificationNonce` | `seller_workspace_profile_runtime_verification_nonces` | owner/connection/runtime, nonce hash only, status, issued/expiry/terminal time, receipt hash |
| `ProfileRuntimeCostEstimate` | `seller_workspace_profile_runtime_cost_estimates` | all standing units, model/table/currency versions, low/high amount, receipt hash, expiry, consumption |
| `ProfileRuntime` | `seller_workspace_profile_runtimes` | owner/connection, status/version, encrypted broker/verifier/stack refs, all immutable hashes, source-key version/hash, estimate acknowledgement, verified/disabled time |
| `CloudObjectSelector` | `cloud_object_selectors` | owner/connection/runtime, immutable ordered encrypted identities and version/ETag/size bindings, selector/input hashes |
| `ProfileCostEstimate` | `seller_workspace_profile_cost_estimates` | owner/runtime/selector, all marginal units, high/low amount, receipt hash, expiry, consumed job |
| `ProfileJob` | `seller_workspace_profile_jobs` | owner bindings, state/version, attempt, immutable input, parser/image/schema versions, phase/absolute deadlines, lease, counters, safe failure, evidence, idempotency |
| `ProfileAttempt` | `seller_workspace_profile_attempts` | owner/job, attempt, deterministic ECS token hash, encrypted task ARN/hash, provider state, usage, terminal/cleanup times |
| `SellerWorkspaceListingEvidence` | `seller_workspace_listing_evidence` | owner/job/attempt, canonical semantic/attestation JSON, three hashes, expiry/deletion time |

`SellerWorkspaceAuditEvent` gains nullable `profile_job_id` plus `(profile_job_id, seller_id) -> (ProfileJob.id, ProfileJob.seller_id)` and an index. The ORM mapping for `profile_job_id` must be deferred, or use an equivalently safe opt-in projection that guarantees legacy W2 repository queries against the pre-W3 `s1648_issue_channel_repair` test schema do not eagerly select the absent column. Every W3 repository/query that requires this field must explicitly load or project and use it. No W2 column is rewritten.

Runtime status is `draft -> authorized -> verified -> disabled`; only a new exact verification can move `authorized -> verified`, and drift/cancel/operator rollback only moves `verified -> disabled`. A disabled version never reactivates; a new immutable runtime version is required.

Job states are exactly:

`queued -> starting -> running -> validating_result -> succeeded`

with `queued -> cancelled`, any nonterminal state to `failed|expired`, and `starting|running|validating_result -> cancel_requested -> cancelled|failed|expired`. Only `succeeded|failed|cancelled|expired` are terminal. The database check constraint names the complete set. A compare-and-swap update always includes `(id, seller_id, version, state, current_attempt)`; zero rows means a stale no-op, never a forced transition.

Nonce states are `pending -> consumed|rejected|expired`. Standing and marginal receipts are immutable and single-use. A source-key submission identical to the current canonical set is a no-op; A-to-B-to-A creates three versions even when the first and third set hashes match.

All tables have same-seller composite foreign keys. Hash fields are lowercase 64-character hex; image digests are `sha256:` plus 64 lowercase hex. JSON columns have explicit canonical byte ceilings. Unique constraints cover owner/idempotency/operation, job/attempt, deterministic token hash, one evidence row per successful attempt, one job per consumed marginal receipt, one authorization per standing receipt, and the nonce tuple from Gate 1.

## 5. API, authorization, caching, and isolation contracts

All routes use the existing router and `require_active_seller`. Every mutation uses the existing `Idempotency-Key` dependency plus immutable request hash. Every lookup includes `seller_id`; foreign and absent IDs produce the same `404` body. Conflict is `409`, stale optimistic version is `409`, disabled/unready dependency is `503`, invalid closed input is `422`, quota/spend rejection is `429`, and provider ambiguity is a redacted `503` safe code. Every response, including error paths, has `Cache-Control: no-store, private`, `Pragma: no-cache`, and no ETag. CDN/shared-cache middleware must not cache the prefix.

The exact new routes are those approved in Gate 1:

- `PUT /connections/{connection_id}/profile-runtime/source-kms-keys`;
- `POST /connections/{connection_id}/profile-runtime/estimates`;
- `POST /connections/{connection_id}/profile-runtime/authorize`;
- `POST /connections/{connection_id}/profile-runtime/verify`;
- `GET /connections/{connection_id}/objects`;
- `POST /cloud-object-selectors`;
- `POST /profile-jobs/estimates`;
- `POST /profile-jobs`;
- `GET /profile-jobs`;
- `GET /profile-jobs/{job_id}`;
- `POST /profile-jobs/{job_id}/cancel`; and
- `GET /profile-evidence/{evidence_id}`.

Request/response fields are the closed Gate 1 fields. All Pydantic models use `extra="forbid"`, bounded lists/strings/integers, strict UUIDs, strict RFC3339 UTC, and enums. Mutations also require `expected_version` where a mutable runtime/job exists. List cursors are opaque AEAD tokens bound to seller, connection, prefix, mode, page size, snapshot window, and expiry; maximum page sizes are 100 objects and 50 jobs.

The W2 correction in `BotoAWSConnectionVerifier._verify_sync` removes the entire `ReadExactVerificationPrefix` statement and `head_object`; neither may be restored. Its session policy permits only `s3:ListBucket` with `StringLike s3:prefix=[bounded_prefix, bounded_prefix + "*"]`; proof is a `ListObjectsV2(MaxKeys=1)` response with a returned key inside the normalized non-root prefix. In `tests/test_s1647_seller_workspace_b2b.py`, only `test_workspace_verifier_uses_exact_prefix_policy_and_900_second_session` changes: it asserts the exact single-statement fixture policy with `Sid=ListExactVerificationPrefix`, `Action=s3:ListBucket`, resource `arn:aws:s3:::seller-proof-bucket`, and `StringLike s3:prefix=["ai-market/proofs/", "ai-market/proofs/*"]`; asserts the exact call `{Bucket:"seller-proof-bucket", Prefix:"ai-market/proofs/", MaxKeys:1}`; and asserts no `s3:GetObject` statement and no `head_object` call. Version discovery separately requests only `s3:ListBucketVersions`. No source-verification permission or call may be broadened, and the W3 AWS adapter never owns an S3 object client method.

Two-seller isolation is mandatory at database, service, broker-envelope, encrypted-AAD, idempotency, cursor, Redis/Celery, and HTTP-cache layers. Seller A and Seller B may use identical connection/job/idempotency UUID text in hostile fixtures; seller B must see neither existence, state, evidence, cursor validity, receipt usability, field-token equality, task identity, nor cached response from seller A. Redis keys are HMAC-scoped with seller ID and purpose, never raw IDs; Celery messages contain only job ID, seller-ID hash, lease epoch, and operation. They contain no selector, ARN, receipt payload, evidence, or source detail.

## 6. Broker/task identity, permissions, and envelopes

The connection-control session can invoke only exact published broker/verifier aliases and list the exact source prefix. It has no source object action, ECS, IAM, KMS, Secrets Manager, Logs, or second-assume-role authority. Session duration remains 900 seconds.

The broker can create/read/delete only the exact request/result keys described in Gate 1, run/tag/describe/stop only the exact task definition and cluster, and pass only the exact task/task-execution roles. `RunTask` has no command, CPU, memory, role, network, image, storage, or arbitrary environment override. The only two overrides are broker-derived `W3_REQUEST_KEY` and `W3_REQUEST_SHA256`. Every `DescribeTasks` identity call includes `include=["TAGS"]`.

The task role alone can read selected source objects, its exact request, the HMAC secret, and write its exact result. It cannot list the source bucket, read another source binding, read any result, overwrite a request, call ECS, assume a role, or reach ai.market/allAI. The execution role can pull only the approved digest and write metadata-only logs. The verifier is read-only and cannot read any object or secret value, launch/stop/tag a task, pass a role, decrypt data, or mutate infrastructure. Its allow actions and implementation calls must be contained exactly within the approved Gate 1 Section 6.3 verifier set; no additional API action or permission may be added by Gate 3.

Verifier and broker use the exact closed Gate 1 envelopes `seller_workspace_profile_runtime_verify.v1` and `seller_workspace_profile_broker_request.v1`. `infra/seller_workspace_profile/common/contracts.py`, backend schemas, Lambda handlers, and task schemas share byte-for-byte golden JSON fixtures but no runtime Python import crosses the image/Lambda/backend boundary. Each package validates its own Pydantic/JSON Schema copy and the workflow compares schema SHA-256 values.

ECS `clientToken` is lowercase SHA-256 over canonical version, cluster-ARN hash, seller, connection, job, attempt, and input hash. Request keys are deterministic. `start` creates with `If-None-Match:*`; `reconcile_start` exact-key reads and validates an existing request. A changed byte, checksum, media type, KMS key, tag, selector, source-key set, runtime, attempt, or expiry fails terminally.

## 7. Deterministic formats and hard numeric ceilings

Only uncompressed CSV/TSV, uncompressed JSON/JSONL, and Parquet are accepted. ZIP, TAR, GZIP, 7z, RAR, XLS/XLSX, databases, images, documents, symlinks, sparse/container formats, URLs, external page/index references, and encrypted Parquet fail before parser work. Therefore archive-member ceiling is **0**, nested-archive ceiling is **0**, and external-reference ceiling is **0**.

The task base is CPython `3.11.11-slim-bookworm` pinned by OCI digest in the reviewed Dockerfile. The runtime production lock pins `boto3==1.42.91`, `botocore==1.42.91`, `pydantic==2.13.2`, and `pyarrow==23.0.1` with platform wheel hashes; CSV and JSON use only the Python standard library. No pandas, DuckDB, fsspec, URL filesystem, plugin, or parser extension is installed.

All ceilings are server, request, broker, and task enforced:

| Resource | Ceiling |
| --- | ---: |
| objects/job | 10 |
| declared size/object | 100 GiB |
| source bytes read | 64 MiB/object; 256 MiB/job |
| rows parsed | 100,000/object; 250,000/job |
| columns/leaves | 512/object |
| emitted field records | 256/job and 90,112 canonical bytes |
| non-field result | 32,768 canonical bytes |
| final result | 131,072 UTF-8 bytes |
| CSV/JSON scalar | 65,536 bytes |
| CSV row/JSON record | 1,048,576 bytes |
| JSON and structural nesting | 32 |
| Parquet footer | 16 MiB |
| Parquet row groups opened | 8/object |
| decompressed bytes | 128 MiB/object; 512 MiB/job |
| decompression ratio | 100:1 |
| parser children | 1; total processes 8 |
| open files | 64 |
| temporary bytes | 1 GiB |
| child address space | 3 GiB; task memory 4 GiB |
| CPU | 540 CPU seconds; task allocation 1 vCPU |
| task wall time | 600 seconds |
| infrastructure retries | 1; maximum attempts 2 |
| connection/seller/global running | 1 / 2 / 20 |
| queued jobs/seller | 4 |
| jobs/seller | 20/day; 100/rolling 30 days |

CSV parsing is streaming and byte-prefix bounded. Dialect detection uses only the first 64 KiB, a fixed candidate order `comma, tab, semicolon, pipe`, and deterministic tie-break. Encoding order is BOM, strict UTF-8, UTF-16LE, UTF-16BE, then Latin-1; no locale participates. Headers/values are discarded after local token/class/count updates. Formula prefixes are counted but never evaluated.

JSON rejects duplicate keys, NaN/Infinity, malformed UTF, overlong number/scalar/record, and depth over 32. JSONL processes records in byte order. Array/object traversal is insertion order from input bytes; emitted fields are sorted by structural position. Huge integers are classified without float conversion.

Parquet reads the bounded footer first, rejects external/encrypted metadata, opens at most eight row groups in index order, and accepts only codecs supported by the exact locked PyArrow build. It never emits statistics, key-value metadata, `created_by`, Arrow metadata, bloom bytes, page/index content, or field names. Codec output is charged to both decompressed-byte and 100:1 limits.

Canonicalization is RFC 8785 UTF-8. Object order is immutable selector order; field order is structural-position order; enum arrays are deduplicated and unsigned-UTF-8 sorted. Golden input produces identical `semantic_evidence` bytes and `semantic_hash` across job IDs, attempts, timestamps, region, CPU/memory observations, and wall duration.

The child process applies `RLIMIT_AS=3 GiB`, `RLIMIT_CPU=540`, `RLIMIT_FSIZE=1 GiB`, `RLIMIT_NOFILE=64`, and `RLIMIT_NPROC=8`; the supervisor uses a new process group, no shell, and kills the group on cancellation, SIGTERM, resource fault, or deadline. Temporary data is mode `0700` under one attempt directory on encrypted ephemeral storage and is removed before exit; task destruction is the crash boundary.

### 7.1 Provider-spend ceilings

All amounts are decimal USD in integer millionths; float money is forbidden. A stale or missing regional price table fails closed. The absolute ceilings below are conservative Gate 2 numeric guardrails implementing approved Gate 1 Decision D2=A. Gate 1 froze the bounded-range/cost-acknowledgement decision, not these dollar values; the values remain subject to the mandatory Gate 3 regional price-model recomputation below.

- standing estimate high: at most **USD 125.00 per runtime per 30 days**;
- marginal estimate high: at most **USD 2.00 per job including the one retry**;
- acknowledged marginal high sums: at most **USD 20.00 per seller/day**, **USD 100.00 per seller/rolling 30 days**, and **USD 400.00 globally/day**;
- allAI/model/provider spend in W3: **USD 0.00** because W3 makes no allAI/provider call;
- unacknowledged, expired, replayed, differently bound, or over-cap receipts cannot authorize a template or launch.

The standing receipt includes every endpoint AZ-hour/byte, key/secret month, verifier Lambda, KMS key/policy read, approved Resolver rule-association/rule and outbound-endpoint inventory read, Route 53 Profile-association inventory read, DNS Firewall configuration/rule/domain/association read, DNS Firewall custom-domain, EventBridge, S3 storage, and log-retention unit. It includes no unit for an API removed by this correction. The marginal receipt includes both attempts' maximum Fargate one-minute/per-second allocation, broker Lambda, S3/KMS/secret/EventBridge/DNS-query/log/endpoint/cross-AZ units. Provider invoice lag cannot be a hard stop, so admission reserves the full acknowledged high estimate transactionally before launch and releases unused modeled amount only after terminal attestation.

The absolute caps above remain binding maxima, but their enforcement is not accepted for launch at Gate 3 until the candidate pins the applicable regional price-table and estimate-model versions and independently recomputes the worst-case standing and two-attempt marginal envelopes for every supported region/AZ/endpoint placement. Gate 3 must prove each modeled envelope fits its cap, each unit is present exactly once, stale/missing prices fail closed, integer-millionth rounding is conservative, and seller/global rolling reservations enforce the stated windows transactionally. A failed recomputation returns to Gate 2; it must not be handled by omitting a cost unit, silently changing a cap, or enabling launch.

## 8. Exact value-free evidence boundary; allAI input deferred to W4

The only result allowed from seller AWS into ai.market is the Gate 1 `seller_workspace_profile_result.v1`, canonical JSON, maximum 131,072 bytes. The allowed top-level keys are exactly `schema_version`, `semantic_evidence`, `semantic_hash`, `runtime_attestation`, `attestation_hash`, and `result_integrity_hash`. The nested fields, enum values, limits, usage counters, and hash relationships are exactly section 9 of Gate 1; no implementation may add a convenience field.

Object records contain only opaque `oNNNN` ordinal, size, binding kind, format enum/closed format metadata, row count plus `exact|estimate|lower_bound`, positional field records, and warning codes. Field records contain only structural position, 64-hex HMAC field token plus key version, physical-type enum, nullable flag, non-null/null counts, distinct/length bands, PII enums/confidence bands, and quality enums.

Bucket, key, filename, extension, account, role, ARN, URL, timestamp, source checksum, header, JSON/Parquet name, value, value hash, sample, min/max, quantile, regex match, snippet, parser message/stderr, provider body, task ARN, credential, and field-token key are forbidden. Whole source objects, whole ranges, whole rows, and whole task output are never persisted in ai.market, Redis, Celery, logs, traces, audit, or evidence. Selector identities, source-key ARNs, runtime refs, and task ARN are separately envelope-encrypted; they are not evidence.

W3 retains only the value-free `seller_workspace_profile_result.v1` evidence contract above. `SellerWorkspaceProfileAllAIInputV1`, `seller_workspace_profile_allai_input.v1`, `build_allai_profile_input`, and any equivalent allAI/LLM adapter, schema, serializer, prompt, gateway, task, route, or agent integration are explicitly deferred to W4. They must not exist in the W3 implementation. W4 may define a consumer only under its own approved specification and may not infer authorization from W3 evidence availability.

W3 tests use AST/import/call-graph and dependency scans plus hostile-marker canaries to prove zero imports or calls from W3 routes, services, Celery tasks, Lambda handlers, runtime code, allAI services, LLM gateways, or agents. This absence check does not create a dormant allAI envelope or call path.

## 9. Lease, idempotency, cancellation, timeout, death, and cleanup

`ProfileJob` contains nullable `lease_owner`, `lease_epoch`, and `lease_expires_at`. Claim is one PostgreSQL transaction using database time and `SELECT ... FOR UPDATE SKIP LOCKED`; it sets a random 128-bit owner hash, increments epoch, and leases for 60 seconds. The worker renews every 20 seconds. Every provider action and state write includes the current epoch and requires at least 10 seconds remaining. An expired worker cannot renew or act; redelivery may claim only after expiry.

`app.tasks.seller_workspace_profile.run_job(job_id, seller_hash, lease_epoch)` is `acks_late=True`, `reject_on_worker_lost=True`, `ignore_result=True`, time limit 1,200 seconds, soft limit 1,170 seconds, queue `seller_workspace_profile_control`. It loads all sensitive state from PostgreSQL after claim. Celery arguments/results never contain raw state.

`railway.profile-worker.json` uses the canonical backend `Dockerfile` and exact command `celery -A app.core.celery_app worker --loglevel=info --concurrency=4 --prefetch-multiplier=1 -Q seller_workspace_profile_control`, one replica, restart on failure. The shared `railway.worker.json` remains unchanged.

The phase maxima are queue 5 minutes, start 3, run 10, validate/commit 2, with one absolute 20-minute deadline and 30-second physical stop grace inside it. Beat enqueues `seller_workspace-profile-reconcile` every 20 seconds and `seller_workspace-profile-expire-cleanup` every 60 seconds onto the dedicated queue. Sweep pages are 100 rows and stop after 10 pages/run.

Idempotent create locks seller quota/spend rows, verifies the current receipt, reserves concurrency/spend, writes job/audit/outbox state, and commits before enqueue. Same owner/key/request hash returns the original safe response; changed hash is `409`. Start ambiguity uses `reconcile_start` with the same request and deterministic ECS token. Attempt 2 is forbidden while attempt 1 start is unresolved and is allowed only once for the Gate 1 infrastructure classes.

Cancellation locks the job. Queued becomes terminal immediately. Live states become `cancel_requested`, revoke further validation, and send exact broker cancel under the current task binding. A successful evidence transaction and cancellation/expiry race have one database winner: success is valid only if its transaction locks a still-`validating_result` row before cancellation/expiry commits. Late output is deleted and recorded only as a safe stale-result code.

Worker death leaves the task/provider state unchanged, late acknowledgement requeues, and the next lease owner reconciles the existing request/task. Broker/transport ambiguity never becomes access denial. At every terminal outcome the controller observes or stops the exact task, deletes request and result, exact-prefix lists with `MaxKeys=2` to prove absence, records cleanup times/hashes, releases concurrency/spend reservation, and clears the lease. The one-day bucket lifecycle is a backstop, not cleanup proof.

## 10. Observability, redaction, and retention

`app/core/seller_workspace_profile_metrics.py` exposes only counters/histograms labeled by fixed provider `aws`, format enum, state, attempt `1|2`, and safe failure code. Metrics include jobs/attempts/transitions, phase seconds, bytes/rows/fields bands, cancellations/timeouts/reconciliations, cleanup success/failure, lease steals, schema rejections, spend-reservation high amount, and redaction-canary detections. Seller, connection, job, object, bucket, key, ARN, field token, receipt, and exception text are prohibited labels.

Application logs are structured allowlist events emitted by W3 code, never interpolation of request/provider/parser objects or exceptions. Allowed keys are event code, state, attempt, safe failure code, duration/quantity bands, runtime-version hash prefix, and correlation ID. `exc_info`, exception string/repr, boto response, Celery args, selector, evidence JSON, request/result bytes, and task stderr are forbidden. OpenTelemetry spans use only the same allowlist; HTTP/Celery instrumentation hooks suppress request/response bodies and task arguments for the W3 route/queue.

`seller_workspace_audit.py` adds exactly these W3 operations to the append-only operation allowlist: `profile_source_key_set_registered`, `profile_source_key_set_unchanged`, `profile_runtime_standing_estimate_created`, `profile_runtime_standing_cost_acknowledged`, `profile_runtime_authorized`, `profile_runtime_verification_requested`, `profile_runtime_verified`, `profile_runtime_verification_rejected`, `profile_runtime_disabled`, `profile_selector_created`, `profile_marginal_estimate_created`, `profile_job_cost_acknowledged`, `profile_job_created`, `profile_job_transitioned`, `profile_job_start_reconciled`, `profile_job_retry_created`, `profile_job_cancel_requested`, `profile_job_cancelled`, `profile_job_failed`, `profile_job_expired`, `profile_attempt_cleanup_recorded`, `profile_evidence_committed`, and `profile_evidence_expired`. No generic or free-form operation is allowed.

Each W3 audit row uses the existing append-only insert path and may contain only the following exact snapshot keys, omitting inapplicable keys rather than inserting ad hoc null fields:

- lifecycle authorization and actor: `actor_kind`, `actor_id`, `operation`, `decision`, `safe_outcome`, `safe_failure_code`;
- ownership and immutable binding: `seller_id`, `connection_id`, `runtime_id`, `runtime_version`, `runtime_authorization_id`, `job_id`, `attempt`, `selector_id`, `selector_version`, `source_key_set_version`, `quota_profile`;
- standing and marginal cost authority: `standing_estimate_receipt_id`, `standing_estimate_receipt_hash`, `marginal_estimate_receipt_id`, `marginal_estimate_receipt_hash`, `cost_acknowledgement_actor_kind`, `cost_acknowledgement_actor_id`, `cost_acknowledged_at`, `cost_acknowledgement_event_id`;
- lifecycle state and versions: `prior_state`, `new_state`, `resource_version`, `replayed`, `price_table_version`, `estimate_model_version`, `currency`;
- safe integrity and runtime bindings: `source_key_set_hash`, `input_hash`, `selector_hash`, `estimate_receipt_hash`, `runtime_verification_receipt_hash`, `semantic_hash`, `attestation_hash`, `result_integrity_hash`, `request_sha256`, `task_arn_hash`, `ecs_client_token_hash`, `template_digest`, `broker_alias_arn_hash`, `verifier_alias_arn_hash`, `task_definition_digest`, `image_digest`, `network_hash`, `dns_firewall_hash`, `resolver_control_hash`, `cleanup_proof_hash`;
- parser/image/task provenance: `parser_version`, `evidence_schema_version`, `field_token_key_version`, `task_definition_version`; and
- bounded result reference and counters: `evidence_ref`, `objects_completed`, `source_bytes_read`, `decompressed_bytes`, `rows_examined`, `field_records_emitted`, `attempt_count`.

Those names are the complete W3 snapshot allowlist; nested arbitrary maps and additional keys fail before persistence. The audit service validates safe enum/token/hash/version/UUID/RFC3339/integer shapes, same-seller ownership, and applicable receipt/acknowledgement bindings before insert. Scope is hashed before persistence. Raw AWS errors map at the adapter boundary to enumerated codes.

Append-only tests cover every operation and every allowlisted key, both standing and marginal acknowledgement actor/time/event bindings, prior/new state, seller/connection/runtime/job/attempt/selector ownership, all safe hashes/versions and parser/image/task-definition provenance, decision/outcome, evidence reference, replay, and bounded counters. They prove an update or delete is rejected and that every unknown key is rejected. Golden redaction tests continue to forbid raw source identifiers or values, source-key ARNs, selector object identities, AWS response bodies, request/result bytes, full task ARNs or ECS tokens, credentials/secrets, exception strings/reprs/tracebacks, parser stderr, URLs, emails, prompts, markup/tool syntax, and all other free text.

Hostile fixtures seed unique markers resembling AWS keys, bearer tokens, URLs, emails, prompts, JSON tool calls, HTML/Markdown, ANSI/control sequences, CSV formulas, SQL, shell, traceparent, bucket/key/ARN, headers, JSON keys, Parquet names/metadata, values, min/max, and exception text. Runtime-only hostile canaries may be constructed during test execution from separately stored non-triggering fragments. Source identifiers, variable names, and fixture keys use neutral symbolic names that do not themselves match blocked scanner patterns. Tests scan PostgreSQL JSON/text, unencrypted bytea projections, Redis/Celery messages/results, captured logs, trace exporter payloads, audit, evidence, and HTTP for every marker, and separately prove that W3 has no allAI/LLM envelope or call path.

Failed/cancelled/expired rows retain only redacted state/hashes/counters for 30 days. Successful evidence payload expires at 30 days; W3 cannot create a longer W4 reference. Expiry nulls/deletes payload and retains immutable hash/deletion proof. Task/audit log groups expire after seven days. No W3 Resolver query logging, VPC Flow Logs, bucket access log, inventory, replication, backup, or Object Lock resource is created.

## 11. Migration, rollback, and capability truth

`20260902_001_s1650_seller_workspace_w3.py` creates the nine tables and one nullable audit FK/index in dependency order. It sets `lock_timeout='5s'`, creates no W3 rows, updates no W2 row, and does not inspect or touch listing/order/delivery/serial data. Upgrade is tested on empty and realistic W2-populated PostgreSQL. The unchanged W2 PostgreSQL test must pass against its pre-W3 `s1648_issue_channel_repair` fixture without an eager `profile_job_id` projection; W3 PostgreSQL tests migrate forward and prove the new column, composite foreign key, index, and explicit W3 loading/use.

Downgrade first queries every W3 table. If any W3 row exists it raises a reviewed `RuntimeError` and leaves the additive schema inert. Only an empty W3 estate may drop the audit FK/column and W3 tables in reverse order. Rollback with data is flags-off plus code rollback, never destructive downgrade.

All nine flags remain false by default and in every deployment configuration:

- `SELLER_WORKSPACE_ENABLED=false`;
- `SELLER_WORKSPACE_AWS_CONNECT_ENABLED=false`;
- `SELLER_WORKSPACE_AWS_PROFILE_ENABLED=false`;
- AWS publish/delivery false; and
- all four R2 flags false.

`capability_payload` continues to report profile `not_implemented` until the full reviewed implementation is present. After implementation, it reports profile available only if master/connect/profile flags are explicitly true, W2 and W3 implementation markers are true, principal/KMS configuration is valid, the dedicated worker heartbeat is fresh, price table is current, and the exact connection/runtime is verified. A table, route, stack, image, environment typo, or partial deployment never creates capability truth. This Gate 2 work does not enable any flag.

Rollback order is profile flag off, refuse/terminally cancel new/queued jobs, stop/reconcile live tasks, prove control-object cleanup, retain allowed audit/evidence, roll back web/control worker, leave schema inert, and let the seller decide whether to delete its stack. W2 connection status/ExternalId, AIM Data, publication/delivery, and `legacy_serial` remain untouched.

## 12. Focused test and hostile-fixture matrix

The implementation adds these exact test files:

- `tests/test_s1650_profile_contracts.py` — strict HTTP/verifier/broker/task-output/evidence schemas, canonical hashes, size ceilings, no-store errors, capability off, and no W3 allAI/LLM schema or call path;
- `tests/test_s1650_profile_authorization.py` — two sellers, foreign/absent equivalence, cursor/idempotency/cache/token isolation, record-specific encryption AAD, list-only W2 correction;
- `tests/test_s1650_profile_lifecycle.py` — every transition, lease steal/expiry, redelivery, both start crash windows, retry, cancel/success/expiry races, worker death, task death, cleanup;
- `tests/test_s1650_profile_postgres.py` — real PostgreSQL migration, constraints, composite ownership, exact append-only audit operations/safe snapshots, empty/nonempty downgrade;
- `tests/test_s1650_profile_aws.py` — STS policies, closed envelopes, IAM simulation fixtures, broker/verifier positive/negative calls, complete multi-CIDR autodefined inventory, exact Gate 1 verifier action-set closure, and pagination;
- `tests/test_s1650_profile_iac.py` — isolated hash-locked `cfn-lint==1.50.1`, parsed exact resources/policies/routes/endpoints/DNS rules/roles/task settings and prohibited-resource absence;
- `tests/test_s1650_profile_observability.py` — metric cardinality, audit allowlist/forbidden-field rejection, canary absence in logs/traces/Redis/Celery/database/audit/HTTP, and zero allAI/LLM path;
- `seller_workspace_profile_runtime/tests/test_csv.py`, `test_json.py`, `test_parquet.py`, `test_supervisor.py`, and `test_golden_evidence.py`; and
- `tests/fixtures/seller_workspace_profile/generate.py` and `tests/fixtures/seller_workspace_profile/expected.json`, which generate only temporary synthetic benign, boundary, bomb, malformed, and hostile files and bind their expected canonical JSON/hashes. No customer-derived or opaque binary fixture is committed.

The matrix includes zero/one/ten/eleven objects; every byte/row/field/result boundary at `limit-1`, `limit`, and `limit+1`; 0/8/9 source KMS keys; current/version selectors; ETag/version drift; every CSV encoding/dialect/quote/multiline/ragged/header case; duplicate JSON keys, deep nesting, huge number, malformed JSONL; each locked Parquet codec, bad footer/page metadata, encrypted/external metadata; decompression/allocation bombs; unsupported archives with one and nested members; resource/CPU/wall kills; deterministic repeats; and every hostile marker above.

The W2 safety suite is a mandatory compatibility gate: B1, B2A, and PostgreSQL remain byte-for-byte unchanged; B2B changes only `test_workspace_verifier_uses_exact_prefix_policy_and_900_second_session` as specified in Sections 2 and 5; every other B2B test remains byte-for-byte unchanged; and all four files must pass. The unchanged PostgreSQL test proves legacy repositories remain safe on the pre-W3 s1648 fixture, while `tests/test_s1650_profile_postgres.py` proves the W3 column/FK/index after migration and explicit W3 use of `profile_job_id`.

AWS fixtures cover both exact `/24` CIDRs and required reverse domains; zero, one and many additional AWS-owned autodefined rules of varying service-observed `RuleType`; missing/duplicate/malformed/wrong-owner/wrong-namespace/nonterminal/shared/endpoint-bearing rules; missing required reverse-domain membership; third/partial CIDR; IPv6; allowed private-hosted-zone-added service rules; private-hosted-zone-added non-autodefined/endpoint-bearing/shared/malformed/foreign-owner/nonterminal rules; outbound endpoint; Profile association; pagination omission or overflow beyond the deliberate 20-page/1,000-record W3 guardrail; API denial; and any verifier call or IAM action outside the exact approved Gate 1 set. Tests prove `RuleType` drift alone cannot admit or reject a rule, an allowed PHZ contribution passes only under the closed rule predicate, and any identity, endpoint, status, pagination, required-multi-CIDR, or action-set mismatch fails closed. Golden tests assert the exact five-key Gate 1 resolver-control preimage and hash; required reverse-rule presence and complete service-owned inventory affect eligibility only and never add hash fields.

Backend/control focused commands, run from the backend `.venv` that intentionally contains no PyArrow or parser-only dependency, are:

```text
.venv/bin/python -m pytest -q tests/test_s1650_profile_contracts.py tests/test_s1650_profile_authorization.py tests/test_s1650_profile_lifecycle.py tests/test_s1650_profile_postgres.py tests/test_s1650_profile_aws.py tests/test_s1650_profile_iac.py tests/test_s1650_profile_observability.py
.venv/bin/python -m pytest -q tests/test_s1647_seller_workspace_b1.py tests/test_s1647_seller_workspace_b2a.py tests/test_s1647_seller_workspace_b2b.py tests/test_s1647_seller_workspace_postgres.py
.venv/bin/python -m pytest -q tests/test_delivery_endpoints.py tests/test_delivery_guarantees.py tests/test_delivery_service.py tests/test_delivery_webhook_integration.py tests/test_serial_serial_id_contract.py tests/test_serial_service.py tests/test_source_delivery.py
.venv/bin/alembic heads
.venv/bin/python infra/seller_workspace_profile/package.py --check
```

Gate 3 bootstraps and runs the linter in a disposable CI temporary directory, never in the backend environment. `infra/seller_workspace_profile/requirements-cfn-lint.lock` must contain `cfn-lint==1.50.1` and every transitive distribution with exact SHA-256 hashes; floating requirements, unhashed downloads, `pipx`, a developer `.venv`, and backend dependency-file edits fail the build. Cleanup is mandatory on success and failure:

```text
S1650_CFN_LINT_VENV="$(mktemp -d "${RUNNER_TEMP:-${TMPDIR:-/tmp}}/s1650-cfn-lint.XXXXXX")"
trap 'rm -rf -- "${S1650_CFN_LINT_VENV:?}"' EXIT
python3.11 -m venv "$S1650_CFN_LINT_VENV"
"$S1650_CFN_LINT_VENV/bin/python" -m pip install --require-hashes -r infra/seller_workspace_profile/requirements-cfn-lint.lock
"$S1650_CFN_LINT_VENV/bin/cfn-lint" --version
"$S1650_CFN_LINT_VENV/bin/cfn-lint" infra/seller_workspace_profile/template.yaml
rm -rf -- "${S1650_CFN_LINT_VENV:?}"
trap - EXIT
```

Runtime parser tests run in a separate disposable CI temporary environment created from the runtime locks, never inside the repository checkout or backend environment. Cleanup is mandatory on success and failure:

```text
S1650_RUNTIME_TEST_VENV="$(mktemp -d "${RUNNER_TEMP:-${TMPDIR:-/tmp}}/s1650-profile-runtime.XXXXXX")"
trap 'rm -rf -- "${S1650_RUNTIME_TEST_VENV:?}"' EXIT
python3.11 -m venv "$S1650_RUNTIME_TEST_VENV"
"$S1650_RUNTIME_TEST_VENV/bin/python" -m pip install --require-hashes -r seller_workspace_profile_runtime/requirements.lock
"$S1650_RUNTIME_TEST_VENV/bin/python" -m pip install --require-hashes -r seller_workspace_profile_runtime/requirements-test.lock
"$S1650_RUNTIME_TEST_VENV/bin/python" -m pytest -q seller_workspace_profile_runtime/tests
docker build --no-cache -f seller_workspace_profile_runtime/Dockerfile seller_workspace_profile_runtime
rm -rf -- "${S1650_RUNTIME_TEST_VENV:?}"
trap - EXIT
```

Dependency/import scans fail on any AIM Data module/package/database/install identity/serial/tunnel/broker client/container dependency, on PyArrow/parser imports in the backend web/control image, and on any W3 allAI/LLM schema, builder, gateway, task, route, import, or call. The separate runtime environment proves the exact locked PyArrow parser surface without claiming or requiring PyArrow in the backend `.venv`.

The existing repository secret-scan gate must pass for the complete candidate without a bypass, suppression, scanner-configuration change, or allowlist expansion. Hostile runtime canaries follow the non-triggering-fragment construction rule in Section 10, and neutral symbolic source names replace identifiers that themselves match blocked scanner patterns.

## 13. Exact Gate 3 and Gate 4 proof

Gate 3 requires one immutable candidate whose changed-path set equals the closed 55-path Section 2 manifest exactly, with no unlisted path and no missing row. The path-set evidence must classify the workflow-produced broker ZIP, verifier ZIP, package/schema digest manifest, OCI manifest/digest, SBOM, and vulnerability report as generated evidence rather than repository diff paths. It must prove `requirements.txt`, `requirements-dev.txt`, W2 B1/B2A/PostgreSQL, every B2B test other than the one named verifier-policy test, `railway.worker.json`, Gate 1, and every delivery/serial/`legacy_serial` file unchanged; the B2B diff must contain only that test. The candidate also requires exact base and diff, clean build, single Alembic head, all backend and separately locked runtime focused commands passing, the unchanged existing secret-scan gate passing without bypass or allowlist expansion, the Section 12 isolated hash-locked `cfn-lint==1.50.1` bootstrap and lint command passing, package/image/SBOM/vulnerability identities, CloudFormation digest, schema digests, default-off configuration proof, unchanged Gate 1 digest, and proof that verifier calls and IAM permissions contain no action outside the exact Gate 1 Section 6.3 set.

Before launch enforcement can be accepted, Gate 3 must also pin the regional price-table and estimate-model versions and supply the Section 7.1 worst-case recomputation showing every absolute USD cap is conservative for each supported region/AZ/endpoint placement and the full two-attempt envelope. Static review, manifest closure, backend tests, runtime tests, package checks, image scan, migration, IaC review, price-model validation, and legacy tests are separate evidence. Independent CC, GLM, and DeepSeek must review the exact Gate 3 commit; the builder is excluded.

Gate 4 requires the exact reviewed backend/control-worker/image/template identities deployed with every production Seller Workspace flag still false, plus a separately authorized synthetic harness. It uses two synthetic seller identities and two seller-owned synthetic stacks/bucket prefixes, never customer credentials/data. Evidence is one immutable redacted receipt binding:

1. deployed Git/image/Lambda/template/task-definition/alias/worker identities and healthy schema head;
2. production capability off before and after, with no public claim or public route availability;
3. normal authorized Chrome proof that the production seller surface exposes no W3 capability while flags are off;
4. controlled synthetic runtime proof of list-only ai.market authority and task-only source reads for CSV, JSON, and Parquet golden/hostile fixtures;
5. complete live two-CIDR autodefined Resolver inventory matching section 3.1, DNS Firewall fail closed, exact allow/redirection success, arbitrary/encoded/ai.market/allAI/unapproved redirect DNS `NODATA`, and no network connection;
6. IAM simulation plus live denied calls for source body/attributes by ai.market/verifier/broker, foreign source/control objects, request overwrite, result read, ECS override/list, role pass, secret/KMS misuse, infrastructure mutation, and cross-seller access;
7. two-seller HTTP/database/cursor/Redis/Celery/cache/field-token/evidence isolation with identical hostile IDs and markers;
8. start reconciliation at both crash windows, one task identity, cancellation in every live phase, 3/10/2/20-minute timeouts, worker/task SIGKILL, one permitted retry, late-result rejection, and terminal cleanup;
9. exact standing/marginal receipt recomputation and every object/byte/row/column/archive/compression/nesting/CPU/memory/wall/retry/concurrency/spend ceiling;
10. canonical semantic hashes stable across attempts/runtime telemetry and all three integrity hashes independently recomputed;
11. zero whole-object persistence and zero hostile/raw marker in database, Redis/Celery, logs, traces, audit, evidence, HTTP, or allAI; and
12. unchanged W2 lifecycle and complete unchanged `legacy_serial` selection.

The synthetic harness may create temporary CloudTrail data selectors, Resolver query logging, and VPC Flow Logs only under separate Gate 4 authorization and budget, with synthetic-only sources and bounded retention; it deletes them and proves deletion. None becomes product IaC. CloudFormation success, an ECS `STOPPED` event, a route response, a queue label, or a merged/deployed status substitutes for none of the other proofs.

## 14. Strict exclusions and dispatch gate

This specification changes no Gate 1 text and preserves its non-custodial architecture. It adds no frontend, listing draft, publication, sample, order, delivery authority, R2, W4/W5, AIM Data runtime, public endpoint claim, customer account, customer credential, customer data, or `legacy_serial` behavior. It authorizes no AWS, Railway, ECR, Lambda, ECS, Route 53, KMS, S3, provider, database, or feature-flag mutation now.

The next permitted action after this candidate is review only. **No MP/build agent, implementation worker, deployment workflow, AWS/provider operation, migration, image build intended for release, or code change may be dispatched until CC, GLM, and DeepSeek independently approve this exact Gate 2 file SHA-256 and that unanimous approval is recorded against `build:bq-seller-workspace-w3-profiling-s1650`.** Any edit after review creates a new digest and requires a fresh complete panel.

## 15. Primary technical references

- AWS autodefined Resolver inventory: <https://docs.aws.amazon.com/Route53/latest/DeveloperGuide/resolver-overview-forward-vpc-to-network-autodefined-rules.html>
- Resolver rule associations and types: <https://docs.aws.amazon.com/Route53/latest/APIReference/API_route53resolver_ListResolverRuleAssociations.html>
- Route 53 Profile associations: <https://docs.aws.amazon.com/Route53/latest/APIReference/API_route53profiles_ListProfileAssociations.html>
- DNS Firewall VPC fail mode: <https://docs.aws.amazon.com/Route53/latest/APIReference/API_route53resolver_GetFirewallConfig.html>
- Fargate ephemeral-storage KMS: <https://docs.aws.amazon.com/AmazonECS/latest/developerguide/fargate-create-storage-key.html>
- ECS `RunTask` idempotency: <https://docs.aws.amazon.com/AmazonECS/latest/developerguide/ECS_Idempotency.html>
- ECR private endpoints and regional layer bucket: <https://docs.aws.amazon.com/AmazonECR/latest/userguide/vpc-endpoints.html>
