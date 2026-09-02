# BQ-SELLER-WORKSPACE-W3-PROFILING-S1650 Gate 2 implementation specification

**Status:** `AUTHORED_PENDING_REVIEW`. This is a specification-only candidate. Implementation dispatch is forbidden until independent CC, GLM, and DeepSeek reviews each approve this exact Gate 2 commit and this file's exact SHA-256. An earlier Gate 1 vote, a vote on another digest, `APPROVE_WITH_NITS` with an unresolved mandate, a provider error, or a substituted reviewer is not approval.

**Build Queue entity:** `build:bq-seller-workspace-w3-profiling-s1650`

**Expected branch:** `spec/bq-seller-workspace-w3-profiling-s1650-gate2-s1653`

**Approved Gate 1 base:** commit `d65c11cbf1bccb8f5a98cb07b0f69983bdfe7b4b`, file `specs/BQ-SELLER-WORKSPACE-W3-PROFILING-S1650-GATE1.md`, SHA-256 `4ff20a4fd80038d572d22db599e3ca7aa9e8fed745bd5ef3efe793ec18d0aa9b`.

**Inspected implementation base:** canonical ai.market backend `main` at `31efd4c607ace06319bbbbc697834584952f7ed9` (2026-09-02). Its single Alembic head is `s1648_issue_channel_repair`. This specification names the exact integration points present at that commit; a builder must stop and request a rebase review if any named path, signature, head, queue, or deployment manifest has drifted.

## 1. Frozen outcome and exclusions

Gate 1 remains authoritative. W3 is a default-off AWS profiling implementation in which ai.market is an authenticated metadata-only control plane and raw source bytes are read only inside one ephemeral task in the seller's AWS account. Max's recorded choices remain D1=A and D2=A: exact field names stay inside that seller account, and the seller acknowledges and pays bounded AWS-native runtime costs.

This Gate 2 authorizes only a future implementation candidate after the review gate above. It does not authorize deployment, AWS or provider mutation, customer credentials or data, a live stack, feature enablement, a public capability claim, W4, W5, R2, AIM Data runtime/package/service import, listing creation, publication, sample generation, delivery, or any change to `legacy_serial` or `legacy_serial_id`. All fixtures, accounts, buckets, objects, roles, keys, identities, and browser journeys must be synthetic and purpose-created.

All Seller Workspace flags remain false in every committed and deployed configuration:

- `SELLER_WORKSPACE_ENABLED=false`;
- `SELLER_WORKSPACE_AWS_CONNECT_ENABLED=false`;
- `SELLER_WORKSPACE_AWS_PROFILE_ENABLED=false`;
- `SELLER_WORKSPACE_AWS_PUBLISH_ENABLED=false`;
- `SELLER_WORKSPACE_AWS_DELIVERY_ENABLED=false`;
- all four `SELLER_WORKSPACE_R2_*` flags remain false.

The implementation may set an internal `AWS_PROFILE_IMPLEMENTED=True` marker only when all reviewed code exists. That marker is not availability: the capability response remains `disabled` while flags are false and must fail closed as `unavailable` when any runtime, queue, price-table, migration, or health prerequisite is absent. No frontend, allAI, route discovery, environment variable, or stack existence may infer availability.

## 2. Existing integration points and required file manifest

The canonical backend already registers `app.api.v1.endpoints.seller_workspace.router` from `app/api/v1/router.py`; provides `SellerWorkspaceNoStoreRoute`, `require_active_seller`, `require_idempotency_key`, uniform safe HTTP errors, and `/api/v1/seller-workspace` routes in `app/api/v1/endpoints/seller_workspace.py`; defines W2 wire models in `app/schemas/seller_workspace.py`; defines `CloudConnection`, `CloudConnectionCredential`, append-only `SellerWorkspaceAuditEvent`, and inactive `DeliveryAuthority` in `app/models/seller_workspace.py`; and implements owner-scoped transactions in `app/services/seller_workspace_connection.py`.

The read-only W2 IaC/deployment inspection found no Seller Workspace CloudFormation, Terraform, or CDK module to extend. W2's seller-account setup surface is the exact trust-policy JSON produced by `SellerWorkspaceConnectionService._build_authorization()` and the list-plus-`HeadObject` session policy in `BotoAWSConnectionVerifier._verify_sync`; backend deployment uses `Dockerfile`, `railway.toml`, `railway.worker.json`, and `railway.beat.json`. The durable W2 schema is `alembic/versions/20260831_001_s1647_seller_workspace_w2.py`, and its live evidence is recorded in `seller-workspace-cloud-listing-delivery.md` plus `receipts/s1648-seller-workspace-gate4-redacted.json`. Gate 2 therefore introduces the first Seller Workspace AWS template at the exact new path below and does not pretend an existing W2 IaC abstraction exists.

The builder must preserve those seams. It must not create a second Seller Workspace router, generic cloud repository, generic workflow engine, generic parser platform, or new queueing system.

### 2.1 Exact backend changes

| Path | Exact change |
| --- | --- |
| `app/core/seller_workspace_config.py` | Add the W3 numeric constants in sections 7, 8, and 11, `AWS_PROFILE_IMPLEMENTED`, profile readiness inputs, `require_aws_profile()`, and truthful dependency-aware capability projection. Defaults stay false. |
| `app/models/seller_workspace.py` | Add the W3 enums and ORM models in section 5; retain the W2 tables and `DeliveryAuthorityKind.legacy_serial` byte-for-byte in behavior. |
| `app/schemas/seller_workspace.py` | Add strict `extra="forbid"` request/response models for the routes in section 6 and the exact evidence models in section 9. Do not loosen W2 models. |
| `app/api/v1/endpoints/seller_workspace.py` | Add the W3 routes to the existing router, reuse `SellerWorkspaceNoStoreRoute`, `require_active_seller`, `_seller_context`, `require_idempotency_key`, and the safe-error mapper, and require `If-Match` where section 6 says so. |
| `app/services/seller_workspace_connection.py` | Replace `BotoAWSConnectionVerifier._verify_sync`'s `s3:GetObject`/`HeadObject` proof with bounded `ListObjectsV2` and optional `ListObjectVersions`; keep the existing `assume_seller_role`, 900-second session, exact ExternalId, owner binding, and normalized provider errors. This change is activation-blocking and has no central object-read fallback. |
| `app/services/seller_workspace_audit.py` | Extend the closed operation/purpose/snapshot allowlists only with the exact W3 fields in section 10. Never accept arbitrary mappings or raw provider errors. |
| `app/services/seller_workspace_profile_encryption.py` | New purpose-bound AES-GCM envelope service for only `source_kms_arns`, `selector_object_identities`, and `task_arn`, using the existing `app.services.kms_service.kms_service`, per-record DEKs, versioned AAD, and destructive clearing. Do not widen `SellerWorkspaceEnvelopeEncryption`, whose existing purpose allowlist is ExternalId-only. |
| `app/services/seller_workspace_profile_contracts.py` | New RFC 8785 canonicalization, duplicate-key rejection, strict evidence/result verification, hash construction, field-token input encoding, deterministic metadata scanner, and the dormant allAI eligibility projection. |
| `app/services/seller_workspace_profile_aws.py` | New closed adapters for connection-scoped list discovery and exact verifier/broker alias invocations. It may use `assume_seller_role` but exposes no general boto client and no source `GetObject*` method. |
| `app/services/seller_workspace_profile_costs.py` | New immutable standing/marginal receipt calculator over the versioned USD price table and the hard spend ceilings in section 11. |
| `app/services/assets/seller_workspace_profile_aws_price_table_usd_v1.json` | New immutable, schema-validated USD unit-price table with effective/expiry timestamps, source references, integer rational rates, and a self-digest. Missing, stale, or unknown units fail closed. |
| `app/services/seller_workspace_profile.py` | New owner-scoped repository/service for source-key sets, nonces, runtimes, selectors, estimates, jobs, attempts, leases, transitions, evidence, cancellation, expiry, and cleanup. Use the existing `AsyncSession`; transaction and row/advisory locks are the authority. |
| `app/allai/schemas/seller_workspace_profile.py` | New strict dormant `SellerWorkspaceProfileAllAIInputV1` allowlist from section 10. It is a validation boundary only and has no agent/provider/dispatch import. |
| `app/tasks/seller_workspace_profile.py` | New metadata-only Celery tasks `seller_workspace_profile.dispatch_outbox`, `seller_workspace_profile.reconcile_job`, and `seller_workspace_profile.expire_and_cleanup`; no parser, S3 source client, field name, selector plaintext, task ARN plaintext, or raw result may enter the Celery body/result. |
| `app/core/celery_app.py` | Add the task module, `Queue("seller_workspace_profile_control", routing_key="seller_workspace_profile_control")`, and 30-second outbox/reconciliation plus 60-second retention sweeps routed only to that queue. Existing queues and schedules remain unchanged. |
| `app/core/seller_workspace_profile_metrics.py` | New low-cardinality OpenTelemetry instruments and label allowlists from section 12. |
| `alembic/versions/20260902_001_s1650_seller_workspace_w3.py` | One additive revision: `revision="s1650_seller_workspace_w3"`, `down_revision="s1648_issue_channel_repair"`; exact schema in section 5. |
| `railway.seller-workspace-profile-worker.json` | New separately deployable worker manifest using the existing `Dockerfile`, one replica, and `celery -A app.core.celery_app worker --loglevel=info --concurrency=4 --prefetch-multiplier=1 -Q seller_workspace_profile_control`. It is not added to or deployed in production until Gate 4 authority. |
| `requirements.txt` | Add only the backend canonical-JSON/schema dependencies required by the reviewed implementation, pinned within the repository's existing dependency policy. Parser libraries do not enter the backend image. |

