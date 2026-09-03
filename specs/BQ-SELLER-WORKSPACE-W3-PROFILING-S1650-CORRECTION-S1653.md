# BQ Seller Workspace W3 profiling — S1653 safety correction

**Status:** `AUTHOR-ONLY/PENDING-REVIEW`. This additive correction is not approval or implementation authority. It was authorized by Max in session `S1653`, Event Ledger `0aef6fad-17c0-4be9-9780-9b997bff34ac`, after failed live proof event `7a303ae4-e374-4e5d-b6a1-eea59f6bd5e8`.

**Binding bases:** approved Gate 1 `d65c11cbf1bccb8f5a98cb07b0f69983bdfe7b4b` and approved Gate 2 `ef91b83ac55d1859c88c528425cdb461046c544b:specs/BQ-SELLER-WORKSPACE-W3-PROFILING-S1650-GATE2.md`. Those files remain unchanged. Exact read-only product candidate: `4adc36fe4b74a666ac5cede859619d95bc5eb4ee` (deployed merge `267f68fd7582453d95f504bc612d18570852e287`).

**Scope:** exactly two incident corrections: observable fail-closed AWS network-isolation evidence and a genuine W3 worker-liveness publisher/read path. Every Gate 1/Gate 2 requirement not explicitly superseded below remains binding.

## 1. Ground truth and governing decision

The authoritative S1653 bundle is `/var/tmp/koskadeux/s1653-w3-live-preflight.NVvjQX/FINDINGS.md` plus its JSON receipts. On the disposable two-CIDR VPC, two complete `ListResolverRuleAssociations` paginations returned only the AWS internet-resolver association; the unchanged candidate failed `required_reverse_rule_missing` twice. This disproves the design assumption that this API inventory exposes the implicit CIDR reverse rules. It does not prove those implicit rules are absent.

The additional raw enabled-state observation `resolver-config-enabled.json` returned, for the exact VPC, `OwnerId=948749907373`, the exact `ResourceId`, and `AutodefinedReverse=ENABLED`, while the association inventory still contained only the internet resolver. AWS documents `GetResolverConfig(ResourceId=vpc)` as the VPC Resolver behavior read, and `ENABLED` as the completed state in which autodefined reverse-lookup rules are enabled. AWS separately documents that adding an IPv4 VPC CIDR creates an autodefined reverse rule. Ground truth still outranks documentation: this correction does not claim those implicit rules are listable.

The same bundle proves `SELLER_WORKSPACE_PROFILE_WORKER_HEARTBEAT_AT` is only environment input, has no writer, expires without refresh, and accepts a timestamp one day in the future. It is configuration, not liveness.

This is Tier 3 because it changes a fail-closed security envelope after a failed proof. Only this delta requires fresh unanimous independent security review; the author/builder is excluded, no previous vote carries, and no review is dispatched by this document.

## 2. Correction A — Resolver evidence

### 2.1 Clauses superseded, narrowly

Gate 2 §3.1 currently requires the two literal CIDR reverse domains to appear in the complete `ListResolverRuleAssociations`/`GetResolverRule` inventory and fails `required_reverse_rule_missing` otherwise. It also fixes a five-key `resolver_control_hash` and says, “No sixth or seventh key is permitted.” Gate 2 §§6, 12, and 13 prohibit verifier calls/actions outside the then-approved Gate 1 §6.3 set; §7.1 says the standing receipt includes no unit for an API removed by that correction.

Those clauses are superseded only as follows:

1. Remove the two-domain membership requirement and `required_reverse_rule_missing` behavior. Do not synthesize, infer, or hash implicit association/rule rows.
2. Transparently restore only `route53resolver:GetResolverConfig`, which round 3 at `397dd312b11ddb5d6063743048ba014c23fe880a` explicitly removed. The removed EC2 peering/TGW reads and every other prohibited call remain removed.
3. Add exactly one sixth stable resolver projection key, `autodefined_reverse_enabled: true`. No seventh key or raw configuration field is permitted.
4. Charge the existing standing `resolver_configuration_reads` unit for one added call per verifier invocation: with the existing ceiling of 100 verifier invocations, change `4,000` to `4,100`. The configuration-read rate and USD 125 standing cap do not change; the estimate-model version and receipt hash must change and the cap must be recomputed before acceptance.

### 2.2 Exact replacement predicate

For the exact stack VPC, the seller-account verifier must:

1. retain exact `DescribeVpcs` proof of only associated `10.203.0.0/24` and `10.203.1.0/24`, no IPv6/third/partial/transitional CIDR, and exact `enableDnsSupport=true` plus `enableDnsHostnames=true`;
2. call `GetResolverConfig` exactly once with `ResourceId=<exact VPC ID>` and require one `ResolverConfig` mapping whose `Id` matches `^rslvr-rc-[A-Za-z0-9-]{1,54}$`, `ResourceId` equals that VPC byte-for-byte, `OwnerId` equals the verified 12-digit seller AWS account, and `AutodefinedReverse` equals the exact terminal value `ENABLED`;
3. reject missing/denied/error responses, unknown or extra shapes, malformed identifiers, wrong resource or owner, and `ENABLING`, `DISABLING`, `DISABLED`, `UPDATING_TO_USE_LOCAL_RESOURCE_SETTING`, `USE_LOCAL_RESOURCE_SETTING`, null, or any unknown state;
4. retain complete bounded pagination of caller-observable rule associations. Every returned association/rule must still be exact-VPC, `COMPLETE`, endpoint-free, `NOT_SHARED`, and AWS service-owned by `OwnerId="Route 53 Resolver"` plus the exact partition/region autodefined-rule ARN namespace. Seller-created, RAM-shared, endpoint-bearing, foreign, duplicate, malformed, nonterminal, truncated, or over-bound results fail closed. An inventory containing only the valid internet-resolver association is eligible if every other predicate passes;
5. retain zero outbound Resolver endpoints, zero Route 53 Profile associations, the exact DNS Firewall allow/block/redirection association with `FirewallFailOpen=DISABLED`, PHZ treatment, exact subnet/routes/security-group/S3 and interface-endpoint restrictions, TLS/resource identity, and every existing no-egress/prohibited-resource check.

The canonical `resolver_control_hash` preimage becomes exactly:

```json
{"autodefined_reverse_enabled":true,"endpoint_bearing_rule_associations":0,"non_autodefined_rule_associations":0,"outbound_endpoints":0,"pagination_complete":true,"profile_associations":0}
```

Its lowercase SHA-256 is `e1fdef33a6130cf08b66d6e65d70a39118e4c47bea0a75f0a8dfb0d438fccd93`.

The verifier receipt exposes only that hash, not ResolverConfig IDs, account/VPC IDs, rule names/domains, CIDRs, or raw AWS responses. The backend expected hash and seller verifier observed hash must both use this six-key projection. Every pre-correction five-key runtime verification is stale and cannot authorize a launch; re-verification creates the new binding rather than rewriting an old receipt.

This replacement is sufficient for the same isolation purpose: `AutodefinedReverse=ENABLED` is the observable VPC control for completed implicit reverse-rule enablement, while complete caller-configurable forwarding associations, outbound endpoints, Profiles, DNS Firewall, and network egress remain independently fail-closed. It proves the control state, not the existence or completeness of hidden rule rows. No new forwarding path is accepted.

## 3. Correction B — genuine W3 worker liveness

### 3.1 Remove static timestamp readiness

Delete `profile_worker_heartbeat_at` and all reads of `SELLER_WORKSPACE_PROFILE_WORKER_HEARTBEAT_AT`. No environment timestamp, future timestamp, deployment-time stamp, generic `celery:heartbeat:worker:*` key, process existence, queue declaration, or Railway “running” state may satisfy W3 readiness.

Use the existing Redis, Celery Beat schedule, dedicated queue, PostgreSQL leases, and one-replica `railway.profile-worker.json`. Add no scheduler, service, table, migration, registry, protocol, background thread, or new queue.

### 3.2 One expiring record

The exact Redis key is:

```text
seller-workspace-profile:liveness:v1:<RAILWAY_ENVIRONMENT_ID>:<RAILWAY_SERVICE_ID>:<RAILWAY_DEPLOYMENT_ID>
```

Its canonical closed JSON value contains only `schema_version=seller_workspace_profile_worker_liveness.v1`, `environment_id`, `service_id`, `deployment_id`, `git_commit_sha`, `replica_id`, `cycle_completed_at`, `progress_at`, and integer `active_poll_count`. It contains no seller, connection, job, task, source, ARN, receipt, or error data. Write it atomically with expiry exactly 90 seconds.

