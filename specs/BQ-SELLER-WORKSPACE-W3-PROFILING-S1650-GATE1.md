# BQ-SELLER-WORKSPACE-W3-PROFILING-S1650 Gate 1 architecture specification

**Status:** Gate 1 candidate. Build remains blocked until the two Max decisions in section 18 are recorded and the required Gate 1 review approves the resulting exact digest.

**Build Queue entity:** `build:bq-seller-workspace-w3-profiling-s1650`

**Expected branch:** `spec/bq-seller-workspace-w3-profiling-s1650`

**Scope:** W3 AWS profiling architecture only. This document authorizes no product code, deployment, provider mutation, customer-data access, public enablement, AIM Data runtime import, W4, W5, R2, publication, sample generation, or delivery work.

## 1. Pinned evidence and governing conflict

This candidate was authored against:

- runbooks `19e3cb87e0c4263b4d1a1b78a920e6165c56d1d6`, including `seller-workspace-cloud-listing-delivery.md` SHA-256 `2ac591901c70a0612c17dc62578a01047f78f75039beba75137fc9faa99f5823`;
- ai-market backend `50fdb680a5b89265a7e668223bfa1b8728c6c4e9`;
- canonical `docs/core/CORE.md` version 9.15, SHA-256 `385042239afac7c54cadefca6be2107e67cb3da2c442be63fdb9fd6b0bdc11e5`;
- AIM Data `f5e92c80a93c159989340d7c45018e2dcea55f53`, inspected only to identify reusable algorithms, unsafe runtime assumptions, and the exclusion boundary.

Round-1 review was performed on candidate `78a2b8e3e317d69207ec092b5156c6e63c831509`, file SHA-256 `e71fa0cea113dcf366152f25838576c668234085ada9b9055691cc448cd901d7`. This revision folds the complete CC response `/Users/max/council/cc/response-20260902-015302-385335.md` and GLM response `/Users/max/council/glm/response-20260902-015303-186203.md`. It does not resolve D1 or D2, authorize implementation, or reuse either verdict for this new digest.

CORE 9.15 says both that ai.market is metadata-only/non-custodial and that raw customer data must not touch ai.market. The W1 runbook instead describes a backend-deployed isolated worker reading bounded source ranges. Isolation and bounded reads reduce exposure but do not change custody: raw bytes would enter an ai.market process. W3 therefore replaces that W1 execution placement with seller-account execution. It does not change the W2 connection lifecycle, W1 product outcome, or any delivery authority.

The relevant backend baseline has:

- one backend-owned capability response with every later stage hard-coded `not_implemented` and every flag default-off;
- W2 connection, encrypted ExternalId, audit, and `DeliveryAuthority` schema foundations only;
- no selector, profile job, evidence, profile route, profile queue, or profile task;
- a W2 verification session policy containing `s3:GetObject` because the implementation calls `HeadObject`, even though it never reads a body;
- shared Celery workers and queues only; there is no Seller Workspace profile-control queue or deployment.

The AIM Data baseline is deliberately unsuitable as a W3 runtime. It is a customer-installed, single-install product with local filesystem/database state and a broad processing service. Its S3 registration path downloads an object into `record.upload_path`; its DuckDB profiling can emit names, minimums, maximums, and sample values. Those facts are evidence for exclusion, not a request to change AIM Data.

## 2. Binding outcome

W3 uses one seller-deployed AWS broker Lambda to launch one seller-account ECS Fargate task per profile attempt. The task reads the selected S3 objects inside the seller account, writes one bounded metadata result into a dedicated seller-owned control bucket, and exits. The broker validates and returns that result to ai.market. No source object body, raw range, row, cell, field name, JSON key, Parquet field name, sample, minimum, maximum, provider credential, presigned URL, or parser stderr may enter ai.market.

ai.market is only the authenticated control plane. It stores the immutable selector, job state, bounded evidence, and redacted audit. It never has an S3 data-read method for the W3 source. W3 invokes the seller broker and polls it; it does not run a parser in the web process, Celery child, Railway container, allAI process, AIM Data process, or any other ai.market-controlled compute.

W3 ends at normalized deterministic evidence. It makes no allAI call and creates no listing draft, public sample, listing, delivery authority, order behavior, or buyer grant. W4 may consume W3 evidence only after its own approved specification.

## 3. Candidate comparison

| Candidate | Raw-byte location | Runtime/custody result | Decision |
| --- | --- | --- | --- |
| Seller-account AWS-native ephemeral execution | S3 and one ephemeral Fargate task in the seller-controlled AWS account | Satisfies the CORE boundary when the split roles, private network, fixed image, bounded result schema, and evidence below are all proved | **Selected** |
| AIM Data runtime path | Customer AIM Data Docker/local filesystem/database | Non-custodial, but it requires an installed product, installation identity, local state, broad processing runtime, and live-flow assumptions that W1 explicitly excludes | **Excluded**; algorithms or fixtures may be ported with provenance, but no package, service, container, database, endpoint, install token, serial, broker client, or runtime import may be used |
| Central ai.market sampling | Raw ranges enter an ai.market backend/worker before parsing | Violates CORE even if reads are bounded, encrypted, immediately deleted, or run in an isolated queue | **Prohibited**; no fallback, diagnostic, retry, support path, or feature flag may enable it |

AWS Lambda alone is not selected for parsing because its fixed execution envelope would make larger bounded CSV/JSON/Parquet work a format-dependent exception. AWS Batch, Step Functions, EKS, and a long-lived ECS service add schedulers or persistent compute that this one-task lifecycle does not need. One broker Lambda plus standalone Fargate tasks is the smallest AWS-native separation that prevents the ai.market principal from receiving source-read permission.

## 4. Trust model

### 4.1 Actors and assumptions