`app/api/v1/router.py`, `alembic/env.py`, `railway.worker.json`, `railway.beat.json`, and `scripts/start_celery.sh` require no edit: the existing router/model import and shared workers remain valid, and the W3 queue must never be consumed by the shared worker.

### 2.2 Exact seller-runtime, IaC, and build files

| Path | Exact responsibility |
| --- | --- |
| `seller_workspace_profile_runtime/pyproject.toml` and `seller_workspace_profile_runtime/requirements.lock` | A separately locked Python 3.11 runtime containing only boto3/botocore, Pydantic, RFC-8785 canonicalization, PyArrow, and their reviewed transitive dependencies. No backend, allAI, AIM Data, DuckDB extension, database, HTTP client, shell, or plugin package. |
| `seller_workspace_profile_runtime/Dockerfile` | Multi-stage, digest-reproducible, non-root task image with read-only root filesystem expectation, fixed `python -m seller_profile_task`, no shell entrypoint, no package manager in the final stage, and OCI source/revision labels. |
| `seller_workspace_profile_runtime/src/seller_profile_task/{__init__.py,__main__.py,limits.py,canonical.py,contracts.py,s3_reader.py,scanner.py,csv_parser.py,json_parser.py,parquet_parser.py,supervisor.py}` | One fixed entrypoint, closed contracts, bounded S3 range reader, deterministic parsers/scanner, HMAC tokenization, resource-limited child, and content-free supervisor failures. |
| `seller_workspace_profile_runtime/lambda/{common.py,broker.py,verifier.py}` | Two separately packaged handlers sharing only closed envelope/canonical helpers. `broker.handler` alone can launch/poll/stop and touch exact control objects; `verifier.handler` is read-only. |
| `seller_workspace_profile_runtime/schemas/{task_request.v1.json,task_output.v1.json,result.v1.json,runtime_verification.v1.json,allai_input.v1.json}` | Checked-in JSON Schemas with `additionalProperties:false`, numeric maxima, regex/enum constraints, and digest manifest. Pydantic and JSON-Schema representations must have a test-proved identical field set. |
| `seller_workspace_profile_runtime/schema-digests.json` | Sorted mapping from schema path to SHA-256; covered by the runtime manifest and template parameters. |
| `infra/seller_workspace_profile/template.yaml` | The single seller-inspectable CloudFormation template implementing section 4. No CDK, Terraform, generated second template, or hidden mutation path. |
| `infra/seller_workspace_profile/parameters.schema.json` | Closed owner-visible parameter contract, including exact connection, account, region, source scope, zero-to-eight source-key ARNs, one primary plus up to four secondary IPv4 CIDRs, two or three AZs, exact immutable image digest, and Lambda package digests. |
| `infra/seller_workspace_profile/iam-negative-cases.json` | Synthetic IAM simulator matrix for every explicit allow and deny in Gate 1; no credential or live ARN. |
| `scripts/build_seller_workspace_profile_runtime.py` | Deterministically build broker/verifier ZIPs, image context, schemas, SBOMs, and one canonical manifest; refuse a dirty source tree, mutable image tag identity, missing digest, or schema drift. It performs no push or deployment. |
| `.github/workflows/seller-workspace-profile-runtime.yml` | Gate-only lint/test/build/SBOM/signature-verification workflow. It has no AWS credential, ECR push, CloudFormation deploy, or Railway deploy step. |

### 2.3 Exact focused test and fixture files

Extend, rather than replace, the inspected W2 tests:

- `tests/test_s1647_seller_workspace_b1.py` for unchanged models, encryption, migration ancestry, and `legacy_serial`;
- `tests/test_s1647_seller_workspace_b2a.py` for the list-only W2 verifier and unchanged owner/idempotency/rotation behavior;
- `tests/test_s1647_seller_workspace_b2b.py` for route registration, default-off truth, no-store, active-seller auth, and safe failures; and
- `tests/test_s1647_seller_workspace_postgres.py` for W2 data survival and append-only audit behavior on real PostgreSQL.

Add:

- `tests/test_s1650_seller_workspace_w3_models.py`;
- `tests/test_s1650_seller_workspace_w3_api.py`;
- `tests/test_s1650_seller_workspace_w3_authorization.py`;
- `tests/test_s1650_seller_workspace_w3_lifecycle.py`;
- `tests/test_s1650_seller_workspace_w3_costs.py`;
- `tests/test_s1650_seller_workspace_w3_redaction.py`;
- `tests/test_s1650_seller_workspace_w3_worker.py`;
- `tests/test_s1650_seller_workspace_w3_migration.py`;
- `seller_workspace_profile_runtime/tests/test_{contracts,s3_reader,csv,json,parquet,supervisor,broker,verifier,template}.py`; and
- only synthetic fixtures under `tests/fixtures/seller_workspace_profile_v1/`: `golden.csv`, `golden.tsv`, `golden.json`, `golden.jsonl`, `hostile.csv`, `hostile.jsonl`, `hostile_values.json`, `parquet_cases.json`, `expected_semantics.json`, and `expected_allai_input.json`. Parquet binaries are deterministically generated from `parquet_cases.json` into a temporary test directory and are never customer-derived.

## 3. Exact identities and non-custody boundary

One `CloudConnection` continues to identify the owning seller, AWS account, region, role ARN, bucket, non-root prefix, and random encrypted ExternalId. W3 adds one immutable runtime version per connection. The execution chain is fixed:

1. ai.market assumes only `CloudConnection.role_arn` through the existing `assume_seller_role` using the connection's encrypted ExternalId and a 900-second session policy.
2. That session may list the exact source prefix and invoke only the immutable verifier and broker aliases. It has no source object action, ECS, IAM, KMS, Secrets Manager, Logs, or second STS hop.
3. The verifier alias runs as the seller-account verifier role and returns a closed hash receipt only.
4. The broker alias runs as the distinct seller-account broker role. It creates/reconciles one immutable request, runs/polls/stops only the pinned task definition on the pinned cluster, validates one result, deletes both artifacts, and returns the closed result.
5. ECS uses a distinct task-execution role only for the exact ECR digest and metadata log stream.
6. The task role alone reads selected source ranges, decrypts only registered source keys through S3, reads the one HMAC secret and exact request, and writes the one result. It cannot assume a role or call ai.market/allAI.

Immutable execution identity is the tuple `(seller_id, connection_id, runtime_version, verified_stack_id_hash, broker_alias_arn_hash, verifier_alias_arn_hash, cluster_arn_hash, task_definition_arn_hash, image_digest, template_digest, schema_digest_set_hash, source_key_set_hash, network_hash, dns_firewall_hash, resolver_control_hash)`. Every start, poll, cancel, result, estimate, job, attempt, audit row, and verifier receipt binds that tuple or its defined subset. A mutable Lambda `$LATEST`, unqualified function ARN, image tag, task-definition family without revision, changed schema digest, changed network, or changed source-key set is ineligible.

No ai.market role or process may instantiate an S3 source-object body client. `app/services/seller_workspace_profile_aws.py` exposes only prefix listing and Lambda invocation. A repository scan must fail on `get_object`, `head_object`, `get_object_attributes`, or `download_file` in `app/`, except unrelated pre-existing modules on an explicit reviewed baseline list; the W3 modules have an empty exception list.

## 4. CloudFormation and complete VPC/Resolver inventory

`infra/seller_workspace_profile/template.yaml` creates exactly the Gate 1 topology: one VPC; two or three private task subnets; no public subnet, NAT gateway, internet gateway, egress-only internet gateway, peering, transit-gateway attachment, VPN, customer gateway, load balancer, ECS service, ECS Exec, EFS, EBS, service discovery, or inbound listener; an S3 gateway endpoint; interface endpoints for ECR API, ECR Docker, CloudWatch Logs, Secrets Manager, and KMS; one no-ingress task security group; one endpoint security group; one ECS cluster with the exact Fargate ephemeral-storage CMK; one task definition; broker and verifier functions plus published aliases; four distinct runtime roles plus the bound existing connection-control role; one control bucket; one control KMS key; one HMAC field-token secret in Secrets Manager; two seven-day log groups; one audit-only EventBridge rule/target; and the closed DNS Firewall allow/block lists, rules, group, association, and fail-closed VPC configuration.

The build produces separate broker/verifier ZIPs. The seller places those immutable ZIPs in a versioned, seller-owned, same-region staging bucket before stack creation and supplies the exact bucket, key, version ID, and SHA-256 parameters. The template never downloads a URL or uses an ai.market credential; the verifier hashes the deployed function code/configuration against the manifest. The task image is pulled by digest from the approved cross-account ai.market release ECR repository under its exact repository policy. Seller artifact staging and stack creation are later owner actions, not ai.market runtime mutations and not authorized in this specification-only turn.

The template accepts `VpcIpv4Cidr0` and optional `VpcIpv4Cidr1` through `VpcIpv4Cidr4`. Empty optional values create no association. Every supplied CIDR must be canonical RFC 4632 private IPv4, `/16` through `/28`, non-overlapping, and in the same exact VPC. Optional Amazon-provided IPv6 is recorded but task routes contain no `::/0`; IPv6 cannot create internet egress. Subnet CIDRs must be contained in the declared active VPC CIDRs and non-overlapping. CloudFormation outputs no source key, source name, field name, secret, object key, or raw policy.

Before a runtime can be verified, `verifier.py` must build the seller-local closed `seller_workspace_profile_vpc_inventory.v1`:

```json
{
  "schema_version": "seller_workspace_profile_vpc_inventory.v1",
  "vpc_id": "seller-local-vpc-id",
  "dns_support": true,
  "dns_hostnames": true,
  "ipv4_cidr_associations": [],
  "ipv6_cidr_associations": [],
  "resolver_rule_associations": [],
  "outbound_resolver_endpoints": [],
  "profile_associations": [],
  "pagination_complete": true
}
```

This full inventory never crosses into ai.market. The verifier returns only its count vector, SHA-256, and the fixed safe resolver-control projection.

Inventory is complete only when all of these checks pass:

1. `DescribeVpcs` returns the exact stack VPC with `enableDnsSupport=true` and `enableDnsHostnames=true`; every IPv4 and IPv6 association in `associating|associated|disassociating|disassociated|failing|failed` state is recorded. Only `associated` entries may be used, and any other state fails verification.
2. The sorted active IPv4 set exactly equals the primary plus every non-empty template secondary CIDR. The active IPv6 set exactly equals the template's optional binding. Unknown, missing, duplicate, overlapping, non-canonical, or extra CIDRs fail.
3. `ListResolverRuleAssociations` uses server filter `VPCId=<exact>`, `MaxResults=100`, follows every `NextToken`, permits at most 20 pages/2,000 records, revalidates every returned VPC ID, and calls both `GetResolverRuleAssociation` and `GetResolverRule` for every record. An unconsumed token, repeated token, duplicate ID, omission, limit hit, permission error, or non-`COMPLETE` object fails.
4. Every direct rule must have no `ResolverEndpointId`, `ShareStatus=NOT_SHARED`, `OwnerId="Route 53 Resolver"`, and ARN `arn:${partition}:route53resolver:${region}::autodefined-rule/rslvr-autodefined-rr-*`. `RuleType` is recorded but is never used as the ownership predicate. Any customer-owned, RAM-shared, endpoint-bearing, malformed, cross-partition, or cross-region rule fails.
5. The complete autodefined inventory includes the documented recursive dot rule; private-hosted-zone rules if present; regional EC2 names (`${region}.compute.internal` and `${region}.compute.${partition_dns_suffix}` outside `us-east-1`, or `ec2.internal`, `compute-1.internal`, and `compute-1.amazonaws.com` in `us-east-1`); AWS internal reverse rules (`10.in-addr.arpa`, `16.172.in-addr.arpa` through `31.172.in-addr.arpa`, `168.192.in-addr.arpa`, `254.169.254.169.in-addr.arpa`); localhost rules (`localhost`, `localdomain`, `127.in-addr.arpa`, and both documented all-zero/loopback `ip6.arpa` names); and every AWS-created reverse rule for every active IPv4 CIDR. Completeness is tested seller-side by mapping every active CIDR's first and last address and every intersecting `/24` boundary to at least one returned AWS-owned reverse-rule suffix. Extra AWS-owned autodefined rules are inventoried, not silently discarded. Raw domains/CIDRs stay seller-side.
6. Peering and transit-gateway route/attachment reads prove none. This prevents peer-CIDR autodefined rules from silently widening the expected inventory. If a future architecture needs peering, it requires a new Gate 1 candidate.
7. `ListResolverEndpoints` uses `Direction=OUTBOUND` and `HostVPCId=<exact>`, exhausts pagination, revalidates the VPC/subnets, and requires an empty set. `ListProfileAssociations(ResourceId=<exact VPC ID>, MaxResults=100)` exhausts pagination and requires an empty set whether an SDK renders the resource as ID or ARN.
8. The safe cross-boundary projection is exactly `{non_autodefined_rule_associations:0, endpoint_bearing_rule_associations:0, outbound_endpoints:0, profile_associations:0, active_ipv4_cidr_count, active_ipv6_cidr_count, autodefined_rule_count, pagination_complete:true}` plus `vpc_inventory_hash`. It contains no CIDR, domain, rule/endpoint/Profile ID, owner account, or ARN.