The worker takes identity only from Railway-provided `RAILWAY_ENVIRONMENT_ID`, `RAILWAY_SERVICE_ID`, `RAILWAY_DEPLOYMENT_ID`, `RAILWAY_GIT_COMMIT_SHA`, and `RAILWAY_REPLICA_ID`; any missing/malformed value suppresses the write. The web reader uses non-secret Railway reference values `SELLER_WORKSPACE_PROFILE_WORKER_SERVICE_ID`, `SELLER_WORKSPACE_PROFILE_WORKER_DEPLOYMENT_ID`, and `SELLER_WORKSPACE_PROFILE_WORKER_GIT_COMMIT_SHA`, plus its own exact `RAILWAY_ENVIRONMENT_ID`, to construct and validate the expected key. Missing or mismatched identity is unready. No image digest is added to this record: the control worker uses the canonical backend Dockerfile/source commit, and exact deployed image identity remains separate mandatory Gate 4 evidence rather than a second liveness authority.

### 3.3 Producer and polling-loop coupling

`seller_workspace_profile.reconcile` keeps its existing 20-second Beat cadence and publishes only after its real non-cleanup `_sweep(cleanup=False)` completes successfully. Each `run_job` loop also publishes only after a real `advance_job` step commits, before its existing 20-second sleep. `expire_cleanup` never publishes.

Before either writer sets the record, it reads one PostgreSQL snapshot of every job in `starting|running|validating_result|cancel_requested`. `active_poll_count` is that count. With no active job, `progress_at=cycle_completed_at=<database UTC now>`. Otherwise, `progress_at` is the oldest non-null committed `lease_last_renewed_at` across all active jobs. A null, future, or stale sibling value is retained as an unhealthy/invalid watermark or suppresses the write; another healthy job or reconciliation sweep can therefore never mask a stuck polling loop. `cycle_completed_at` is the database completion time, not caller input.

The existing Celery prefork/process model remains unchanged: synchronous task wrappers continue to enter the existing async work with `asyncio.run`; publication runs in that same task child after the committed async step/sweep. No liveness thread runs beside a blocked provider call. At four occupied worker slots, the job loops themselves publish; when idle, the existing reconciliation task publishes.

At process start the new deployment key is absent and W3 is unready until one real cycle completes. Worker/Beat/broker death, a stuck DB/provider/poll loop, or Redis/DB loss produces no successful refresh; the last record expires. Publication failure does not alter provider/job state or fabricate success. Restart/rollout changes the deployment-scoped key, so an old deployment cannot satisfy the new expected identity.

### 3.4 Existing availability gates read it

The async FastAPI `get_seller_workspace_config` dependency loads environment flags first. When the master/connect/profile flags are not all explicitly true, it performs no W3 Redis read, so ordinary W2 and profile-off paths are unchanged. When all three are true, it reads the exact key and Redis TTL and hydrates a boolean worker-ready result; Redis absence/error is unready, not an exception that disables W2.

The record is ready only when its closed schema and identities match, `0 < TTL <= 90`, `0 <= now-cycle_completed_at <= 90`, `0 <= now-progress_at <= 90`, and `0 <= active_poll_count <= 20`. Any future timestamp, naive/non-UTC time, unknown field, malformed JSON/value, wrong deployment/source/service/environment, missing expiry, or age over 90 seconds is unready.

`capability_payload` and `require_aws_profile` remain synchronous pure checks over the hydrated config; profile route/service construction continues to use the same request-scoped dependency. W3 Celery tasks do not require their own liveness record to repair/clean in-flight work. Master/connect/profile flags, principal/KMS, current price table/model, exact artifacts, and verified connection/runtime remain conjunctive requirements.

## 4. Exact later implementation paths

No new implementation path is authorized. A later reviewed correction changes only these existing Gate 2 manifest paths:

- Resolver: `app/services/seller_workspace_profile_aws.py`, `infra/seller_workspace_profile/verifier/handler.py`, `infra/seller_workspace_profile/template.yaml`, `app/services/seller_workspace_profile.py`, `tests/test_s1650_profile_aws.py`, and `tests/test_s1650_profile_iac.py`.
- Liveness: `app/core/seller_workspace_config.py`, `app/api/v1/endpoints/seller_workspace.py`, `app/tasks/seller_workspace_profile.py`, `tests/test_s1650_profile_contracts.py`, `tests/test_s1650_profile_lifecycle.py`, and `tests/test_s1650_profile_observability.py`.