| Actor | Trusted for | Not trusted or not authorized for |
| --- | --- | --- |
| Authenticated active seller | Choosing a verified connection, immutable selector, and explicit profile start/cancel action | Acting for another seller; changing a running job; enabling W4/W5/R2 |
| ai.market web/API | Seller authentication, ownership checks, immutable job records, flags, quotas, and redacted audit | Reading source bytes, executing parsers, changing the seller stack, or treating route presence as availability |
| ai.market profile-control worker | Invoking/polling/cancelling the exact broker alias with an immutable envelope | S3, ECS, IAM, KMS, Secrets Manager, raw task output, free-form overrides, or source access |
| Seller broker Lambda | Validating the envelope, launching/stopping the fixed task, reading and validating the bounded result, and deleting control artifacts | Reading source objects, widening selectors, returning raw values, or accepting a mutable task definition |
| Seller Fargate profile task | Reading only the verified connection prefix, parsing locally, and writing one evidence object | Calling ai.market/allAI, public egress, assuming another role, changing AWS infrastructure, publishing, or delivery |
| allAI | Nothing in W3 | Credentials, broker access, source content, W3 task invocation, or publication authority |
| Support/operator | Redacted status and evidence references for an explicit purpose | Credentials, source data, exact field names, result objects, or implicit administrator bypass |

The signed, digest-pinned ai.market image and broker package are trusted code for the duration of one approved runtime version. The seller controls the AWS account, roles, network, KMS keys, logs, and ability to remove the stack. A compromised seller account can falsify its own metadata; W3 does not claim remote attestation. ai.market validates provenance and consistency but does not claim the evidence proves the truth of hostile seller-controlled data or infrastructure.

### 4.2 Non-custody invariant

The invariant is conjunctive:

1. only the task role can read source object bodies;
2. that role is trusted only by `ecs-tasks.amazonaws.com`, never by the ai.market principal or broker role;
3. the task has no public IP, NAT route, internet gateway route, ai.market callback, or arbitrary network egress;
4. its only control-bucket read is the broker-created, checksum-bound request for its exact connection/job/attempt, and its only data write is that attempt's exact result key;
5. the result schema excludes source-derived strings and raw values and is capped at 131,072 UTF-8 bytes;
6. the broker rejects before returning any result whose length, checksum, media type, schema, field allowlist, counters, or provenance do not match;
7. ai.market has only the exact broker invocation plus prefix-bounded S3 list permission needed for W2 discovery, and has no source object-read, ECS, IAM, KMS, or Secrets Manager permission.

Failure of any conjunct makes AWS profiling unavailable. There is no central-read fallback.

## 5. Seller-account AWS topology

The later W3 implementation supplies a versioned CloudFormation template for the seller to inspect and deploy. One stack/runtime is bound one-to-one to one `CloudConnection`; roles and source-prefix permissions are not shared across connections. W3 product code may verify the stack but may not create, update, or delete it. The seller passes the already pinned connection-role name and explicitly removes its old object-read policy as part of the upgrade. The stack contains exactly:

- one broker Lambda function and immutable published alias;
- one ECS cluster for standalone Fargate tasks, Linux platform `1.4.0` or later;
- one task definition pinned to an immutable image digest, fixed entrypoint, `1 vCPU`, `4 GiB` memory, `20 GiB` ephemeral storage, read-only root filesystem, non-root user, no privileged mode, no added Linux capabilities, and `stopTimeout=30` seconds;
- distinct broker, task, and task-execution IAM roles plus a template parameter that binds the existing cross-account connection-control role;
- one seller-owned control bucket with separate `requests/` and `results/` prefixes, public access blocked, TLS required, SSE-KMS, versioning disabled, replication disabled, backup excluded, incomplete multipart uploads aborted after one day, and object expiry after one day. Before launch the broker writes one canonical request object with `If-None-Match: *`, checksum, JSON media type, SSE-KMS key ID, and connection/job/attempt/runtime tags. An existing key or metadata mismatch fails closed; neither broker nor task may replace it;
- one customer-managed KMS key for the control bucket and Fargate ephemeral storage, with grants limited by the stack resources;
- private subnets, a no-ingress task security group, and only the endpoints needed to launch and run the task. The S3 gateway endpoint policy is an explicit allowlist for: the verified source bucket and objects under its exact connection prefix; the control bucket and only `requests/<connection-id>/.../request.json` plus `results/<connection-id>/.../evidence.json`; and the mandatory regional ECR layer bucket `arn:${Partition}:s3:::prod-${Region}-starport-layer-bucket` plus its objects, read-only. Source/control bucket resources are additionally restricted to the verified seller account. ECR API, ECR Docker, CloudWatch Logs, Secrets Manager, and required KMS use private interface endpoints;
- no public IP, NAT gateway, internet gateway route, load balancer, inbound listener, ECS Exec, service discovery, EFS, EBS, shell endpoint, or long-lived ECS service;
- one metadata-only CloudWatch log group with seven-day retention and one EventBridge rule for task-state events; and
- one seller-owned HMAC key in Secrets Manager used only inside the task to create stable, non-reversible field tokens. The key value never leaves the seller account.

The image is pulled from the approved ai.market release ECR repository under a cross-account repository policy and by digest. A mutable tag is never an execution identity. The broker refuses a task definition revision whose image digest, task role, execution role, CPU, memory, storage, command, network mode, logging configuration, or read-only settings differ from the verified runtime record.

The request object, not a container command or selector-valued environment variable, is the immutable task input. `RunTask` may supply exactly two broker-derived bootstrap environment values: `W3_REQUEST_KEY` (the canonical key constructed from the validated connection/job/attempt) and `W3_REQUEST_SHA256` (the checksum of the create-only request object). The broker never copies an ai.market-provided override map and rejects every other container, command, environment, role, image, resource, or network override. The fixed entrypoint retrieves only that key, verifies checksum, media type, KMS key, tags, schema, input hash, selector scope, expiry, and its broker-set ECS task tags before reading source data. The request contains the validated envelope and selector; it is not an audit-only artifact. A mismatch stops before any source read or result write.