The task security group permits UDP/TCP 53 only to the VPC resolver and TCP 443 only to the interface-endpoint security group plus the regional S3 managed prefix list. The endpoint group permits 443 only from the task group. Route tables have only local VPC routes and the S3 gateway endpoint. The S3 endpoint policy names the exact source bucket/prefix, exact request/result shapes, and `arn:${AWS::Partition}:s3:::prod-${AWS::Region}-starport-layer-bucket/*`; it has no other bucket/resource. DNS Firewall has an exact lower-priority allow rule with `INSPECT_REDIRECTION_DOMAIN` and an exact higher-priority `*`/`BLOCK NODATA` rule, with `FirewallFailOpen=DISABLED`.

## 5. Persistence model and migration

The single additive migration creates the following tables. UUIDs use PostgreSQL UUID, timestamps are timezone-aware, hashes are lowercase 64-character hex unless explicitly `sha256:<hex>`, money is integer USD micros, JSON is JSONB with an octet-length check, and every owner-dependent foreign key contains `seller_id`.

| ORM/table | Required columns and invariants |
| --- | --- |
| `SellerWorkspaceProfileSourceKmsKeySet` / `seller_workspace_profile_source_kms_key_sets` | `id`, `seller_id`, `connection_id`, `version>0`, `encrypted_arns`, `envelope_version`, `key_version`, `arn_count 0..8`, `set_hash`, `aws_account_id`, `region`, `created_by`, `created_at`, `superseded_at`; unique `(seller_id,connection_id,version)`. Adjacent identical sets are a no-op; historical A-B-A hashes may repeat. |
| `SellerWorkspaceProfileRuntimeVerificationNonce` / `seller_workspace_profile_runtime_verification_nonces` | owner/runtime, `nonce_hash`, `status pending|consumed|rejected|expired`, issued/expiry/terminal timestamps, optional receipt hash/outcome; unique `(seller_id,connection_id,runtime_version,nonce_hash)`. Never store nonce plaintext. |
| `SellerWorkspaceProfileRuntimeCostEstimate` / `seller_workspace_profile_runtime_cost_estimates` | owner/source-key/template/network/DNS/Resolver bindings; every standing unit named in Gate 1; `price_table_version`, `estimate_model_version`, `currency='USD'`, low/high micros, receipt hash, disclosed/expiry, `consumed_authorization_id`; immutable and single use. |
| `SellerWorkspaceProfileRuntime` / `seller_workspace_profile_runtimes` | owner, `runtime_version`, `status pending|verified|disabled|drifted`, optimistic `version`, encrypted broker/runtime references, all identity hashes in section 3, standing acknowledgement actor/time/event/hash, token-key version, verified/disabled timestamps; unique owner connection/runtime. |
| `CloudObjectSelector` / `cloud_object_selectors` | owner/runtime, immutable `selector_version`, encrypted ordered object identities, `object_count 1..10`, total declared bytes, version mode, source-key-set hash, selector hash, created/expiry; no plaintext bucket/key/version/ETag outside the encrypted envelope. |
| `SellerWorkspaceProfileCostEstimate` / `seller_workspace_profile_cost_estimates` | owner/runtime/selector and standing receipt bindings; every marginal unit named in Gate 1; low/high USD micros, receipt hash, disclosure/expiry, `consumed_job_id`; immutable and single use. |
| `SellerWorkspaceProfileJob` / `seller_workspace_profile_jobs` | owner/runtime/selector/receipt bindings; state, optimistic `version`, current attempt `0..2`, input hash, quota profile, parser/image/schema versions, phase/absolute deadlines, `cancel_requested_at`, `lease_generation>=0`, `lease_owner_hash`, `lease_token_hash`, `lease_expires_at`, `next_reconcile_at`, aggregate bounded counters, safe failure code, evidence ID, idempotency key/hash, acknowledgement actor/time/event/hash, timestamps. Unique `(seller_id,operation,idempotency_key)`. |
| `SellerWorkspaceProfileAttempt` / `seller_workspace_profile_attempts` | owner/job, attempt `1..2`, deterministic ECS token hash, encrypted task ARN plus ARN hash, AWS state, request checksum, launch/binding/stop timestamps, bounded usage counters, terminal/cleanup reason and timestamps; unique job/attempt and client-token hash; at most one task ARN. |
| `SellerWorkspaceListingEvidence` / `seller_workspace_listing_evidence` | owner/job/attempt, schema versions, canonical semantic JSONB, canonical runtime-attestation JSONB, semantic/attestation/result-integrity hashes, allAI-eligibility projection JSONB, expiry/deletion; each JSONB length checked and immutable; one evidence per successful attempt. |
| `SellerWorkspaceProfileOutbox` / `seller_workspace_profile_outbox` | owner/job, operation `reconcile|cancel|expire|cleanup`, not-before, claim/lease hashes and expiry, attempt count `0..20`, delivered/terminal timestamps; unique `(job_id,operation,job_version)`. Payload contains IDs/hashes only. |
| existing `seller_workspace_audit_events` | Add nullable `profile_job_id` and owner-preserving composite foreign key/index. Existing append-only update/delete/truncate triggers remain active. |

Database checks encode enum membership, terminal timestamps, phase deadline `<= absolute_deadline`, absolute lifetime `<=20 minutes`, attempt maximum 2, payload byte limits, money ceilings, counts, hash forms, ownership, single-use receipts, immutable selectors/evidence/receipts/attempt identity, and one successful evidence row. Partial indexes cover queued/reconcilable jobs, expired leases, active per-connection/per-seller/global counts, evidence expiry, and pending outbox rows.

The migration inserts no rows; updates no W2 record; changes no connection status, active/pending credential, role, ExternalId, listing, order, delivery, `serials`, `legacy_serial`, or `legacy_serial_id`; and creates no AWS resource. Upgrade tests run from the exact `s1648_issue_channel_repair` head over a W2-shaped real PostgreSQL database. Downgrade first takes an advisory lock and refuses if any W3 table contains a row; only an unused schema may be dropped. After any W3 row exists, operational rollback leaves the additive schema inert with flags off.

## 6. API and authorization contract

All paths are under the existing `/api/v1/seller-workspace` router. Every response, including validation and errors, has `Cache-Control: no-store` and `Pragma: no-cache`. Every route requires `require_capability("seller","active")`, master/profile flags, a verified owning connection where applicable, and owner-filtered queries. Foreign and missing IDs produce the same 404 body and timing class. Mutation routes require the existing safe `Idempotency-Key`; state-changing existing-resource routes also require `If-Match: "<positive-version>"`. Unknown request fields are rejected without reflection.

Implement exactly the Gate 1 routes:

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

There is no retry, expiry, raw-result, task, stack mutation, provider debug, allAI dispatch, listing, publication, or delivery endpoint. `GET /objects` permits `limit=1..100`, exact non-root descendant prefixes, and `current|versions`. Its cursor is an authenticated encrypted server token binding seller, connection, prefix, mode, page size, and snapshot expiry; seller B cannot replay seller A's cursor. It returns owner-visible keys only on this owner-only setup route. Those identities are never stored in cache/log/audit/evidence or returned elsewhere.

`PUT source-kms-keys` is the only ai.market route that accepts raw source-key ARNs. It encrypts before commit and returns count, version, and set hash only. Runtime verification carries only the set hash; the seller-local verifier obtains the raw set from its immutable Lambda environment. Estimates expire in 15 minutes and are single-use. Job creation transactionally consumes the exact receipt, reserves quota/concurrency/spend, persists `queued`, and writes an outbox row; it never publishes to Celery inside an uncommitted database transaction.