`app/core/celery_app.py`, `railway.profile-worker.json`, all models/migrations/locks/runtime parser files, `requirements*`, W2 b1/b2a/b2b/PostgreSQL tests, shared `railway.worker.json`, delivery/serial/`legacy_serial`, AIM Data, W4/W5/R2, frontend, allAI, and publication remain unchanged. This author cycle changes no credential, deployment configuration, or feature-flag value; the three non-secret identity references above are later reviewed activation bindings. The implementation candidate must still match the approved 55-path manifest; this delta adds no 56th path.

## 5. Objective acceptance and negative controls

1. Static action/call/IaC closure differs by exactly `route53resolver:GetResolverConfig`; the old prohibited-set entry is removed, all mutation denies remain, and no other action appears.
2. Unit fixtures accept the observed two-CIDR, DNS-enabled, internet-resolver-only association inventory only with exact-owner/resource `AutodefinedReverse=ENABLED`. Every transitional/disabled/unknown/missing/malformed/wrong-owner/wrong-resource response fails before a receipt.
3. Existing association, outbound-endpoint, Profile, PHZ, Firewall, egress, pagination, duplicate, ownership, status, and wrong-namespace negative controls remain green. Tests prove no implicit reverse-rule row is fabricated.
4. Golden tests pin the exact six-key preimage/hash; an old five-key expected hash fails. Standing receipts pin `resolver_configuration_reads=4,100`, a new estimate-model version, recomputed receipt hashes/ranges, and the unchanged USD cap.
5. Before security review, the evidence package must bind fresh disposable two-CIDR live receipts for both terminal `ENABLED` acceptance and `DISABLED` rejection, exact request/response ownership, candidate source digests, full pagination, and cleanup. The current enabled receipt is supporting evidence; no disabled-state or correction-code live receipt is claimed here.
6. Liveness tests prove: no/startup/expired record is unready; a real idle reconciliation cycle becomes ready; each committed run-job step refreshes; cleanup/generic heartbeat/static env cannot refresh; 90 seconds is accepted and greater than 90 rejected; every future, malformed, wrong-identity/source/deployment, missing-TTL, or over-TTL value is rejected.
7. A hostile two-job test holds one poll/provider step so its committed lease watermark ages past 90 seconds while the sibling and reconciliation cycle continue. The single record remains unready. Worker kill, Beat/broker interruption, DB loss, and Redis loss also become unready within 90 seconds without changing a job outcome.
8. With profile off, W2 makes no new Redis liveness read and all frozen W2 tests/behavior remain unchanged. With profile on, valid liveness alone is insufficient: each other Gate 1/Gate 2 dependency and exact runtime binding is still required.
9. The focused Gate 2 backend, IaC, W2 safety, no-allAI/no-parser-import, redaction/canary, default-off, concurrency/rate/spend, and full Gate 3/Gate 4 proof requirements remain mandatory.

## 6. Rollback and residual proof boundary

Rollback starts by keeping/turning the profile flag off. Stop admission, reconcile existing exact tasks and cleanup, then roll back the web/control-worker/verifier code together. New deployment-scoped Redis keys expire without deletion. Do not rewrite runtime receipts: hashes from the rolled-back projection are ineligible until matching re-verification. Seller stacks, W2 connection/ExternalId state, schema, seller data, and all no-egress resources remain untouched.

Unproven here: correction code, tests, reviews, disabled Resolver live proof, final AWS semantics beyond the cited fixture, deployment identity, worker liveness under a deployed workload, normal-Chrome evidence, customer behavior, and Gate 3/Gate 4 completion. Production remains off and synthetic-only. No customer credential/data access, cloud mutation, implementation dispatch, merge, or deployment is authorized by this file.

## 7. Primary references

- AWS `GetResolverConfig`: <https://docs.aws.amazon.com/Route53/latest/APIReference/API_route53resolver_GetResolverConfig.html>
- AWS `ResolverConfig` states and ownership fields: <https://docs.aws.amazon.com/Route53/latest/APIReference/API_route53resolver_ResolverConfig.html>
- AWS autodefined VPC Resolver rules: <https://docs.aws.amazon.com/Route53/latest/DeveloperGuide/resolver-overview-forward-vpc-to-network-autodefined-rules.html>
- Railway deployment identity variables: <https://docs.railway.com/variables/reference>