The endpoint policy has no wildcard seller-bucket resource and no catch-all S3 statement. Its implicit deny is verified for every other source prefix, control key, seller bucket, regional/non-regional ECR layer bucket, S3 access point, and public S3 endpoint. Removing the regional ECR layer-bucket entry must make a private digest pull fail, while the complete allowlist must permit the exact digest pull without NAT or an internet-gateway route.

AWS documents the underlying primitives used here: Fargate tasks use `awsvpc` task ENIs; task roles and task-execution roles are distinct; platform 1.4.0 provides encrypted ephemeral storage and supports a customer-managed KMS key; and task state changes expose the image digest. These are platform facts, not completion evidence. W3 must still prove the exact deployed stack.

## 6. Least-privilege permissions

No role may combine two rows below.

### 6.1 Cross-account connection-control role

For a W3-ready connection this is the existing immutable `CloudConnection.role_arn`, still trusted only for the configured ai.market AWS principal with the existing random per-connection ExternalId. The seller replaces its permissions during the explicit profile-runtime upgrade; the role ARN and ExternalId do not silently change. Its permission policy contains only:

- `lambda:InvokeFunction` on the exact published broker alias ARN;
- `s3:ListBucket` on the exact source bucket with the exact non-root connection prefix; and
- `s3:ListBucketVersions` on the same bucket/prefix only when versioned selector discovery is enabled.

It has no object-ARN permission, including `s3:GetObject`, `s3:GetObjectVersion`, `s3:GetObjectAttributes`, `s3:GetObjectVersionAttributes`, or any range-read equivalent; no `ecs:*`, `iam:*`, `kms:*`, `secretsmanager:*`, `logs:*`, second `sts:AssumeRole`, wildcard resource, or unqualified Lambda-version permission. The ai.market session duration is at most 900 seconds. W2 verification and object discovery use bounded `ListObjectsV2`/`ListObjectVersions` results only and call neither `HeadObject` nor `GetObjectAttributes`. `HeadObject` requires `s3:GetObject`, or `s3:GetObjectVersion` for a specified version; the attributes API has separate `s3:GetObjectAttributes` and version-specific `s3:GetObjectVersionAttributes` permissions. All four remain absent and are tested independently.

### 6.2 Broker Lambda execution role

The broker role has only:

- `ecs:RunTask` for the exact task-definition family/revision on the exact cluster, with Fargate launch type, required task tags, and only the two broker-derived request bootstrap values in section 5;
- `ecs:DescribeTasks` and `ecs:StopTask` for tasks on that cluster carrying the exact seller/connection/job tags;
- `iam:PassRole` for the exact task role and exact task-execution role, conditioned on `iam:PassedToService=ecs-tasks.amazonaws.com`;
- `s3:PutObject` plus `s3:PutObjectTagging` only for `requests/<connection-id>/<job-id>/<attempt>/request.json`, with bucket-policy conditions requiring `If-None-Match: *`, the canonical request media type, SHA-256 checksum, the exact control KMS key, and connection/job/attempt/runtime tags;
- `s3:GetObject`, `s3:GetObjectAttributes`, and `s3:GetObjectTagging` only for `results/<connection-id>/<job-id>/<attempt>/evidence.json`, and `s3:DeleteObject` only for those exact request and result key shapes after terminal acknowledgement;
- `kms:Encrypt` and `kms:GenerateDataKey` for the create-only request, and `kms:Decrypt` for result validation, only on the control key with `kms:ViaService` fixed to regional S3 and `kms:EncryptionContext:aws:s3:arn` restricted to the exact control-bucket request/result prefixes; and
- metadata-only log writes to the exact log group.

The broker has no source-bucket permission and cannot accept task command, arbitrary environment, role, image, subnet, security-group, CPU, memory, or storage overrides from ai.market. It constructs the fixed runtime values from the verified stack record and the two bootstrap values from the validated envelope. It cannot put a result, overwrite a request, list the control bucket, or read a request body after creation.

### 6.3 Task execution role

The execution role has `ecr:GetAuthorizationToken` on `*` only because ECR does not support a repository resource for that action; `ecr:BatchCheckLayerAvailability`, `ecr:GetDownloadUrlForLayer`, and `ecr:BatchGetImage` are restricted to the one approved release repository. It may create/write only the exact metadata log stream. It has no source bucket, control-bucket data, KMS decrypt for source objects, Secrets Manager field-token key, ECS control, IAM, or STS permission.

### 6.4 Profile task role

The task role is scoped to one verified connection and has only:

- `s3:ListBucket` on the exact source bucket with the exact non-root connection prefix condition;
- `s3:GetObjectAttributes` and `s3:GetObject` on that exact source prefix and, when versioned selectors are used, `s3:GetObjectVersionAttributes` plus `s3:GetObjectVersion`;
- `kms:Decrypt` only for explicitly registered seller KMS keys needed by selected source objects, restricted through S3 and the expected encryption context;
- `secretsmanager:GetSecretValue` on the single field-token key;
- `s3:GetObject`, `s3:GetObjectAttributes`, and `s3:GetObjectTagging` on the control-bucket request key shape `requests/<connection-id>/<job-id>/<attempt>/request.json`, with no `ListBucket`, version, sibling-connection, or result-read grant;
- `kms:Decrypt` on the control key for request retrieval, restricted by `kms:ViaService` and the request-key encryption context;
- `s3:PutObject` plus `s3:PutObjectTagging` on the matching exact result-key shape `results/<connection-id>/<job-id>/<attempt>/evidence.json`, with conditions requiring the configured SSE-KMS key ID, evidence media type, SHA-256 checksum, and exact connection/job/attempt/runtime tags in the same request; and
- `kms:Encrypt`, `kms:GenerateDataKey`, and `kms:Decrypt` on the control key for the tagged SSE-KMS result upload, restricted through regional S3 and to the matching result-key encryption context; and
- no other action.