The only plaintext task ARN in ai.market exists in owner-authorized process memory after decryption for a broker poll/cancel. API responses, exception strings, Celery payloads/results, Redis, traces, metrics, and audit contain only attempt ID and task-ARN hash.

## 7. State machines, leases, idempotency, cancellation, and cleanup

Job states are exactly:

`queued -> starting -> running -> validating_result -> succeeded`

with `queued -> cancelled`, `starting|running|validating_result -> cancel_requested -> cancelled`, and any nonterminal state to `failed|expired`. Terminal states are `succeeded|failed|cancelled|expired`. An illegal transition raises a stable code and appends a redacted deny audit event.

Runtime nonce states are `pending -> consumed|rejected|expired`. Outbox states are derived from nullable timestamps: pending, leased, delivered, terminal. Attempt AWS states are `unbound|start_ambiguous|provisioning|running|stopping|stopped|cleanup_pending|cleaned|failed` and never override the authoritative job state.

Exact timing and lease values:

| Control | Ceiling |
| --- | ---: |
| Queue wait | 5 minutes |
| Broker-accepted task start | 3 minutes |
| Task wall time | 10 minutes |
| Result validation/commit | 2 minutes |
| Absolute job deadline | 20 minutes |
| Physical stop grace | 30 seconds inside the absolute deadline |
| Worker job lease | 60 seconds |
| Lease renewal interval | 20 seconds |
| Outbox lease | 30 seconds |
| Reconciliation cadence | 30 seconds |
| Celery soft/hard limit | 45/55 seconds per delivery; work checkpoints and redelivers |
| Automatic infrastructure retries | 1, therefore at most 2 attempts |

Lease acquisition is one `UPDATE ... WHERE state nonterminal AND (lease_expires_at IS NULL OR lease_expires_at < now()) RETURNING ...` under owner/job version, with a random 256-bit token stored only as SHA-256 plus a monotonically increasing generation. Every mutation supplies generation and token hash. Renewal cannot pass the phase/absolute deadline. A late or dead worker cannot commit after lease loss. Celery is late-acknowledged, rejects on worker loss, prefetches one, and uses metadata IDs/hashes only.

The ECS `clientToken` is the Gate 1 cluster-bound deterministic SHA-256. A crash after request PUT and before `RunTask`, or after AWS accepted `RunTask` and before task-ARN persistence, remains the same attempt in `start_ambiguous`. Redelivery sends a fresh short-lived `reconcile_start` envelope, exact-key verifies the immutable request, and replays identical parameters/token. No new attempt or concurrency reservation is allowed while start is unresolved. Changed body/checksum/media type/KMS key/tags/input/deadline/token parameters fail terminally.

Only launch capacity, transient AWS control-plane, host interruption, or broker transport failure before a valid result commits can create attempt 2. Parser rejection, quota/spend exhaustion, permission denial, schema/hash rejection, runtime drift, raw-output suspicion, or cleanup failure is not automatically retried. Daily/monthly quota and spend count both attempts conservatively.

Cancel is transactional. Queued cancellation wins immediately. For a bound live task it writes `cancel_requested`, commits, and emits a cancel outbox row. The worker asks the broker to validate exact task identity/tags and stop it. A successful evidence transaction wins only if it commits first; otherwise validation observes the terminal/cancel version and becomes a stale no-op. Expiry follows the same rule. At 20:00 no nonterminal row is legal; stop grace is subtracted from running/validation time rather than appended.

Every terminal path, including worker death and task SIGKILL, must observe/stop the exact task, block late commit, delete exact request and result keys, list only the two exact attempt directories with `MaxKeys=2`, prove absence, clear encrypted task-ARN material after it is no longer needed, clear the lease, and retain only allowed evidence/redacted audit. Cleanup retries use the same attempt identity for at most 20 sweeps over 24 hours; the bucket's one-day lifecycle is a backstop, not success proof. Cleanup exhaustion raises an operator-visible safe alert while flags remain off.

## 8. Deterministic formats, isolation, and hard ceilings

All limits are server constants and are repeated in the signed task request/result. Lower estimate/runtime limits may be chosen, never higher.

| Limit | Exact maximum |
| --- | ---: |
| Objects/job | 10 |
| Declared size/object | 100 GiB |
| Source bytes read | 64 MiB/object; 256 MiB/job |
| S3 range request | 8 MiB |
| In-memory range cache | 64 MiB/task |
| Rows parsed | 100,000/object; 250,000/job |
| Columns/fields/leaves | 512/object |
| Emitted field records | 256/job and 88 KiB canonical JSON |
| Non-field result JSON | 32 KiB |
| CSV/JSON scalar | 64 KiB |
| CSV row or JSON record | 1 MiB |
| JSON depth | 32 |
| Parquet footer | 16 MiB |
| Parquet row groups opened | 8/object |
| Decompressed bytes | 128 MiB/object; 512 MiB/job |
| Compression ratio | 100:1 compressed-to-decompressed ceiling |
| Archive members | 0 |
| Archive/container nesting | 0 |
| Result JSON | 131,072 UTF-8 bytes |
| Task allocation | 1 vCPU, 4,096 MiB memory, 20 GiB encrypted ephemeral storage |
| Parser child address space | 3 GiB |
| Parser child CPU | 540 CPU-seconds |
| Parser child wall time | 570 seconds; supervisor kills by task 600 seconds |
| Child processes/open files/file size | 1 child, 64 FDs, 512 MiB temporary-file ceiling |

The task uses `BoundedS3ObjectReader`, which performs exact-version or `If-Match` range GETs and charges every returned byte before exposing it to a parser. It never downloads or persists a whole object. CSV/JSON are streamed; Parquet uses a seekable bounded range adapter with 8-MiB chunks and LRU eviction. Temporary files contain only bounded chunks/pages under one attempt directory and never a complete object. The task checks returned ETag/version, length, encryption, registered KMS key, and selector binding before parsing bytes.

Supported input is only uncompressed CSV/TSV, uncompressed JSON/JSONL, and Parquet. ZIP, TAR, GZIP-wrapped files, XLS/XLSX, databases, images, documents, symlinks, sparse/recursive containers, external page/index references, and encrypted Parquet are rejected. Archive member and nesting limits are therefore exactly zero. Parquet codec allowlist is `UNCOMPRESSED|SNAPPY|GZIP|BROTLI|ZSTD|LZ4_RAW`; all others reject. The decompression byte and 100:1 limits are charged before allocation.

Determinism rules are exact:

- objects use immutable selector order; fields use structural encounter position; ties use unsigned UTF-8 canonical structural-position bytes, never names;
- CSV dialect detection examines the first bounded 64 KiB, tries the fixed delimiter order comma, tab, semicolon, pipe, chooses the highest consistent row-width score, and breaks ties in that order; encoding order is UTF-8, UTF-16LE, UTF-16BE, Latin-1; unknown/ambiguous is recorded without returning bytes;
- CSV headers are classified by a versioned deterministic heuristic, used only inside HMAC token input, then discarded; formulas are never evaluated;
- JSON rejects duplicate keys, comments, NaN/Infinity, unpaired surrogates, depth over 32, oversized scalars/records, and trailing bytes; JSONL order is physical line order, arrays are element order, and object keys are parser encounter order;
- Parquet reads the bounded footer, opens at most the first eight row groups in physical order, uses schema leaf order, ignores value-bearing statistics/key-value metadata/created-by/Arrow metadata/bloom filters in output, and never follows external references;
- type merging uses the fixed lattice `null < boolean < integer < decimal < float < string < binary < date < time < timestamp < list < struct < map < unknown`; incompatible types become `unknown` plus `mixed_physical_types`;
- counts saturate at their ceiling and reconcile; a cap yields a truthful lower-bound/truncated marker only after structurally safe parsing; allocation, footer, depth, record, decompression, or ratio violations fail the object/job;
- PII detection is a versioned deterministic local regex/checksum/shape classifier over bounded values. Matching source substrings never enter findings. No ML, model, network, allAI, prompt, URL fetch, or dynamic code participates;
- the HMAC field-token byte input is exactly Gate 1's domain, NUL separator, format enum, and tagged length-prefixed NFC path components; the raw name/key exists only for that call and is then discarded; and
- RFC 8785 canonical bytes and the Gate 1 `input_hash`, `semantic_hash`, `attestation_hash`, and `result_integrity_hash` projections are test vectors. Job IDs, attempts, clocks, CPU/memory, duration, cost, and region cannot perturb semantic bytes.