The task role has explicit denies for other buckets, request writes, result-key reads, object deletion, ACL changes, untagged or wrongly encrypted writes, multipart upload/copy, network/infrastructure APIs, `sts:AssumeRole`, and secrets other than the token key. IAM limits source access to the verified connection prefix and control access to the connection-fixed request/result key shapes; the broker-derived bootstrap key, create-only request checksum/tags, and immutable selector narrow one task to its exact job/attempt and at most ten exact versioned source objects. The task never lists the control bucket and rejects any request whose path components, tags, body identity, input hash, or ECS task tags disagree.

### 6.5 W2 permission correction required before W3 activation

The present W2 verifier uses `HeadObject`, whose session policy includes `s3:GetObject`. A connection cannot become W3-ready while that centrally assumable role retains source-body read authority. The W3 build must add a profile-runtime upgrade ceremony that creates and verifies the split roles above, replaces the existing connection-role policy with section 6.1, and changes W2 verification to bounded `ListObjectsV2`/`ListObjectVersions` proof without any object-read permission. Existing W2 connections remain verified for W2 and remain profile-unavailable until the seller explicitly upgrades. No automatic IAM change, role-ARN change, ExternalId change, or silent policy replacement is allowed.

## 7. Control-plane contracts and routes

All routes remain under `/api/v1/seller-workspace`, require the active seller capability, owner-scoped lookup, a valid idempotency key for mutations, optimistic version protection, `Cache-Control: no-store`, and the master plus AWS-profile flags. Foreign and absent IDs are indistinguishable.

| Method and path | W3 contract |
| --- | --- |
| `POST /connections/{connection_id}/profile-runtime/verify` | Verify the exact broker alias, stack ID/version, region, role split, task definition digest, network controls, and no-source-read broker probe. Store only redacted runtime identifiers/hashes. It never creates or changes AWS resources. |
| `POST /profile-jobs` | Accept one verified connection/runtime and an immutable selector of 1–10 exact objects under the connection prefix. Freeze versions/ETags, quotas, parser/image/schema versions, create `queued`, and enqueue control work. |
| `GET /profile-jobs/{job_id}` | Return owner-visible state, bounded progress counters, safe failure code, evidence reference when successful, and no provider raw error or source content. |
| `POST /profile-jobs/{job_id}/cancel` | Move a queued job directly to `cancelled`, or record `cancel_requested` and invoke broker stop for a live task. A completed result wins only if it committed before the cancel transaction. |
| `GET /profile-evidence/{evidence_id}` | Return the normalized evidence schema in section 9 only to the owning seller. It is not public and is not sent to allAI in W3. |

Object discovery/selection may return owner-only object identity metadata already permitted by the connection (`key`, version/ETag, size, last-modified, format candidate). It must not read a body. Object identifiers are confidential operational metadata: they are encrypted or access-controlled like connection scope, excluded from profile evidence/allAI/logs, and never exposed to another seller or buyer.

Every cross-account broker call carries a canonical JSON envelope with exactly: `schema_version`, `operation`, `seller_id`, `connection_id`, `runtime_version`, `job_id`, `attempt`, `input_hash`, `selector`, `quota_profile`, `parser_version`, `image_digest`, `evidence_schema_version`, `issued_at`, and `expires_at`. The seller, connection, runtime, job, attempt, selector, limits, and digests are immutable. The broker rejects unknown fields, expiry, clock skew over 60 seconds, replayed start, an input-hash mismatch, a selector outside the verified prefix, and any runtime identity drift.

## 8. Job lifecycle, leases, retries, and concurrency

The durable states are:

`queued -> starting -> running -> validating_result -> succeeded`

and terminal alternatives:

- `queued -> cancelled`;
- `starting|running -> cancel_requested -> cancelled`;
- `queued|starting|running|validating_result -> failed`;
- `queued|starting|running -> expired` when its hard deadline passes.

Only `succeeded`, `failed`, `cancelled`, and `expired` are terminal. Illegal transitions fail closed and append a redacted audit event. A job input never changes. A retry creates `attempt + 1` under the same job and input hash; it is allowed once, only for launch capacity, transient AWS control-plane, Spot-interruption-equivalent, or broker transport failures before a valid result commits. Parser rejection, quota exhaustion, schema rejection, permission denial, digest drift, or suspected raw-output leakage is not retried automatically.

The ai.market profile-control worker uses the existing Redis/Celery substrate only for metadata orchestration. It has a new dedicated `seller_workspace_profile_control` queue and a separately deployed worker with concurrency 4, prefetch 1, late acknowledgement, and no source SDK client. The Fargate task, not the Celery child, is the parser. Task state is reconciled from broker responses and seller-account task events; a stale Celery delivery may poll idempotently but may not launch another attempt.

Timing is exact:

- queue wait: 5 minutes maximum;
- task start: 5 minutes maximum after broker acceptance;
- task wall time: 10 minutes maximum;
- result validation/commit: 2 minutes maximum;
- total job deadline: 20 minutes;
- task stop grace: 30 seconds;
- broker request/result artifacts: delete immediately after terminal acknowledgement, with one-day lifecycle as fail-safe;
- at most one running job per connection, two running jobs per seller, four queued jobs per seller, and twenty running jobs globally in ai.market control state.