The parser child has no shell, `eval`, dynamic import, SQL, DuckDB, macro, UDF, extension, plugin, subprocess command, URL reader, remote filesystem, or inherited credential beyond its exact task role. Filenames, headers, keys, cells, Parquet metadata, Unicode controls, formulas, Markdown/HTML, URLs, tool syntax, and prompt instructions are inert data. Exceptions are caught inside the seller account and mapped to an allowlisted code; raw exception strings are destroyed, never logged.

## 9. Exact value-free schema crossing into ai.market

The broker returns only canonical `seller_workspace_profile_result.v1`, at most 131,072 bytes, media type `application/vnd.aimarket.seller-profile+json`. The top-level fields are exactly `schema_version`, `semantic_evidence`, `semantic_hash`, `runtime_attestation`, `attestation_hash`, and `result_integrity_hash` as defined in Gate 1. Unknown/duplicate keys, non-canonical JSON/numbers, BOM, comments, NaN/Infinity, invalid UTF-8, wrong media/checksum/KMS/tags, or an over-limit counter reject before persistence.

`semantic_evidence` has exactly:

- identity/version fields: `schema_version`, `input_hash`, `selector_hash`, `parser_version`, `evidence_schema_version`, `field_token_key_version`;
- `limits` with the numeric object/read/row/field/record/JSON-depth/decompression ceilings above;
- `observed`: `objects_completed`, `source_bytes_read`, `decompressed_bytes`, `rows_examined`, `truncated`, and enum-only `truncation_reasons`;
- `objects`, maximum 10, each containing only `object_ref=o0001..o0010`, declared source-size integer, `version_binding_kind=version_id|etag_size`, `format=csv|tsv|json|jsonl|parquet`, closed format metadata, row count `{value,accuracy=exact|estimate|lower_bound}`, positional field records, and safe warning enums; and
- `findings` containing sorted unique enum arrays `pii_classes_present`, `quality_flags`, and `warning_codes`.

Each field record contains only `position`, `structural_position`, lowercase HMAC `field_token`, `field_token_key_version`, allowlisted `physical_type`, `nullable_observed`, non-negative reconciling `non_null_count`/`null_count`, `distinct_band`, `length_band`, sorted unique PII class enums with `low|medium|high` confidence band, and sorted unique quality enums. Total records are at most 256/88 KiB.

CSV metadata is exactly encoding enum, delimiter enum, quote enum, header enum, line-ending enum, detected column count, malformed-row count, formula-like boolean, and row-count accuracy. JSON metadata is exactly framing, root type, records observed, max depth, malformed count, heterogeneous boolean. Parquet metadata is exactly version enum, row-group count, row count/accuracy, field count, sorted codec enums, and page/column-index booleans.

`runtime_attestation` is exactly Gate 1's job/attempt/request/provider/execution/region/task-definition/image/allocation/pricing fields and closed usage counters. Every usage counter is a bounded non-negative integer aggregated over at most two attempts. It contains no seller, account, connection, bucket, key, prefix, role, ARN, URL, source timestamp/checksum, DNS name/CIDR, provider response, task stop message, or free text.

The following are forbidden everywhere across the broker boundary: source object/range/body, whole object, filename, bucket/key/version/ETag text, exact field/header/JSON/Parquet name, raw value, sample, value hash, min/max/quantile, regex match, snippet, free-text warning/error, prompt/tool instruction, secret/credential, presigned URL, task ARN/token, raw policy, CIDR/domain/rule/Profile detail, parser stderr/stdout, stack template, and arbitrary metadata. A recursive string scanner rejects a seeded canary or any string outside the exact schema/enum/ID/hash patterns before ai.market commits.

## 10. Deterministic allAI eligibility contract without W3 dispatch

Gate 1 forbids an allAI call in W3. The implementation nevertheless provides the requested hard schema boundary after deterministic scanning: `app/allai/schemas/seller_workspace_profile.py` defines `SellerWorkspaceProfileAllAIInputV1`, and `build_allai_eligible_projection()` in `seller_workspace_profile_contracts.py` constructs it only from already validated `semantic_evidence`. No W3 module imports an allAI agent, router, provider, prompt, service bus, model, or dispatch function; no route/task sends the object. Actual use requires a separately approved later gate.

The closed projection is at most 32,768 canonical bytes and contains exactly:

```json
{
  "schema_version": "seller_workspace_profile_allai_input.v1",
  "evidence_schema_version": "seller_workspace_profile_semantics.v1",
  "semantic_hash": "sha256-hex",
  "summary": {
    "object_count": 0,
    "format_set": [],
    "row_count_band": "0|1_100|101_1000|1001_10000|10001_100000|gt_100000|unknown",
    "field_count_band": "0|1_10|11_50|51_128|gt_128|unknown",
    "pii_classes_present": [],
    "quality_flags": [],
    "warning_codes": [],
    "truncated": false
  },
  "objects": []
}
```

Each allAI `objects` entry has only `object_ref`, `format`, `size_band`, row-count band/accuracy, and at most 128 field summaries containing structural position, physical type, nullability, distinct/length band, PII enum/confidence band, and quality enums. It excludes field tokens, exact counts/sizes, identifiers, names, values, hashes other than semantic hash, timestamps, runtime/cost/provider data, and all free text. Construction order is deterministic selector/structural order; arrays of enums are sorted/deduplicated. Pydantic strict validation, checked-in JSON Schema validation, canonical-size check, forbidden-key scan, canary scan, and injection-fixture scan all run before the projection is eligible. Failure deletes the projection and terminally rejects evidence; it never falls back to a broader model such as existing `DatasetMetadataSummary`, whose `column_names` field makes it prohibited for W3.

## 11. Quotas, concurrency, and provider-spend ceilings

Transactional ceilings are:

- one running job per connection;
- two running jobs per seller;
- four queued jobs per seller;
- twenty running jobs globally;
- twenty accepted jobs per seller per UTC day;
- one hundred accepted jobs per seller per rolling 30 days;
- one infrastructure retry, two total attempts;
- marginal estimate high bound no more than `5,000,000` USD micros ($5.00) per job;
- sum of reserved marginal high bounds no more than `20,000,000` USD micros ($20.00) per seller per UTC day;
- sum no more than `100,000,000` USD micros ($100.00) per seller per rolling 30 days;
- sum no more than `500,000,000` USD micros ($500.00) globally per UTC day; and
- standing estimate high bound no more than `250,000,000` USD micros ($250.00) per runtime per 30-day modeled month.

Only USD price tables are eligible in W3; missing/stale prices or another currency fail closed. These are conservative estimate/reservation ceilings, not claims that ai.market can stop or reproduce the seller's AWS invoice. Seller-side AWS Budgets may add a stricter deny, never a weaker allowance. Pre-existing seller resources/discounts/free tiers/credits are not netted against ceilings.

`app/services/seller_workspace_profile_costs.py` uses one immutable price-table version and integer rational arithmetic with ceiling rounding; floating point is forbidden. It includes every standing and marginal unit enumerated in Gate 1, including endpoints, KMS/Secrets storage and calls, Lambda, S3, Fargate one-minute minimum/per-second billing, DNS Firewall custom domains and queries including redirection follows, EventBridge, log ingestion/storage, image-layer/S3 transfer, interface-endpoint bytes, possible cross-AZ bytes, and both attempts. An undefined unit, stale table, high bound over any ceiling, receipt binding drift, or arithmetic overflow denies authorization/start.

Advisory locks are acquired in fixed order global, seller, connection. The same transaction counts active/queued jobs and unexpired spend reservations, consumes the receipt, and inserts the job/outbox. The broker receives the quota/spend profile and refuses start when its exact immutable values differ. Cache, Celery, or AWS observed counts are never the authority.

## 12. Logs, traces, metrics, and redaction

Backend/task/broker/verifier logs are structured and field-allowlisted. Allowed backend fields are operation enum, safe state/failure code, job/attempt UUID or hashes, resource version, duration/counter numbers, runtime/schema versions, and booleans. Allowed seller-runtime fields are phase enum, object ordinal, numeric counters, truncation/failure enum, and digests. No logger call may interpolate a request/response/provider exception/object/selector/schema field/value.

OpenTelemetry instruments are exactly:

- `seller_workspace_profile_jobs_total{terminal_state,safe_code}`;
- `seller_workspace_profile_phase_duration_seconds{phase,outcome}`;
- `seller_workspace_profile_lease_reclaims_total{reason}`;
- `seller_workspace_profile_cleanup_total{outcome}`;
- `seller_workspace_profile_provider_calls_total{operation,outcome}`;
- `seller_workspace_profile_active_jobs{scope=global}`;
- `seller_workspace_profile_result_rejections_total{reason}`; and
- `seller_workspace_profile_reserved_usd_micros_total{scope=global}`.

No seller/connection/job/attempt/object/task/ARN/account/region/CIDR/domain/source key, error text, or unbounded value is a metric label. Trace span names are fixed operation names; attributes use the same enums/hashes and never bodies. Exceptions are recorded as safe codes without exception message/stack locals on this boundary.

Audit extends the current allowlist with exact IDs/hashes, actor, prior/new state, receipt bindings, versions, decision, and safe code. It never accepts selector plaintext, encrypted/plain credentials, raw ARN arrays, provider results, evidence JSON, allAI projection, raw error, or source-derived strings. Redaction tests seed unique canaries through CSV/JSON/Parquet values, headers/keys, object keys, role/source-key/task ARNs, provider errors, prompt instructions, DNS names, and policies, then scan PostgreSQL non-encrypted fields, Redis/Celery, captured logs/traces/errors/audit/API, result rejection output, and allAI mocks for zero occurrences.

## 13. Focused acceptance matrix

### 13.1 Contracts, ownership, and cache isolation

- flags absent/false, stray profile flag, missing queue/price/runtime, and route presence all remain unavailable or disabled truthfully;
- two synthetic sellers each own a connection/runtime/selector/job/evidence with colliding human-visible metadata; every foreign ID and cursor on verify/list/create/read/cancel/evidence is uniformly absent;
- every Redis rate/idempotency/outbox key includes operation and seller UUID plus connection/job version where applicable; seller A cannot affect or hit seller B's cached response/rate bucket except the intentional global budget;
- no evidence/result/selector cache exists; every API response is no-store; Celery result bodies are disabled/empty for W3 tasks;
- duplicate idempotency same hash replays, changed hash conflicts, stale resource version conflicts, and concurrent requests consume one receipt/create one job;
- W2 initial/rotation verification uses list-only proof with no `GetObject*`, while every inspected W2 test and exact `legacy_serial` derivation remains green.

### 13.2 Runtime/IAM/network

- template/schema lint, deterministic render/digest, all five role separations, exact aliases/revisions/image, task allocation, KMS policies, create-only requests, exact tagged launch, exact task identity, no overrides, and all Gate 1 positive/negative IAM calls;
- zero, one, and eight source keys plus every invalid ninth/alias/wildcard/duplicate/cross-account/region/asymmetric/disabled/policy-broadened case;
- clean one-, two-, and five-IPv4-CIDR VPCs plus optional IPv6 inventory; every CIDR association and AWS autodefined rule is enumerated once, mapped, hashed seller-side, and reduced to the safe projection; truncated/repeated pagination, missing reverse coverage, extra customer/shared/endpoint rule, outbound endpoint, peering/TGW route, or Profile association fails;
- positive DNS/S3/ECR/Logs/Secrets/KMS paths and negative public DNS, high-entropy tunnel label, ai.market, allAI, unapproved redirect, other bucket/key, unrelated ENI, public S3, NAT, and internet destinations; DNS Firewall unavailable fails closed;
- request PUT/read/reconcile, result write/read, `DescribeTasks(include=["TAGS"])`, stop, delete, and absence-list operations match exact keys/checksums/media/KMS/tags; every sibling/wildcard/overwrite/list/body-read/ACL/multipart/copy action denies.

### 13.3 Parsers and hostile data

- golden CSV/TSV/JSON/JSONL/Parquet canonical bytes/hashes repeat across job IDs, attempts, clocks, CPU/memory, and durations;
- empty, BOM/encoding, quoting, multiline, duplicate/missing headers, ragged rows, duplicate JSON keys, heterogeneous records, deep nesting, huge numbers, malformed footer/page, each exact codec, footer/decompression/allocation/ratio bombs, formula/HTML/Markdown/tool syntax/URLs/credentials/PII, and raw exception-copy cases;
- object 11, byte +1, row +1, column 513, archive member 1, nesting 1, compression ratio >100, JSON depth 33, child CPU/memory/wall/open-file/file-size +1, result 131,073, record 257, and field bytes 90,113 each fail/truncate exactly as specified;
- field tokens are stable only within `(seller_id,connection_id,field_token_key_version)` and unlinkable across either seller, connection, or key version;
- no whole object is written; bounded range/cache/temp maxima are observed under crash and cancellation;
- hostile strings including `ignore previous instructions`, fake tool calls, Markdown links/images, XML/JSON prompt wrappers, Unicode bidi/control characters, AWS keys, JWT-like tokens, URLs, SQL/shell, and source strings embedded in exceptions remain inert and absent from every boundary.

### 13.4 Lifecycle, migration, spend, and redaction

- every legal/illegal transition, lease expiry/reclaim, late worker, Celery death, broker ambiguity, both start crash windows, task SIGTERM/SIGKILL, cancel at every phase, timeout at every boundary, stale result, and success-vs-cancel/expiry transaction race;
- exact per-connection/seller/global concurrency, queue, daily/30-day quota, per-job/daily/monthly/global spend boundaries under concurrent PostgreSQL transactions;
- deterministic cost recomputation for every unit, zero-rate unit, two attempts, standing/marginal receipt expiry/replay/drift, and one-micro over-ceiling denial;
- immediate request/result/task/temp cleanup on every terminal path, late-object rejection, bounded cleanup retry/backstop, evidence 30-day expiry, and no whole-object persistence;
- real PostgreSQL upgrade from `s1648_issue_channel_repair`, model/schema equality, W2 row/hash/constraint survival, empty-schema downgrade, nonempty downgrade refusal, and unchanged `serials`/`legacy_serial`/`legacy_serial_id`;
- recursive exact-schema, forbidden-key, raw-string/canary, structured-log, OTel attribute/label, audit, Redis/Celery, API, database, and allAI-mock scans.