Concurrency is enforced transactionally before launch and rechecked by the broker. Reconciliation may reduce observed capacity after crashes; it may never launch beyond a reserved slot. Provider ambiguity stays `starting` or `running` until reconciled and is never rewritten as a definitive denial.

## 9. Evidence schema and data minimization

The only accepted result is canonical UTF-8 JSON, media type `application/vnd.aimarket.seller-profile+json`, at most 131,072 bytes, with no duplicate keys, NaN/Infinity, byte-order mark, comments, unpaired surrogates, unknown fields, or non-canonical numbers. The top-level schema is `seller_workspace_profile_evidence.v1`:

```json
{
  "schema_version": "seller_workspace_profile_evidence.v1",
  "job_id": "uuid",
  "attempt": 1,
  "input_hash": "sha256-hex",
  "selector_hash": "sha256-hex",
  "runtime": {
    "provider": "aws",
    "execution": "ecs_fargate",
    "region": "aws-region",
    "task_definition_digest": "sha256-hex",
    "image_digest": "sha256:hex",
    "parser_version": "semver-or-git-sha",
    "field_token_key_version": "opaque-version"
  },
  "limits": {
    "objects": 10,
    "source_bytes_per_object": 67108864,
    "source_bytes_total": 268435456,
    "rows_per_object": 100000,
    "rows_total": 250000,
    "fields_per_object": 512,
    "json_depth": 32,
    "decompressed_bytes_total": 536870912,
    "wall_seconds": 600
  },
  "observed": {
    "objects_completed": 0,
    "source_bytes_read": 0,
    "decompressed_bytes": 0,
    "rows_examined": 0,
    "peak_memory_bytes": 0,
    "cpu_milliseconds": 0,
    "truncated": false,
    "truncation_reasons": []
  },
  "objects": [],
  "findings": {
    "pii_classes_present": [],
    "quality_flags": [],
    "warning_codes": []
  },
  "started_at": "RFC3339 UTC",
  "finished_at": "RFC3339 UTC",
  "result_hash": "sha256-hex"
}
```

Each object entry contains only `object_ref` (an opaque job-assigned identifier), source size, version-binding kind (`version_id` or `etag_size`), format, format metadata below, row-count object `{value, accuracy}` where accuracy is `exact`, `estimate`, or `lower_bound`, positional field records, and safe warning codes. It does not contain bucket, key, account, role, ARN, URL, filename, extension, source timestamp, raw checksum, or provider response.

Every field record contains only:

- `position` and a synthetic structural position such as `f0001` or `f0001.f0002`;
- `field_token`, computed as HMAC-SHA-256 over the normalized full field path with the seller-owned token key, plus key version;
- `physical_type` from the allowlist `null|boolean|integer|decimal|float|string|binary|date|time|timestamp|list|struct|map|unknown`;
- `nullable_observed`;
- `non_null_count`, `null_count`, and `distinct_band` (`0|1|2_10|11_100|101_1000|gt_1000|unknown`);
- `length_band` for string/binary values (`0|1_16|17_64|65_256|257_4096|gt_4096|not_applicable`);
- zero or more `pii_class` enums (`email|phone|postal_address|person_name|government_id|financial|health|precise_location|credential|other_sensitive`) and a confidence band (`low|medium|high`); and
- safe quality flags such as `all_null`, `mostly_null`, `high_cardinality`, `mixed_physical_types`, `invalid_encoding`, or `truncated`.

Exact field names, keys, values, samples, value hashes, minimums, maximums, quantiles, regex matches, snippets, and free-text parser messages are prohibited. Counts are non-negative integers and must reconcile with rows examined. A field token supports same-seller drift comparison without making low-entropy names guessable outside the seller account.

Canonical hashes use RFC 8785 JSON serialized as UTF-8. `result_hash` is SHA-256 over the evidence object with the `result_hash` member omitted; the broker recomputes it before accepting the supplied value. Field-token input is `seller_workspace_field_token.v1`, a NUL byte, the format enum, then for each path component a one-byte component-kind tag, four-byte unsigned big-endian UTF-8 byte length, and Unicode-NFC component bytes. CSV without a header uses only the ordinal component; headers, JSON keys, and Parquet names are used only inside this HMAC input and are then discarded. The token is lowercase hex HMAC-SHA-256. No unkeyed hash of a name/value is emitted.

### 9.1 CSV

Supported input is uncompressed RFC-4180-like CSV or TSV. Format metadata is limited to encoding (`utf-8|utf-16le|utf-16be|latin-1|unknown`), delimiter (`comma|tab|semicolon|pipe|other`), quote mode (`double|single|none|other`), header presence (`present|absent|uncertain`), line ending (`lf|crlf|cr|mixed`), detected column count, malformed-row count, and row-count accuracy. The parser never returns header text or cells. Spreadsheet formula prefixes are counted only as `formula_like_cells_present`; formulas are never evaluated.

### 9.2 JSON

Supported input is uncompressed JSON Lines, a top-level array of records, or one top-level object. Format metadata is limited to framing (`jsonl|array|object`), root type, records observed, maximum depth observed, malformed-record count, and heterogeneous-structure flag. Keys become field tokens inside the task; values never leave. Duplicate keys, excessive nesting, overlong numbers/strings, and non-finite numbers fail closed according to section 10.

### 9.3 Parquet

Supported input is Parquet with a readable footer and only parser-library-supported encodings/codecs. Format metadata is limited to Parquet version, row-group count, row count and accuracy, field count, codec enums, and whether page/column indexes are present. Field names become tokens. Statistics containing source values, key-value metadata, created-by strings, embedded Arrow metadata, bloom-filter bytes, and page data never leave. Encrypted Parquet and external page/index references are unsupported in W3.

## 10. Hard quotas and parser isolation

These are server-enforced maxima, not UI hints:

| Limit | Value |
| --- | ---: |
| Objects per job | 10 |
| Declared object size | 100 GiB each |
| Source bytes read | 64 MiB per object; 256 MiB per job |
| Rows parsed | 100,000 per object; 250,000 per job |
| Fields/leaves | 512 per object; 2,048 field records per job |
| CSV/JSON scalar | 64 KiB |
| CSV row or JSON record | 1 MiB |
| JSON depth | 32 |
| Parquet footer | 16 MiB |
| Parquet row groups opened | 8 per object |
| Decompressed bytes | 128 MiB per object; 512 MiB per job |
| Compression ratio | 100:1 |
| Result JSON | 128 KiB |
| CPU/memory/ephemeral disk | 1 vCPU / 4 GiB / 20 GiB |
| Wall time | 10 minutes |

CSV and JSON are prefix-sampled within byte/row limits; their total row counts are never called exact unless the task reached a verified end-of-object. Parquet may obtain exact row counts from bounded footer metadata, but field statistics remain locally classified and raw footer values remain inside the seller account. Reaching a sampling cap produces a valid truncated result only when parsing remained structurally safe; decompression, allocation, depth, record-size, footer-size, or schema-limit violations fail the object/job.

The runtime:

- detects format from bounded magic/structure, never extension alone;
- supports only CSV, TSV, JSON, JSONL, and Parquet; rejects ZIP, TAR, GZIP, XLS/XLSX, databases, images, documents, symlinks, sparse files, recursive containers, and external references;
- uses no shell, `eval`, dynamic import, parser extension, DuckDB extension, SQL execution, macro, UDF, plugin, subprocess command, URL reader, or remote filesystem;
- treats filenames, headers, keys, values, schemas, Parquet metadata, Unicode controls, formulas, HTML/Markdown, and instruction-like strings as inert bytes/data;
- runs the parser in a child process with hard address-space, file-size, open-file, process-count, and CPU limits; the supervisor kills the process group on limit, timeout, cancellation, or SIGTERM;
- writes temporary bytes only to the task's encrypted ephemeral directory, with one directory per attempt and restrictive permissions;
- never logs source content or raw exceptions; maps failures to stable allowlisted codes; and
- deletes temporary files before normal exit while relying on Fargate task destruction as the crash/kill cleanup boundary.

The parser package may port a small deterministic AIM Data algorithm or fixture only when the candidate records source path/commit, copies no runtime dependency, removes sample/value outputs, passes the W3 quotas, and is reviewed as W3 code. A dependency/import test must fail on any `aim-data`, AIM Data application module, local database, install identity, serial, tunnel, broker client, or Docker-runtime import.

## 11. Cost controls

Fargate and S3/KMS/Logs charges accrue in the seller AWS account. That commercial fact is a Max decision in section 18, not something the builder may hide in copy.

Technical controls are binding regardless of that decision:

- no service or idle task; one on-demand Fargate task per attempt;
- no Fargate Spot in W3, so interruption behavior and estimates are deterministic;
- the fixed `1 vCPU`/`4 GiB` task cannot be overridden;
- 10-minute task and 20-minute job deadlines;
- one automatic infrastructure retry maximum;
- seller/connection/global concurrency and daily/monthly quotas of 20 jobs per seller per day and 100 per seller per rolling 30 days;
- before start, the seller sees selected object count, maximum bytes read, task size, maximum runtime, possible retry count, and an estimated AWS-cost range computed from a versioned regional price table;
- the evidence records actual task duration, CPU/memory allocation, bytes read, and price-table version so the estimate is recomputable;
- every resource is tagged `ai-market:seller-workspace=w3`, connection hash, job ID, attempt, and runtime version without seller email or source names; and
- optional seller-owned AWS Budget alarms may notify or deny later launches, but AWS Budgets is not treated as an instantaneous hard stop. The broker and ai.market quotas are the launch boundary.

A stale/missing price table makes profiling unavailable; it never silently estimates zero. No listing fee, ai.market infrastructure surcharge, or billing integration is introduced by W3.

## 12. Cleanup and retention

On success, failure, cancellation, expiry, parser crash, broker timeout, worker death, or task kill:

1. stop or observe termination of the exact task;
2. prevent a late result from committing after a terminal attempt;
3. delete the attempt request and result objects after terminal acknowledgement;
4. verify the expected keys are absent; and
5. retain only redacted audit/provenance and the allowed evidence record.

Fargate destruction removes task memory and ephemeral storage. The one-day S3 lifecycle is a recovery backstop, not proof of immediate cleanup. Control-bucket versioning, replication, Object Lock, inventory exports, access logging with object names, and backup are disabled by the W3 stack so deletion does not create retained copies. CloudWatch task logs contain only allowlisted lifecycle fields and expire after seven days. CloudTrail and VPC Flow Logs remain seller-controlled AWS audit evidence under the seller's policy; they must not include request/result bodies.

Failed, cancelled, and expired job rows retain redacted state, counters, hashes, and failure code for 30 days. Successful W3 evidence expires after 30 days unless a later approved W4 record references its immutable evidence hash; W3 itself cannot create that reference. Expiry deletes the evidence payload and preserves only event identity, actor, timestamps, decision, hashes, and deletion proof under the existing audit-retention policy.

## 13. Persistence and migrations

One additive Alembic revision creates:

- `seller_workspace_profile_runtimes`: seller/connection ownership, AWS region, status, optimistic version, encrypted or redacted broker/runtime references, verified task/image/network/role hashes, token-key version, verified/disabled timestamps;
- `cloud_object_selectors`: seller/connection ownership, immutable selector version, encrypted object identities, version/ETag/size bindings, selector hash, created timestamp;
- `seller_workspace_profile_jobs`: seller, connection, runtime, selector, state, attempt, input hash, quota profile, parser/image/evidence versions, task ARN hash, deadlines, counters, safe failure code, evidence reference, idempotency key, timestamps;
- `seller_workspace_listing_evidence`: seller/job ownership, schema version, canonical JSON payload, result hash, provenance hashes, expiry and deletion timestamps; and
- nullable `profile_job_id` plus owner-preserving composite foreign key/index on `seller_workspace_audit_events`.