## 14. Rollback

Operational rollback is: keep/set `SELLER_WORKSPACE_AWS_PROFILE_ENABLED=false`; reject new estimates/jobs; cancel queued work; stop and reconcile exact live tasks within their existing deadlines; delete and prove absence of request/result objects; clear leases/outbox; retain allowed evidence/audit until normal expiry; roll back backend/control-worker code; and leave additive W3 tables inert. The seller alone decides whether to delete its synthetic/runtime stack. Rollback never changes the verified W2 connection/ExternalId, enables a central parser, imports AIM Data, calls allAI, changes a listing/delivery authority, or touches `legacy_serial`.

## 15. Exact Gate 3 and Gate 4 proof

### Gate 3: reviewed implementation candidate, flags off, no deployment

Gate 3 requires one immutable candidate manifest binding backend commit, this approved Gate 2 commit/digest, migration revision, every changed path, schema digests, Lambda ZIP digests, image digest/SBOM/signature, template digest, price-table/model versions, and synthetic fixture digests. Required checks are:

1. diff proves only the section 2 manifest and no frontend/public/W4/W5/R2/AIM Data/legacy delivery file;
2. all focused tests in section 13 plus the four W2 suites and real-PostgreSQL migration tests pass;
3. `alembic heads` is exactly `s1650_seller_workspace_w3`, upgrade succeeds, unused downgrade succeeds, nonempty downgrade refuses, and ORM/schema comparison passes;
4. runtime dependency/import scan, secret scan, SBOM/vulnerability review, reproducible ZIP/image/schema/template hashes, non-root/read-only/resource-limit tests, and no AIM Data/DuckDB-extension/backend/allAI runtime import;
5. CloudFormation lint, change-set render without execution, IAM simulator fixtures, endpoint/DNS/Resolver/Profile inventory unit tests, and no deployment credentials in CI;
6. static scans prove no source-object body API in ai.market W3 code, no W3 allAI dispatch/import, no raw values/free text in schemas/logs/traces/audit, no whole-object persistence, and all flags false; and
7. fresh independent CC, GLM, and DeepSeek review of the exact implementation manifest/candidate with every mandate folded and the exact resulting candidate re-reviewed. Gate 3 is not deployment authority.

### Gate 4: separately authorized synthetic deployment and live proof

Gate 4 requires explicit later authority before any action and uses only a purpose-created synthetic seller identity/account, two synthetic sellers in ai.market, synthetic source buckets/keys/objects, and an approved bounded test budget. It must independently prove:

1. exact Git ancestry and equality of local/origin/deployed backend commit, profile worker commit, image digest, Lambda packages/aliases, task definition revision, template/change-set/stack digest, schemas, migration head, and flags false;
2. authenticated normal Chrome owner journey for runtime cost disclosure/acknowledgement, template access, verification, object discovery/selector, marginal disclosure/acknowledgement, start/status/cancel/evidence, plus seller-B foreign-ID/cache denial; API/curl/in-app browser is not a substitute for required Chrome proof;
3. seller-account task execution identity, private ENI/no public IP, exact role split, image/task/allocation/Fargate CMK/tags, one- and multi-CIDR complete autodefined inventories, no peering/TGW/outbound resolver/Profile association, DNS Firewall fail-closed, allowlisted traffic, and negative egress/tunneling probes;
4. positive exact request/source-range/result path and every IAM negative call, including connection-control/verifier/broker source `GetObject`, `HeadObject`, unversioned/versioned attributes, cross-object/version/connection, overwrite, result read/delete by task, wildcard list, wrong tags/checksum/media/KMS, ACL/multipart/copy, standalone tag, wrong cluster/task/role/image/network override;
5. deterministic CSV/JSON/Parquet outputs, hostile prompt/data fixtures, all numeric boundary probes, stable semantic hash, valid volatile attestation/integrity hashes, and the schema-validated allAI-eligible projection with zero actual allAI calls;
6. success, parser error, quota/spend, cancel, each timeout, lease/worker death, start ambiguity, retry, task kill, runtime/image/role/network drift, late result, cleanup, and 30-day expiry using time-controlled synthetic tests where real waiting is unnecessary;
7. database/Redis/Celery/log/trace/audit/API/allAI canary scans showing no source/name/value/credential/task/raw error leakage, no whole object, exact object cleanup/absence, task destruction, and bounded retained metadata only;
8. production health and queue readiness without enabling flags, W2 create/verify/rotate/disconnect regression, and unchanged legacy fulfillment/`legacy_serial` constraints; and
9. one immutable redacted receipt referencing every independent proof. Static review, tests, migration, stack identity, IAM, network, cleanup, browser, redaction, and legacy evidence are conjunctive; no merge, deploy label, queue status, provider log, or CloudFormation success substitutes for another.

After Gate 4, the feature still remains off. Enabling or making a public capability claim requires a separate explicit product/operational decision and is not part of W3 implementation acceptance.

## 16. Implementation source pins

Gate 1's source references remain binding. The multi-CIDR inventory and exact implementation checks additionally pin these AWS primary sources, which must be re-read if the implementation base changes:

- Route 53 Resolver autodefined system rules and per-VPC-CIDR reverse rules: <https://docs.aws.amazon.com/Route53/latest/DeveloperGuide/resolver-overview-forward-vpc-to-network-autodefined-rules.html>;
- Resolver rule/association filtering and pagination: <https://docs.aws.amazon.com/Route53/latest/APIReference/API_route53resolver_ListResolverRuleAssociations.html>;
- Route 53 Profile association list contract: <https://docs.aws.amazon.com/Route53/latest/APIReference/API_route53profiles_ListProfileAssociations.html>;
- Route 53 Resolver and Profiles IAM action/resource semantics: <https://docs.aws.amazon.com/service-authorization/latest/reference/list_route53resolver.html> and <https://docs.aws.amazon.com/service-authorization/latest/reference/list_route53profiles.html>; and
- ECS cluster-managed Fargate ephemeral-storage KMS binding: <https://docs.aws.amazon.com/AWSCloudFormation/latest/TemplateReference/aws-properties-ecs-cluster-managedstorageconfiguration.html>.

## 17. Known risks and hard stops

- AWS may change service-owned Resolver inventory or pricing. Any unknown owner/namespace, incomplete inventory, pagination anomaly, price-table staleness, or non-recomputable unit fails closed and requires a reviewed update; it is never silently allowed.
- Seller-account control reduces ai.market custody but is not remote attestation against a malicious seller. Evidence proves the approved code/path identity observed, not truth of seller-controlled data or infrastructure.
- Fargate/Lambda/S3 control outcomes can be ambiguous. Deterministic request keys, ECS tokens, leases, and exact reconciliation prevent duplicate launch; ambiguity is not converted to success or a denial.
- PyArrow/parser vulnerabilities are high-impact inside the seller task. Exact dependency locks, sandbox/resource limits, hostile fixtures, image signing, and no egress are Gate 3/4 requirements.
- Estimated AWS spend is bounded by admission assumptions, not an invoice guarantee. Any high estimate over the numeric ceilings is refused; AWS Budgets is optional defense in depth.
- Existing `app/allai/schemas/metadata_summary.py::DatasetMetadataSummary` exposes column names and is prohibited for W3. Only the closed dormant projection in section 10 is eligible, and W3 dispatch remains forbidden.

No implementation task may be created, claimed, queued, or dispatched until the exact Gate 2 candidate has independent CC, GLM, and DeepSeek approval with zero unresolved mandates. This sentence is a hard authorization boundary, not a scheduling preference.