Database checks enforce state enums, positive versions/attempts/limits, terminal timestamps, payload size, hash shapes, unique seller/idempotency operation, one evidence row per successful attempt, and same-seller composite foreign keys. Audit update/delete triggers remain append-only. Selector and successful evidence payloads are immutable; a new source or parser version creates a new selector/job/evidence row.

The migration inserts no W3 rows, rewrites no W2 row, changes no existing connection status, and touches no `serials`, listing, order, delivery, or `legacy_serial` column/constraint. Downgrade is permitted only before any W3 row exists; otherwise rollback leaves the additive tables inert and flags off rather than destroying audit/evidence.

## 14. Audit and Gate 4 evidence contract

Each lifecycle action appends an ai.market audit event containing actor kind/ID, seller, connection, runtime, job, attempt, operation, prior/new state, input/selector/result hashes, resource version, quota profile, parser/image/task-definition digests, decision, safe outcome/failure code, and redacted evidence reference. It never contains source identifiers outside the owner-only selector store, task credentials, raw AWS errors, source content, field names, values, result-object bytes, or the field-token key.

Gate 4 is conjunctive and must produce one redacted immutable receipt binding:

- exact backend and seller-runtime source commits, built artifacts, image digest, task-definition revision, CloudFormation template digest, and deployed identities;
- default-off master/AWS-profile flags and truthful capability response before and after proof;
- synthetic seller/account/connection/runtime/job IDs and timestamps;
- CloudTrail evidence that ai.market assumed only the broker-invoke role and invoked only the exact broker alias;
- IAM-policy and negative-call evidence that the ai.market connection-control and broker roles could not `GetObject`, `GetObjectVersion`, `HeadObject`, or `GetObjectAttributes` from the source bucket, while only the task role read the exact selected versions;
- ECS task/event evidence for cluster, task ARN, image digest, CPU/memory/storage, private ENI, no public IP, start/stop reason, and task destruction;
- VPC Flow Log/route/endpoint evidence showing no public/NAT/ai.market/allAI egress from the task;
- source-read byte counts, result checksum/size/schema validation, and exact request/result cleanup timestamps;
- canary scans proving raw source rows/cells/names and seeded injection strings are absent from ai.market database, Redis/Celery payloads/results, logs, traces, errors, audit, evidence, and allAI;
- success plus parser error, quota, cancellation, timeout, worker-death, task-kill, stale-result, role-drift, image-drift, and cleanup paths;
- unchanged W2 connection management and unchanged legacy fulfillment evidence; and
- seller-visible pre-run cost disclosure plus recomputable actual task usage.

Static review, tests, migration success, AWS stack identity, IAM denial, network proof, cleanup proof, browser journey, and `legacy_serial` proof are independent. No queue label, route response, CloudFormation success, ECS success, or provider log substitutes for another item.

## 15. Flags, capability truth, and rollback

All controls remain default-off:

- `SELLER_WORKSPACE_ENABLED=false`;
- `SELLER_WORKSPACE_AWS_CONNECT_ENABLED=false` unchanged;
- `SELLER_WORKSPACE_AWS_PROFILE_ENABLED=false` unchanged;
- all AWS publish/delivery and every R2 flag remain false.

The profile stage reports `not_implemented` until the complete reviewed W3 code is present. After implementation it reports available only when the master and AWS-profile flags are explicitly true, W2 connect is available, the connection is verified, the split profile runtime is verified at the exact approved hashes, the control worker is ready, the price table is current, and every dependency is healthy. A stray environment variable, route, table, seller stack, or task definition never makes the stage available.

Rollback order is:

1. turn off AWS profile, leaving master/connect and all other stage flags at their prior values;
2. refuse new jobs and cancel queued jobs;
3. request stop for running tasks and reconcile them to terminal state;
4. perform and verify request/result cleanup;
5. retain redacted audit and allowed evidence until normal expiry;
6. roll back backend/control-worker code to the last known-good commit; and
7. leave additive schema inert. The seller, not ai.market, chooses whether to delete the AWS stack.

Rollback never disables or rotates a verified W2 connection, rewrites a listing authority, invokes AIM Data, or affects `legacy_serial` fulfillment.

## 16. Required test plan

### 16.1 Contracts and authorization

- capability remains default-off and dependency-aware;
- two sellers plus foreign connection/runtime/selector/job/evidence IDs for create, list, read, cancel, retry, and expiry, with uniform non-enumerating denial;
- immutable envelope, idempotency replay/conflict, optimistic version, stale attempt, late result, and terminal-transition tests;
- exact broker alias/external-ID verification and rejection of mutable versions or runtime drift;
- IAM simulation and live synthetic negative calls for every forbidden action, especially source `GetObject` by ai.market/broker roles and any non-selected-prefix access by the task;
- no command/environment/role/image/network override path;
- redaction scans across HTTP errors, structured logs, traces, Celery payloads/results, audit, database JSON, and result validation errors.

### 16.2 Parsers and hostile inputs

Golden deterministic CSV/TSV, JSON/JSONL, and Parquet fixtures pin canonical evidence bytes and hashes. Tests cover empty input, encodings, quoting, multiline cells, duplicate/missing headers, ragged rows, duplicate JSON keys, heterogeneous objects, Unicode controls, very long scalars, deep nesting, huge numbers, malformed footer/page metadata, every supported Parquet codec, allocation/decompression bombs, formula cells, HTML/Markdown, tool syntax, prompt instructions, URLs, credentials, PII, and source strings copied into exception messages.

Tests prove names/keys/values/min/max/quantiles/samples never appear, field tokens are stable only for the same seller key version, different seller keys produce different tokens, counts reconcile, truncation is truthful, and unsupported/archive/external-reference formats fail closed. Fuzz and crash tests run each parser in the same child-process/resource-limit boundary used by the image.

### 16.3 Lifecycle, cleanup, and cost

- success, deterministic parser failure, quota exhaustion, cancellation before launch/during run/during validation, 5-minute start timeout, 10-minute task timeout, broker ambiguity, Celery worker death, task SIGTERM/SIGKILL, and one permitted infrastructure retry;
- concurrency and 20/day, 100/30-day quotas under races;
- task/request/result cleanup on every terminal path and one-day lifecycle backstop;
- fixed CPU/memory/storage and no override, price-table staleness, estimate calculation, retry maximum, usage reconciliation, and tag completeness;
- task ENI/private route/VPC endpoint tests and a failed attempt to reach public internet or ai.market; and
- result length, duplicate-key, checksum, media-type, schema, unknown-field, counter, provenance, and raw-string rejection before ai.market persistence.

### 16.4 Migration and existing behavior

- Alembic upgrade on empty and W2-populated PostgreSQL databases;
- same-seller composite foreign keys, constraints, append-only audit trigger, immutability, and downgrade-empty/refuse-nonempty behavior;
- all existing W2 Seller Workspace connection tests;
- `tests/test_delivery_endpoints.py`, `tests/test_delivery_guarantees.py`, `tests/test_delivery_service.py`, `tests/test_delivery_webhook_integration.py`, `tests/test_serial_serial_id_contract.py`, `tests/test_serial_service.py`, and `tests/test_source_delivery.py` unchanged; and
- dependency/import scans proving no AIM Data runtime, package, database, serial, tunnel, broker client, or container dependency.

## 17. Acceptance criteria

W3 may pass Gate 3 only when the exact candidate proves all of the following:

1. raw source bytes are read only by one seller-account task role and never enter ai.market;
2. only the bounded canonical evidence schema crosses the broker boundary;
3. CSV/JSON/Parquet outputs are deterministic, size-limited, value-free, and injection-inert;
4. every permission is role-separated and negative-call tested;
5. every job is owner-bound, immutable, quota-bound, idempotent, cancellable, and terminally cleaned;
6. worker/task death cannot leak bytes, duplicate a launch, exceed concurrency, or commit stale evidence;
7. seller cost exposure is bounded, disclosed, tagged, measured, and recomputable;
8. all public, AWS publish/delivery, R2, W4/W5, and AIM Data runtime capabilities remain unavailable;
9. additive migrations preserve all W2 rows and constraints; and
10. the complete unchanged `legacy_serial` test selection passes with no authority fallback or migration.

Gate 4 additionally requires the complete live synthetic evidence in section 14 on the exact reviewed/deployed identities. Customer data or a customer account is never acceptable test material.

## 18. Genuine Max product decisions

These are product choices, not engineering facts. No builder or reviewer may infer them.

### D1 — May exact source field names leave the seller account?

This candidate's privacy-max baseline returns only seller-keyed field tokens, positions, types, counts/bands, and classifications. Exact CSV headers, JSON keys, and Parquet field names are source bytes and do not leave. That is the strongest reading of CORE and preserves a clean custody claim, but it gives a later W4 listing assistant less useful schema language.

Max must choose:

- **A (recommended):** keep exact names inside the seller account for W3; W4 may later request a separate, explicit seller-approved disclosure contract; or
- **B:** treat exact schema names as approved non-sensitive metadata in W3, requiring a new bounded schema, seller confirmation, redaction rules, and revised acceptance evidence before build.

### D2 — Is seller-paid AWS execution the intended commercial experience?

Seller-account execution necessarily places Fargate, S3, KMS, ECR/network-endpoint, and log charges on the seller's AWS bill. W3 can bound and disclose them, but cannot silently decide who should pay or how that promise is described.

Max must choose:

- **A (recommended):** seller pays its AWS-native profiling cost, with explicit pre-run estimate/acknowledgement and no ai.market listing fee; or
- **B:** ai.market subsidizes profiling, which requires a different funding/credit design but must not move raw execution into ai.market.

Until D1 and D2 are recorded, Gate 1 may be reviewed for architecture but Gate 2/build dispatch remains blocked.

## 19. Source references

- AWS ECS Fargate task definitions and networking: <https://docs.aws.amazon.com/AmazonECS/latest/developerguide/fargate-tasks-services.html>
- AWS ECS task roles: <https://docs.aws.amazon.com/AmazonECS/latest/developerguide/task-iam-roles.html>
- AWS ECS task-execution role: <https://docs.aws.amazon.com/AmazonECS/latest/developerguide/task_execution_IAM_role.html>
- Fargate ephemeral-storage security: <https://docs.aws.amazon.com/AmazonECS/latest/developerguide/security-fargate.html>
- Fargate customer-managed ephemeral-storage key: <https://docs.aws.amazon.com/AmazonECS/latest/developerguide/fargate-create-storage-key.html>
- ECS task-state events: <https://docs.aws.amazon.com/AmazonECS/latest/developerguide/ecs_task_events.html>
- S3 prefix policy conditions: <https://docs.aws.amazon.com/AmazonS3/latest/userguide/amazon-s3-policy-keys.html>
- S3 API permission mapping, including the `s3:GetObject` requirement for object attributes: <https://docs.aws.amazon.com/AmazonS3/latest/userguide/using-with-s3-policy-actions.html>
- AWS Budgets limits and actions: <https://docs.aws.amazon.com/cost-management/latest/userguide/budgets-managing-costs.html>
