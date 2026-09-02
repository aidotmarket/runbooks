# BQ-SELLER-WORKSPACE-W3-PROFILING-S1650 Gate 1 architecture specification

**Status:** Gate 1 corrective candidate. Max selected D1=A and D2=A in authenticated directive event `127c8533-5f58-4b87-a8fe-3a81469d64a1` and authorized CC/GLM/DeepSeek for this review in event `b756003d-6d8c-4835-8c36-dc53a6f97ce1`. Build remains blocked until that required panel approves this exact resulting digest.

**Build Queue entity:** `build:bq-seller-workspace-w3-profiling-s1650`

**Expected branch:** `spec/bq-seller-workspace-w3-profiling-s1650`

**Scope:** W3 AWS profiling architecture only. This document authorizes no product code, deployment, provider mutation, customer-data access, public enablement, AIM Data runtime import, W4, W5, R2, publication, sample generation, or delivery work.

## 1. Pinned evidence and governing conflict

This candidate was authored against:

- runbooks `19e3cb87e0c4263b4d1a1b78a920e6165c56d1d6`, including `seller-workspace-cloud-listing-delivery.md` SHA-256 `2ac591901c70a0612c17dc62578a01047f78f75039beba75137fc9faa99f5823`;
- ai-market backend `50fdb680a5b89265a7e668223bfa1b8728c6c4e9`;
- canonical `docs/core/CORE.md` version 9.15, SHA-256 `385042239afac7c54cadefca6be2107e67cb3da2c442be63fdb9fd6b0bdc11e5`;
- AIM Data `f5e92c80a93c159989340d7c45018e2dcea55f53`, inspected only to identify reusable algorithms, unsafe runtime assumptions, and the exclusion boundary.

Round-1 review was performed on candidate `78a2b8e3e317d69207ec092b5156c6e63c831509`, file SHA-256 `e71fa0cea113dcf366152f25838576c668234085ada9b9055691cc448cd901d7`. This revision folds the complete CC response `/Users/max/council/cc/response-20260902-015302-385335.md` and GLM response `/Users/max/council/glm/response-20260902-015303-186203.md`. It also records Max's D1=A and D2=A choices from event `127c8533-5f58-4b87-a8fe-3a81469d64a1`; it does not authorize implementation or reuse either earlier verdict for this new digest.

No round-2 panel verdict is claimed in this document; the numbering below preserves the governed dispatch history rather than renumbering later recorded rounds.

Round-3 review of candidate `5253fe8d8ac055ff2b60e181b0d9b3bd9bc902da`, file SHA-256 `b162dc8bdd828347030abd14d68715eda79005f92d64ad7b9add44891ab3c8e2`, returned CC `APPROVE_WITH_NITS`, GLM `REQUEST_CHANGES`, and DeepSeek `APPROVE_WITH_NITS`, recorded in event `9efa5779-34d7-447c-81a5-9c23ac2a19a1`. This corrective revision folds those exact findings. No earlier verdict carries forward to this digest.

Round-4 review of candidate `c29f8fbc0e17c2e99ccf79cd3b028d26a7ece408`, file SHA-256 `1f95aefa1057b065ad949ac4fecb59541fc2cfa6dad1bcb13a9fc9528a6f0cfa`, returned GLM `REQUEST_CHANGES`, DeepSeek `APPROVE_WITH_NITS`, and no CC vote after a bounded profile-lock wait, recorded in event `784ee29b-853d-4fad-beac-3f659ae07c67`. This corrective revision folds those findings. No round-4 verdict carries forward to this digest.

Round-5 review of candidate `f3d0cf222b4ca3f5ac9062dd29cc0e4ed779f0e9`, file SHA-256 `c2799d7e0735ce32e53936e5143272254a9217e3bd93e89b7550eb0c1c26080b`, returned CC `APPROVE_WITH_NITS`, GLM `REQUEST_CHANGES`, and DeepSeek `APPROVE_WITH_NITS`, recorded in event `88f463b7-c59a-4cd1-abf3-bd76da79cc41`. This corrective revision folds those findings. No round-5 verdict carries forward to this digest.

Round-6 review of candidate `25663d314390b611ff3b9d9f31d0dda5a10f1db7`, file SHA-256 `b1505ce91c7580b756b42b92e4ce452a25e35f086007ef5b0bbee0037d42db48`, returned CC `APPROVE_WITH_NITS`, GLM `REQUEST_CHANGES`, and DeepSeek `APPROVE_WITH_NITS`, recorded in event `fdabfe30-35f8-4943-a5af-450a58009826`. This corrective revision folds the product-spec findings; the next review package separately supplies repository/diff/check evidence and numbered failure-mode questions. No round-6 verdict carries forward to this digest.

Round-7 review of candidate `2cf797b702eb0d2ebf400d65c07a2efc6ecf264a`, file SHA-256 `0ca3566e734bdbb5192f86d022a6ab7972dd191c9ab59697f8620bafa242a202`, returned CC `REQUEST_CHANGES`, GLM `REQUEST_CHANGES`, and DeepSeek `APPROVE_WITH_NITS`, recorded in event `c974020c-4b2c-4a4e-bee5-b13e9f2ac7b4`. This corrective revision folds those findings. No round-7 verdict carries forward to this digest.

Round-8 review of candidate `bbc22643cfe9cdd684fdc2b233a188c053bc5554`, file SHA-256 `0eacbb1d1cbe92ea7fa1173bd2dcddbf3bb35a0f956632aafbbcac72203a48c3`, returned CC `APPROVE_WITH_NITS`, GLM `REQUEST_CHANGES`, and DeepSeek `REQUEST_CHANGES`, recorded in event `f3d46127-c576-4678-aca3-c081fcb2a480`. This corrective revision folds every blocking finding and nit. No round-8 verdict carries forward to this digest.

Round-9 review of candidate `07f6d218679df682ca51216335f38a3853663a06`, file SHA-256 `69a85ae3ca5622a3a99bdce6ab4e3f3af54502a7031f44322ce9a3bbce0289d6`, returned CC `APPROVE`, GLM `REQUEST_CHANGES`, and DeepSeek `APPROVE_WITH_NITS`, recorded in event `e2fb7310-1012-4a4d-9ae7-5aa2f83b1ce5`. This corrective revision folds the DNS-resolution blocker and every round-9 nit. No round-9 verdict carries forward to this digest.

CORE 9.15 says both that ai.market is metadata-only/non-custodial and that raw customer data must not touch ai.market. The W1 runbook instead describes a backend-deployed isolated worker reading bounded source ranges. Isolation and bounded reads reduce exposure but do not change custody: raw bytes would enter an ai.market process. W3 therefore replaces that W1 execution placement with seller-account execution. It does not change the W2 connection lifecycle, W1 product outcome, or any delivery authority.

The relevant backend baseline has:

- one backend-owned capability response with every later stage hard-coded `not_implemented` and every flag default-off;
- W2 connection, encrypted ExternalId, audit, and `DeliveryAuthority` schema foundations only;
- no selector, profile job, evidence, profile route, profile queue, or profile task;
- a W2 verification session policy containing `s3:GetObject` because the implementation calls `HeadObject`, even though it never reads a body;
- shared Celery workers and queues only; there is no Seller Workspace profile-control queue or deployment.

The AIM Data baseline is deliberately unsuitable as a W3 runtime. It is a customer-installed, single-install product with local filesystem/database state and a broad processing service. Its S3 registration path downloads an object into `record.upload_path`; its DuckDB profiling can emit names, minimums, maximums, and sample values. Those facts are evidence for exclusion, not a request to change AIM Data.

## 2. Binding outcome

W3 uses one seller-deployed AWS broker Lambda to launch one seller-account ECS Fargate task per profile attempt. The task reads the selected S3 objects inside the seller account, writes one bounded metadata output into a dedicated seller-owned control bucket, and exits. The broker validates that internal output, constructs the separately hashed runtime/cost attestation after task termination, and returns only the final bounded result to ai.market. No source object body, raw range, row, cell, field name, JSON key, Parquet field name, sample, minimum, maximum, provider credential, presigned URL, or parser stderr may enter ai.market.

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

The later W3 implementation supplies a versioned CloudFormation template for the seller to inspect and deploy. One stack/runtime is bound one-to-one to one `CloudConnection`; roles and source-prefix permissions are not shared across connections. W3 product code may verify the stack through the read-only verifier below but may not create, update, or delete it. The seller passes the already pinned connection-role name and explicitly removes its old object-read policy as part of the upgrade. The stack contains exactly:

- one broker Lambda function and immutable published alias. Its published version has the stack-generated immutable environment value `W3_SOURCE_KEY_ARNS_CANONICAL_JSON`, equal to the RFC 8785 canonical zero-to-eight-key JSON array derived from the exact owner-visible CloudFormation parameter (`[]` for no source KMS keys). This seller-local value needs no broker API read permission, is covered by the function/version/template hashes, and never enters the ai.market-to-broker envelope;
- one runtime-verifier Lambda function and immutable published alias, with a distinct read-only execution role and no task-launch, role-pass, source-object, secret-value, or mutation authority;
- one ECS cluster for standalone Fargate tasks, Linux platform `1.4.0` or later, whose CloudFormation `Configuration.ManagedStorageConfiguration.FargateEphemeralStorageKmsKeyId` is the exact control-key ARN;
- one task definition pinned to an immutable image digest, fixed entrypoint, `1 vCPU`, `4 GiB` memory, `20 GiB` ephemeral storage, read-only root filesystem, non-root user, no privileged mode, no added Linux capabilities, and `stopTimeout=30` seconds;
- distinct verifier, broker, task, and task-execution IAM roles plus a template parameter that binds the existing cross-account connection-control role;
- one seller-owned control bucket with separate `requests/` and `results/` prefixes, public access blocked, TLS required, SSE-KMS, versioning disabled, replication disabled, backup excluded, incomplete multipart uploads aborted after one day, and object expiry after one day. Before first launch the broker writes one canonical request object with `If-None-Match: *`, checksum, JSON media type, SSE-KMS key ID, and connection/job/attempt/runtime tags. On an exact start reconciliation, an existing deterministic request key is read only by the broker, and canonical bytes, checksum, media type, KMS key, and all tags must equal the immutable attempt; an exact match proceeds to idempotent `RunTask`, while any mismatch terminally fails without replacement or source read. Neither broker nor task may replace it;
- one customer-managed KMS key for the control bucket and Fargate ephemeral storage, with grants limited by the stack resources, plus an optional closed set of at most eight seller customer-managed source-key ARNs bound to the connection/runtime as described below;
- private subnets, a no-ingress task security group, and only the endpoints needed to launch and run the task. The broker and verifier Lambdas are not VPC-attached; from Lambda-managed networking they call only their IAM-allowlisted AWS metadata/control-plane APIs and have no source-object permission. Task-security-group egress permits TCP 443 only to the exact interface-endpoint security group and the regional S3 managed prefix list, plus DNS only to the VPC resolver; it has no other rule. The interface-endpoint security group admits TCP 443 only from the task security group. The S3 gateway endpoint policy is an explicit allowlist for: the verified source bucket and objects under its exact connection prefix; the control bucket and only `requests/<connection-id>/.../request.json` plus `results/<connection-id>/.../evidence.json`; and read-only `s3:GetObject` on the mandatory regional ECR layer objects `arn:${AWS::Partition}:s3:::prod-${AWS::Region}-starport-layer-bucket/*`. Source/control bucket resources are additionally restricted to the verified seller account. ECR API, ECR Docker, CloudWatch Logs, Secrets Manager, and required KMS use private interface endpoints for the task;
- one stack-managed Route 53 Resolver DNS Firewall foundational rule group associated only with the exact W3 VPC. Its lower-numbered rule allows all query types only for the immutable exact allow-domain list generated from the runtime's partition, region, account, verified source/control buckets, regional S3 endpoint, exact ECR API/Docker and mandatory regional ECR layer-bucket names, exact Logs/Secrets Manager/KMS service names, exact interface-endpoint DNS names, and every DNS name in each approved CNAME/DNAME redirection chain. The allow rule uses the default `INSPECT_REDIRECTION_DOMAIN`; every subsequent redirection target must therefore be present in the same closed allowlist and is also independently allowed for a direct client query. A higher-numbered rule uses a separate domain list containing only `*` and blocks every other query with `NODATA`; the exact VPC configuration requires `FirewallFailOpen=DISABLED`. Wildcard allow entries, `TRUST_REDIRECTION_DOMAIN`, DNS Firewall Advanced rules, an additional rule-group association, and a Resolver forwarding/outbound endpoint are prohibited. The canonical sorted allow-domain list, one-entry block-all list, rule priorities/actions/redirection settings, association, fail-closed configuration, and their hash are runtime-bound and verified before launch. This permits only the names required for the already network-restricted AWS paths; it denies arbitrary public recursive DNS, encoded-label tunneling, ai.market, allAI, and unapproved redirect targets;
- no public IP, NAT gateway, internet gateway route, load balancer, inbound listener, ECS Exec, service discovery, EFS, EBS, shell endpoint, or long-lived ECS service;
- separate metadata-only task/runtime and EventBridge-audit CloudWatch log groups with seven-day retention, and one EventBridge rule whose only target is the audit group for task-state events. The rule is not a control or correlation path; authoritative reconciliation uses the exact task identity below; and
- one seller-owned HMAC key in Secrets Manager used only inside the task to create stable, non-reversible field tokens. The key value never leaves the seller account.

The image is pulled from the approved ai.market release ECR repository under a cross-account repository policy and by digest. A mutable tag is never an execution identity. Before any launch, the runtime verifier proves the pinned task-definition revision's image digest, task role, execution role, CPU, memory, storage, command, network mode, logging configuration, and read-only settings against the verified runtime record. The broker's `RunTask` condition then permits only that exact family/revision; after launch, every identity-validating `DescribeTasks` call supplies `include=["TAGS"]` and must return the same task-definition ARN, image digest, and exact task tags.

The request object, not a container command or selector-valued environment variable, is the immutable task input. `RunTask` may supply exactly two broker-derived bootstrap environment values: `W3_REQUEST_KEY` (the canonical key constructed from the validated connection/job/attempt) and `W3_REQUEST_SHA256` (the checksum of the create-only request object). The broker never copies an ai.market-provided override map and rejects every other container, command, environment, role, image, resource, or network override. The fixed entrypoint retrieves only that key and verifies checksum, media type, KMS key, request-object tags, schema, input hash, selector scope, source-key-set hash, and expiry before reading source data. For a `current` selector it issues source `GetObject` with the exact frozen ETag in `If-Match` and rejects a precondition failure or response ETag/content-length mismatch before parsing; for a `versions` selector it supplies the exact frozen `versionId` and rejects a returned version ID or content-length mismatch. Before parsing any response body, it requires S3-managed encryption or an `aws:kms` response key ARN in the exact runtime-bound registered set; missing, unregistered, wrong-account/region, disabled, asymmetric, or policy-mismatched source encryption fails closed. It never silently reads a newer current object. The task does not call ECS or inspect ECS task tags. Before accepting a result, the broker describes the persisted exact task ARN and verifies the task-definition revision, image digest, Fargate ephemeral-storage KMS key, network attachments, and broker-set task tags against the immutable request. Before either initial request creation or `reconcile_start`, the broker parses only its immutable seller-local `W3_SOURCE_KEY_ARNS_CANONICAL_JSON`, rejects non-canonical/duplicate/over-eight/wrong-account-or-region input, recomputes the lowercase SHA-256 set hash, and requires equality with the verified function/template/runtime and hash-only broker envelope. The request contains that exact canonical registered source-key ARN array so the task can test response-key membership inside the seller account; raw ARNs never enter ai.market transport or logs. A request/runtime/source-binding mismatch stops before source parsing; a later ECS identity/tag mismatch prevents result acceptance, requests stop of that exact task, and terminally fails the attempt.

The endpoint policy has no wildcard seller-bucket resource and no catch-all S3 statement. Its implicit deny is verified for every other source prefix, control key, seller bucket, regional/non-regional ECR layer bucket, S3 access point, and public S3 endpoint. Removing the regional ECR layer-bucket entry must make a private digest pull fail, while the complete allowlist must permit the exact digest pull without NAT or an internet-gateway route.

AWS documents the underlying primitives used here: Fargate tasks use `awsvpc` task ENIs; task roles and task-execution roles are distinct; platform 1.4.0 provides encrypted ephemeral storage and supports a customer-managed KMS key; and task state changes expose the image digest. These are platform facts, not completion evidence. W3 must still prove the exact deployed stack.

## 6. Least-privilege permissions

No role may combine two rows below.

### 6.1 Cross-account connection-control role

For a W3-ready connection this is the existing immutable `CloudConnection.role_arn`, still trusted only for the configured ai.market AWS principal with the existing random per-connection ExternalId. The seller replaces its permissions during the explicit profile-runtime upgrade; the role ARN and ExternalId do not silently change. Its permission policy contains only:

- `lambda:InvokeFunction` on only the exact published verifier and broker alias ARNs;
- `s3:ListBucket` on the exact source bucket, conditioned with `StringLike` so the request's `s3:prefix` is the normalized non-empty connection prefix ending in `/` or any descendant `${connection_prefix}*`, while empty, parent, sibling, widened, root-equivalent, and cross-connection prefixes cannot match; and
- `s3:ListBucketVersions` under the identical anchored prefix condition only when versioned selector discovery is enabled.

It has no object-ARN permission, including `s3:GetObject`, `s3:GetObjectVersion`, `s3:GetObjectAttributes`, `s3:GetObjectVersionAttributes`, or any range-read equivalent; no `ecs:*`, `iam:*`, `kms:*`, `secretsmanager:*`, `logs:*`, second `sts:AssumeRole`, wildcard resource, or unqualified Lambda-version permission. The ai.market session duration is at most 900 seconds. W2 verification and object discovery use bounded `ListObjectsV2`/`ListObjectVersions` results only and call neither `HeadObject` nor `GetObjectAttributes`. AWS requires `s3:GetObject` plus `s3:GetObjectAttributes` for an unversioned attributes call, and `s3:GetObjectVersion` plus `s3:GetObjectVersionAttributes` when `versionId` is supplied. All four actions remain absent, and negative tests issue the body, head, unversioned-attributes, and versioned-attributes calls independently.

### 6.2 Broker Lambda execution role

The exact task-tag key set is byte-for-byte `ai-market:seller-workspace`, `ai-market:seller-hash`, `ai-market:connection-hash`, `ai-market:job-id`, `ai-market:attempt`, and `ai-market:runtime-version`. `ai-market:seller-workspace=w3`, `ai-market:seller-hash`, `ai-market:connection-hash`, and `ai-market:runtime-version` are stack-fixed values. `ai-market:job-id` and `ai-market:attempt` are dynamic canonical safe values derived only from, and required to equal, the validated immutable broker envelope.

The broker role has only:

- `ecs:RunTask` for the exact task-definition family/revision on the exact cluster, with Fargate launch type, required task tags, and only the two broker-derived request bootstrap values in section 5. The `RunTask` statement requires exactly the allowlisted tag keys, exact stack-fixed W3/seller-hash/connection-hash/runtime-version values, and canonical safe job-ID/attempt shapes; broker code requires the dynamic job/attempt values to equal the validated envelope. The broker derives the ECS `clientToken` as the 64-character lowercase hex SHA-256 over the canonical version, exact cluster-ARN hash, seller, connection, job, attempt, and input hash; the same request parameters therefore replay the same AWS request and changed parameters conflict. The effective token window is `min(24 hours, task lifetime + 1 hour)`, which exceeds the 20-minute job deadline;
- `ecs:TagResource` on `Resource: *` only for tag-on-create authorization, conditioned with `ecs:CreateAction=RunTask`, the identical exact `aws:TagKeys` allowlist, exact stack-fixed request-tag values, and canonical safe dynamic tag shapes above. Because an ordinary standalone `TagResource` call has no matching `ecs:CreateAction`, it is denied; missing, extra, or wrong fixed tags also deny `RunTask`;
- `ecs:DescribeTasks` and `ecs:StopTask` only on `arn:${AWS::Partition}:ecs:${AWS::Region}:${AWS::AccountId}:task/<exact-cluster-name>/*`, conditioned on the exact cluster and stack-fixed W3/seller-hash/connection-hash/runtime-version resource tags. The broker accepts only the one encrypted exact task ARN carried by a validated poll/cancel envelope, requires its hash to match the attempt row, requires its dynamic job/attempt tags to equal the envelope, supplies the exact cluster on every call, and supplies `include=["TAGS"]` on every `DescribeTasks` identity check because ECS otherwise omits tags. The broker has no `ecs:ListTasks`; the namespace policy is static authorization while the persisted ARN and tags are application-level exact identity, never lookup;
- `iam:PassRole` for the exact task role and exact task-execution role, conditioned on `iam:PassedToService=ecs-tasks.amazonaws.com`;
- `s3:PutObject` plus `s3:PutObjectTagging` only for `requests/<connection-id>/<job-id>/<attempt>/request.json`. The broker must use `If-None-Match: *`, the canonical request media type, SHA-256 checksum, exact control KMS key, and connection/job/attempt/runtime tags; IAM/bucket-policy conditions enforce the supported KMS-key and request-tag conditions, while the broker and task validate the checksum/media type;
- `s3:GetObject` plus `s3:GetObjectTagging` only for the exact `requests/<connection-id>/<job-id>/<attempt>/request.json` during `reconcile_start` and for `results/<connection-id>/<job-id>/<attempt>/evidence.json` during validation, and `s3:DeleteObject` only for those exact request and result key shapes after terminal acknowledgement. Request recovery validates the bounded canonical body, checksum, media type, KMS key, and every tag against the immutable reconciliation envelope; result validation checks the bounded body and checksum. The broker never calls `GetObjectAttributes`;
- `s3:ListBucket` on the control bucket only with `s3:prefix` equal to the exact terminal attempt directory `requests/<connection-id>/<job-id>/<attempt>/` or `results/<connection-id>/<job-id>/<attempt>/` and `s3:max-keys<=2`, used only after deletion to prove both expected keys absent. Every sibling, parent, wildcard, or cross-connection prefix is denied;
- `kms:GenerateDataKey` for the create-only request and `kms:Decrypt` only for exact-request recovery or result validation, on the control key with `kms:ViaService` fixed to regional S3 and `kms:EncryptionContext:aws:s3:arn` restricted to the exact control-bucket request/result prefixes; and
- metadata-only log writes to the exact log group.

The broker has no source-bucket permission and cannot accept task command, arbitrary environment, role, image, subnet, security-group, CPU, memory, or storage overrides from ai.market. It constructs the fixed runtime values from the verified stack/function version, the seller-local canonical source-key array above, and the two bootstrap values from the validated envelope. A successful or idempotently replayed start returns the exact task ARN only to the owning ai.market control plane; it is never written to ai.market or application logs/audit/evidence/UI/allAI. Seller-owned CloudTrail and task-event audit may retain the ARN under the seller's policy. It cannot put a result, overwrite a request, or list any control-bucket prefix except the exact terminal attempt prefixes for post-delete absence proof; it may read a request body only through the exact-key, identity-matched `reconcile_start` path above.

### 6.3 Runtime-verifier Lambda execution role

The verifier accepts only the operation-specific envelope in section 7 and reads only configuration belonging to the exact tagged stack/runtime. It has `cloudformation:DescribeStacks`, `cloudformation:GetTemplate`, and `cloudformation:ListStackResources` for the exact stack; Lambda configuration/alias/policy reads for the broker and verifier; IAM role and policy-document reads for the five exact roles (connection-control, verifier, broker, task, and task-execution) and their attached policies; `ecs:DescribeClusters` for the exact cluster and `ecs:DescribeTaskDefinition` for the pinned revision; ECR image-description reads for the approved repository/digest; `kms:DescribeKey` and `kms:GetKeyPolicy` on the exact control key and up to eight runtime-registered source keys; control-bucket public-access, policy, encryption, lifecycle, versioning, replication, and Object Lock configuration reads; EventBridge rule/target and CloudWatch log-group configuration reads for the exact stack resources; the EC2 describe calls required for the stack's exact VPC, subnet, route-table, security-group, endpoint, endpoint-security-group, VPC-resolver, and S3 managed-prefix-list IDs; and read-only Route 53 Resolver calls `GetFirewallConfig`, `GetFirewallRuleGroup`, `ListFirewallRules`, `GetFirewallDomainList`, `ListFirewallDomains`, `GetFirewallRuleGroupAssociation`, and bounded `ListFirewallRuleGroupAssociations` for the exact stack-found rule group/domain lists/association and exact VPC. It requires the cluster's `Configuration.ManagedStorageConfiguration.FargateEphemeralStorageKmsKeyId` to equal the exact control-key ARN; every registered source key to be an enabled symmetric customer-managed key in the seller account and runtime region whose key-policy application statements permit only the exact task role to decrypt through regional S3 with the expected source-object encryption context and the exact verifier role to perform only `DescribeKey`/`GetKeyPolicy`; the live source-key-set hash to equal the authorization/runtime binding; and the DNS Firewall association, canonical allow-domain list, one-entry `*` block list, priorities, `ALLOW`/`BLOCK NODATA` actions, `INSPECT_REDIRECTION_DOMAIN`, wildcard-allow absence, and `FirewallFailOpen=DISABLED` to equal section 5. It rejects a missing/different binding, alias, wildcard allow, unapproved redirection target, extra association, cross-account/region key, or broader task-role use. AWS describe/list APIs that do not support resource ARNs use `Resource: *`, but the closed verifier code accepts only the connection role and IDs bound to the exact connection or found in the exact `ListStackResources` result, bounds and exhausts pagination, and emits only the source-key-set and DNS-firewall hashes rather than raw source-key ARNs, policies, domain names, credentials, or secret values.

The verifier has explicit denies for every mutation, `iam:PassRole`, `ecs:RunTask|StopTask|ExecuteCommand`, Route 53 Resolver create/update/delete/associate/disassociate/import action, STS role chaining, `s3:GetObject*`, `s3:ListBucket` on the source bucket, `kms:Decrypt|GenerateDataKey`, `secretsmanager:GetSecretValue`, and any resource not tagged/bound to the one runtime. It returns only a closed `seller_workspace_profile_runtime_verification.v1` receipt containing the expected/observed runtime version, stack/template/broker/task-definition/image/role/policy/network/control-resource/DNS-firewall hashes, `nonce_hash`, verification timestamp, safe mismatch codes, and receipt hash; the receipt hash covers every preceding receipt field including `nonce_hash`. Raw policies, DNS domain lists, ARNs not already stored for the owning connection, subnet/routes, bucket names, and source-prefix identities do not cross to ai.market.

### 6.4 Task execution role

The execution role has `ecr:GetAuthorizationToken` on `*` only because ECR does not support a repository resource for that action; `ecr:BatchCheckLayerAvailability`, `ecr:GetDownloadUrlForLayer`, and `ecr:BatchGetImage` are restricted to the one approved release repository. It may create/write only the exact metadata log stream. It has no source bucket, control-bucket data, KMS decrypt for source objects, Secrets Manager field-token key, ECS control, IAM, or STS permission.

### 6.5 Profile task role

The task role is scoped to one verified connection and has only:

- `s3:GetObject` on that exact source prefix and, only when versioned selectors are used, `s3:GetObjectVersion`; every current read must carry the frozen `If-Match` ETag and every versioned read the frozen `versionId`, with returned ETag/version and content length checked before parsing. The task never calls `HeadObject` or `GetObjectAttributes`, and the dedicated attribute actions remain absent;
- `kms:Decrypt` only for the zero-to-eight exact source KMS key ARNs registered, encrypted at rest, template-bound, live-verified, and hashed for this connection/runtime, restricted through regional S3 and the expected source-object encryption context. Aliases, wildcards, cross-account/region keys, and any key outside the immutable set are absent;
- `secretsmanager:GetSecretValue` on the single field-token key;
- `s3:GetObject` plus `s3:GetObjectTagging` on the control-bucket request key shape `requests/<connection-id>/<job-id>/<attempt>/request.json`, with no `ListBucket`, version, sibling-connection, result-read, or object-attributes grant;
- `kms:Decrypt` on the control key for request retrieval, restricted by `kms:ViaService` and the request-key encryption context;
- `s3:PutObject` plus `s3:PutObjectTagging` on the matching exact result-key shape `results/<connection-id>/<job-id>/<attempt>/evidence.json`. The client must send the configured SSE-KMS key ID, evidence media type, SHA-256 checksum, and exact connection/job/attempt/runtime tags in the same request; IAM/bucket-policy conditions enforce the supported KMS-key and request-tag conditions, and the broker validates all four classes before acceptance; and
- `kms:GenerateDataKey` on the control key for the tagged SSE-KMS result upload, restricted through regional S3 and to the matching result-key encryption context; and
- no other action.

The task role has explicit denies for other buckets, request writes, result-key reads, object deletion, ACL changes, untagged or wrongly encrypted writes, multipart upload/copy, network/infrastructure APIs, `sts:AssumeRole`, and secrets other than the token key. IAM limits source access to the verified connection prefix and control access to the connection-fixed request/result key shapes; the broker-derived bootstrap key, create-only request checksum/tags, and immutable selector narrow one task to its exact job/attempt and at most ten exact versioned source objects. The task never lists the control bucket and rejects any request whose path components, request-object tags, body identity, input hash, or selector scope disagree. ECS task identity and tags are validated only by the broker before result acceptance.

The control-bucket object-access statements admit only the broker and task operations above over TLS. Separate configuration-read statements admit the verifier only for the bucket-level configuration APIs in section 6.3 and confer no object or list permission. The policy explicitly denies wrong/missing control-key encryption, required tag keys/values, ACLs, and every principal outside the stack. For S3, the control KMS key policy mirrors the exact broker/task principals, operations, regional-S3 `ViaService`, and encryption-context boundaries. For Fargate ephemeral storage, the same key separately permits principal `fargate.amazonaws.com` only `kms:GenerateDataKeyWithoutPlaintext` and `kms:CreateGrant`, with `kms:EncryptionContext:aws:ecs:clusterAccount` equal to the seller account and `kms:EncryptionContext:aws:ecs:clusterName` equal to the exact cluster name; `kms:CreateGrant` additionally requires `ForAllValues:StringEquals kms:GrantOperations=[Decrypt]`. The exact verifier role alone among the five runtime roles may call `kms:DescribeKey` and `kms:GetKeyPolicy` for the control and registered source keys; broker, task, task-execution, and connection-control roles are denied. The seller's own CloudFormation/deployment administration remains outside the ai.market-callable runtime role set and does not enter a job envelope. Source-key grants created independently by the seller are outside W3 remote-attestation claims; the verifier proves the closed key-policy application statements and exact task-role IAM policy, while no ai.market principal receives source-key decrypt authority. The control key has no wildcard application principal or standing grant. IAM simulation proves the connection-fixed resource boundaries, while fixed-task negative calls prove the selector and broker-bootstrap narrowing within that connection. The positive test must exercise the same `PutObject` request that carries tags and therefore requires both `s3:PutObject` and `s3:PutObjectTagging`.

### 6.6 W2 permission correction required before W3 activation

The present W2 verifier uses `HeadObject`, whose session policy includes `s3:GetObject`. A connection cannot become W3-ready while that centrally assumable role retains source-body read authority. The W3 build must add a profile-runtime upgrade ceremony that creates and verifies the split roles above, replaces the existing connection-role policy with section 6.1, and changes W2 verification to bounded `ListObjectsV2`/`ListObjectVersions` proof without any object-read permission. Existing W2 connections remain verified for W2 and remain profile-unavailable until the seller explicitly upgrades. No automatic IAM change, role-ARN change, ExternalId change, or silent policy replacement is allowed.

## 7. Control-plane contracts and routes

All routes remain under `/api/v1/seller-workspace`, require the active seller capability, owner-scoped lookup, a valid idempotency key for mutations, optimistic version protection, `Cache-Control: no-store`, and the master plus AWS-profile flags. Foreign and absent IDs are indistinguishable.

| Method and path | W3 contract |
| --- | --- |
| `PUT /connections/{connection_id}/profile-runtime/source-kms-keys` | Before estimating or authorizing a runtime, accept zero to eight exact customer-managed KMS key ARNs declared by the owning seller. Require canonical key ARNs, one seller account and runtime region, no aliases/wildcards/duplicates, encrypt the ARNs under the owner-only application boundary, and persist an immutable version plus canonical set hash. The hash input is the RFC 8785 UTF-8 JSON array of unique ARN strings sorted by unsigned UTF-8 byte order; the set hash is lowercase SHA-256 hex. Submitting the current set is an idempotent no-op; every different submission, including reversion A→B→A, creates a new version and invalidates any unconsumed estimate/runtime binding. Historical versions may therefore repeat a canonical set hash. This route only records seller input; it does not call KMS or mutate AWS. |
| `POST /connections/{connection_id}/profile-runtime/estimates` | Before exposing the versioned stack template/upgrade instructions, create an immutable standing-cost receipt binding seller, connection, source-key-set hash/count, runtime/template digest, region, Availability Zone and interface-endpoint count, endpoint hourly/data-processing rates, control-key/Secrets Manager monthly storage and request-price assumptions, DNS Firewall foundational rule-group/association rate, exact custom-domain count and domain-name-month rate, explicit prohibition of Advanced rules, verifier Lambda and KMS/Route-53-Resolver configuration-read units, EventBridge and audit-log assumptions, price-table/model/currency versions, bounded monthly/hourly range, disclosure time, and 15-minute expiry. Existing registered source keys are seller resources not created by W3, so their storage key-month is explicitly excluded while W3-attributable verification and decrypt requests remain included. No AWS resource is created. |
| `POST /connections/{connection_id}/profile-runtime/authorize` | Require the current source-key-set version, standing-cost receipt ID, and explicit `cost_acknowledged=true`; atomically persist actor/time/event, source-key-set hash, and receipt hash, then expose only the exact bound template/upgrade instructions. The template takes the exact registered key ARNs as one closed parameter, generates the task/verifier policies and immutable broker-version `W3_SOURCE_KEY_ARNS_CANONICAL_JSON` from that same value, and emits only their set hash to the verifier receipt. A missing, stale, replayed, or differently bound acknowledgement fails closed. ai.market still never deploys or mutates the stack. |
| `POST /connections/{connection_id}/profile-runtime/verify` | Require the bound runtime-cost acknowledgement, then invoke only the immutable runtime-verifier alias with the closed verification envelope below. Verify the exact stack/template, cluster-to-CMK binding, broker/verifier aliases, role/policy split, task-definition and image digests, control-resource settings, private subnets/routes/security-group egress/endpoint rules, exact DNS Firewall walled-garden association/rules/domain-list/redirection/fail-mode hash, and absence of source-read or mutation authority. Persist only the closed hashed verification receipt. It never creates or changes AWS resources. |
| `GET /connections/{connection_id}/objects` | Owner-only bounded `ListObjectsV2`/`ListObjectVersions` discovery. Require `prefix` within the connection's non-root prefix, `version_mode=current|versions`, `limit<=100`, and an opaque server-bound cursor. Return only owner-visible key, version/ETag, size, last-modified, and extension-only format candidate; never read a body or expose another seller's existence. |
| `POST /cloud-object-selectors` | Accept 1–10 exact object bindings returned by discovery for one verified connection/runtime. Re-list and atomically freeze encrypted key identities, version/ETag, size, runtime source-key-set hash, discovery cursor/version mode, ordered selector hash, and selector version. Reject missing, changed, foreign, root-prefix, duplicate, stale source-key-set, or body-dependent input. The immutable selector ID is owner-only. |
| `POST /profile-jobs/estimates` | Accept one verified runtime, its acknowledged standing-cost receipt, immutable selector ID, and quota profile. Persist and return a short-lived immutable marginal-cost receipt binding seller, connection, runtime, standing-receipt/source-key-set hashes, selector hash, region, fixed task allocation, quotas, retry assumption, bounded Fargate/Lambda/S3-request/S3-storage-byte-duration/S3-in-region-transfer/EC2-cross-AZ-transfer/KMS/Secrets-Manager/EventBridge/Route-53-Resolver-DNS-Firewall-query/task-and-audit-log/interface-endpoint units, regional price-table version, estimate-model version, currency, bounded low/high estimate, disclosed timestamp, and expiry. DNS Firewall query units include queries caused by following approved CNAME/DNAME chains. No job or task is created. |
| `POST /profile-jobs` | Accept one verified connection/runtime, immutable selector ID, quota profile, current estimate-receipt ID, and explicit `cost_acknowledged=true`. In one transaction verify every binding, persist acknowledgement actor/time and receipt hash, freeze parser/image/schema versions, create `queued`, and enqueue control work. A stale, replayed, differently bound, or unacknowledged estimate fails closed. |
| `GET /profile-jobs` | List only the owning seller's jobs with bounded pagination and allowlisted state/runtime/created-before filters. Return the same safe summary fields as the single-job route and no selector object identities, provider errors, or evidence payload. |
| `GET /profile-jobs/{job_id}` | Return owner-visible state, bounded progress counters, safe failure code, evidence reference when successful, and no provider raw error or source content. |
| `POST /profile-jobs/{job_id}/cancel` | Move a queued job directly to `cancelled`, or record `cancel_requested` and invoke broker stop for a live task. A completed result wins only if it committed before the cancel transaction. |
| `GET /profile-evidence/{evidence_id}` | Return the normalized evidence schema in section 9 only to the owning seller. It is not public and is not sent to allAI in W3. |

Discovery pagination is stable only for the connection, prefix, version mode, and snapshot window encoded into the opaque cursor. A cursor cannot widen the prefix or change modes. `current` returns the current version/ETag; `versions` requires the separately enabled `ListBucketVersions` permission and returns explicit version IDs without delete markers. Empty, foreign, deleted, changed, or truncated results reveal no cross-seller information. Object identifiers are confidential operational metadata: they are encrypted or access-controlled like connection scope, excluded from profile evidence/allAI/logs, and never exposed to another seller or buyer.

There is no seller retry or expiry mutation route. The single permitted infrastructure retry is an internal state transition under section 8 and never accepts changed input; expiry is a deadline-driven terminal transition. `GET /profile-jobs` and `GET /profile-jobs/{job_id}` expose those safe states, while an expired evidence ID is uniformly absent after payload deletion. Contract tests must exercise those semantics rather than inventing retry/expiry endpoints.

Before invoking the verifier, ai.market generates a 128-bit random nonce and atomically inserts its SHA-256 hash as `pending` under a unique `(seller_id, connection_id, runtime_version, nonce_hash)` constraint in the durable control database; a duplicate reservation fails before invocation, and a lost response is retried only with a fresh nonce while the original reservation remains pending until expiry. The runtime-verification call carries the closed canonical envelope `seller_workspace_profile_runtime_verify.v1` with exactly: `schema_version`, `operation=verify_runtime`, `seller_id`, `connection_id`, `expected_runtime_version`, `expected_stack_id_hash`, `expected_template_digest`, `expected_broker_alias_arn_hash`, `expected_verifier_alias_arn_hash`, `expected_cluster_arn_hash`, `expected_control_key_arn_hash`, `expected_cluster_control_key_binding_hash`, `expected_source_key_set_hash`, `expected_task_definition_arn_hash`, `expected_image_digest`, `expected_network_hash`, `expected_dns_firewall_hash`, `nonce`, `issued_at`, and `expires_at`. It has no job, selector, quota, parser, or result fields. The verifier resolves stack/network resources only from exact stack membership. It reads the exact published broker-version configuration, parses `W3_SOURCE_KEY_ARNS_CANONICAL_JSON`, recomputes its canonical lowercase SHA-256 set hash, and requires equality with `expected_source_key_set_hash`, which ai.market derived from the encrypted owner-bound registration; it never receives the raw ARN array from ai.market. It recomputes the cluster-to-key, source-key-policy, network, and DNS-firewall hashes from live configuration, rejects unknown fields, expiry, clock skew over 60 seconds, a resource outside the exact tagged stack/registered set, or any expected/observed mismatch, and returns only the receipt defined in section 6.3 with `nonce_hash`. The seller verifier is stateless: it validates nonce shape, issuance, expiry, and clock skew, and covers the nonce hash in the receipt; durable reservation binding and single-use enforcement belong only to ai.market. On a valid response, one transaction locks the matching unexpired `pending` reservation, verifies every seller/connection/runtime/nonce and receipt binding, recomputes the receipt hash, atomically writes that hash and `consumed`, and only then persists the verified runtime. A concurrent, second, stale, differently bound, or already terminal response fails closed; invalid responses become `rejected`, and cleanup turns untouched expired reservations into `expired`.

Every broker invocation instead carries `seller_workspace_profile_broker_request.v1` with exactly: `schema_version`, `operation=start|reconcile_start|poll|cancel`, `seller_id`, `connection_id`, `runtime_version`, `source_key_set_hash`, `job_id`, `attempt`, `task_arn`, `request_sha256`, `job_deadline`, `input_hash`, `selector`, `quota_profile`, `parser_version`, `image_digest`, `evidence_schema_version`, `cost_estimate_receipt_hash`, `cost_acknowledgement_event_id`, `price_table_version`, `estimate_model_version`, `currency`, `issued_at`, and `expires_at`. `task_arn` is JSON null for `start|reconcile_start` and the ai.market-decrypted exact ARN for `poll|cancel`; ai.market first requires its hash to equal the immutable attempt row, while the broker requires the ARN to belong to the exact cluster and validates its seller/connection/job/attempt tags with `DescribeTasks(include=["TAGS"])` before further ECS action. `start` may create the request only when absent. `reconcile_start` is a fresh, normally expiring invocation allowed only for an already-created exact request, the same immutable attempt, and `now < job_deadline`; it exact-key reads and validates the original request before replaying the deterministic ECS token. The create-only task request uses `job_deadline`, not the short broker-invocation expiry, as its source-read expiry. All immutable fields other than operation/invocation timestamps must match the attempt; changed parameters conflict. The broker rejects unknown fields, invocation expiry, clock skew over 60 seconds, a conflicting replay, an input-hash or request-hash mismatch, a selector outside the verified prefix, stale/mismatched cost authority, a poll/cancel task mismatch, or runtime drift.

## 8. Job lifecycle, leases, retries, and concurrency

The durable states are:

`queued -> starting -> running -> validating_result -> succeeded`

and terminal alternatives:

- `queued -> cancelled`;
- `starting|running|validating_result -> cancel_requested -> cancelled`;
- `queued|starting|running|validating_result -> failed`;
- `queued|starting|running|validating_result -> expired` when its hard deadline passes.

Only `succeeded`, `failed`, `cancelled`, and `expired` are terminal. Illegal transitions fail closed and append a redacted audit event. A job input never changes. A retry creates `attempt + 1` under the same job and input hash; it is allowed once, only for launch capacity, transient AWS control-plane, host-interruption-equivalent, or broker transport failures before a valid result commits. Parser rejection, quota exhaustion, schema rejection, permission denial, digest drift, or suspected raw-output leakage is not retried automatically.

The ai.market profile-control worker uses the existing Redis/Celery substrate only for metadata orchestration. It has a new dedicated `seller_workspace_profile_control` queue and a separately deployed worker with concurrency 4, prefetch 1, late acknowledgement, and no source SDK client. The Fargate task, not the Celery child, is the parser. Task state is reconciled only by broker responses over the exact encrypted attempt-to-task binding; seller-account task events are audit evidence, not control input. After `RunTask` acceptance, the broker returns the exact ARN and ai.market atomically stores its encrypted value plus hash before moving `starting -> running`. If a worker/transport failure occurs after request creation and before that commit, redelivery issues a fresh `reconcile_start` envelope for the same immutable attempt. The broker validates the exact persisted request, reconstructs the identical cluster-bound ECS `clientToken` and original parameters, AWS returns the one idempotent task whether the first call occurred or not, and the binding commits without a duplicate. The original short invocation envelope may expire; reconciliation remains available only until the immutable job deadline. No `attempt + 1` may be created while an earlier attempt has an unresolved start reconciliation. A stale Celery delivery may reconcile or poll idempotently but may not create a new attempt.

Timing is exact:

- queue wait: 5 minutes maximum;
- task start: 3 minutes maximum after broker acceptance;
- task wall time: 10 minutes maximum;
- result validation/commit: 2 minutes maximum;
- total job deadline: 20 minutes;
- task stop grace: 30 seconds, consumed inside the 20-minute absolute deadline and therefore from the remaining running/validation time rather than after it;
- broker request/result artifacts: delete immediately after terminal acknowledgement, with one-day lifecycle as fail-safe;
- at most one running job per connection, two running jobs per seller, four queued jobs per seller, and twenty running jobs globally in ai.market control state.

The 20-minute absolute deadline is authoritative and the phase maxima sum to it: five minutes queued, three minutes starting, ten minutes running, and two minutes validating. Every phase records its own deadline capped by the remaining absolute time. Cancellation or expiry during validation prevents commit unless the successful evidence transaction committed first; a later validator, cancel, expiry, or task result becomes a stale no-op with a redacted audit event. No nonterminal state may survive the absolute deadline.

Concurrency is enforced transactionally before launch and rechecked by the broker. Reconciliation may reduce observed capacity after crashes; it may never launch beyond a reserved slot. Provider ambiguity stays `starting` or `running` until reconciled and is never rewritten as a definitive denial.

## 9. Evidence schema and data minimization

The task's encrypted control-bucket upload is the internal closed schema `seller_workspace_profile_task_output.v1`, containing exactly `schema_version`, `semantic_evidence`, `semantic_hash`, bounded `task_observed_usage`, and `task_output_integrity_hash`; it is subject to the same 131,072-byte and canonical-JSON limits, and the broker never returns it verbatim. The only result allowed to cross the broker boundary is canonical UTF-8 JSON, media type `application/vnd.aimarket.seller-profile+json`, at most 131,072 bytes, with no duplicate keys, NaN/Infinity, byte-order mark, comments, unpaired surrogates, unknown fields, or non-canonical numbers. Deterministic semantic evidence and volatile runtime/cost attestation are separate closed-schema objects. The returned top-level schema is `seller_workspace_profile_result.v1`:

```json
{
  "schema_version": "seller_workspace_profile_result.v1",
  "semantic_evidence": {
    "schema_version": "seller_workspace_profile_semantics.v1",
    "input_hash": "sha256-hex",
    "selector_hash": "sha256-hex",
    "parser_version": "semver-or-git-sha",
    "evidence_schema_version": "seller_workspace_profile_semantics.v1",
    "field_token_key_version": "opaque-version",
    "limits": {
      "objects": 10,
      "source_bytes_per_object": 67108864,
      "source_bytes_total": 268435456,
      "rows_per_object": 100000,
      "rows_total": 250000,
      "fields_per_object": 512,
      "field_records_total": 256,
      "field_record_json_bytes_total": 90112,
      "json_depth": 32,
      "decompressed_bytes_total": 536870912
    },
    "observed": {
      "objects_completed": 0,
      "source_bytes_read": 0,
      "decompressed_bytes": 0,
      "rows_examined": 0,
      "truncated": false,
      "truncation_reasons": []
    },
    "objects": [],
    "findings": {
      "pii_classes_present": [],
      "quality_flags": [],
      "warning_codes": []
    }
  },
  "semantic_hash": "sha256-hex",
  "runtime_attestation": {
    "schema_version": "seller_workspace_profile_runtime_attestation.v1",
    "job_id": "uuid",
    "attempt": 1,
    "request_sha256": "sha256-hex",
    "provider": "aws",
    "execution": "ecs_fargate",
    "region": "aws-region",
    "task_definition_digest": "sha256-hex",
    "image_digest": "sha256:hex",
    "task_allocation": {
      "cpu_units": 1024,
      "memory_mib": 4096,
      "ephemeral_storage_gib": 20
    },
    "usage": {
      "started_at": "RFC3339 UTC",
      "finished_at": "RFC3339 UTC",
      "billable_duration_milliseconds": 0,
      "cpu_milliseconds": 0,
      "peak_memory_bytes": 0,
      "attempt_count": 1,
      "fargate_vcpu_milliseconds": 0,
      "fargate_memory_gib_milliseconds": 0,
      "fargate_billable_ephemeral_storage_gib_milliseconds": 0,
      "s3_get_requests": 0,
      "s3_put_requests": 0,
      "s3_delete_requests": 0,
      "s3_list_requests": 0,
      "control_s3_byte_milliseconds": 0,
      "s3_in_region_transfer_bytes": 0,
      "ec2_cross_az_transfer_bytes": 0,
      "kms_generate_data_key_requests": 0,
      "kms_generate_data_key_without_plaintext_requests": 0,
      "kms_create_grant_requests": 0,
      "kms_retire_grant_requests": 0,
      "kms_decrypt_requests": 0,
      "broker_lambda_requests": 0,
      "broker_lambda_gib_milliseconds": 0,
      "secretsmanager_get_secret_value_requests": 0,
      "eventbridge_aws_service_events": 0,
      "eventbridge_target_deliveries": 0,
      "route53_resolver_dns_firewall_queries": 0,
      "cloudwatch_log_ingested_bytes": 0,
      "audit_log_ingested_bytes": 0,
      "interface_endpoint_processed_bytes": 0
    },
    "pricing": {
      "price_table_version": "immutable-version",
      "estimate_model_version": "immutable-version",
      "currency": "ISO-4217"
    }
  },
  "attestation_hash": "sha256-hex",
  "result_integrity_hash": "sha256-hex"
}
```

Each object entry contains only `object_ref` (the deterministic opaque ordinal `o0001`... assigned by immutable selector order), source size, version-binding kind (`version_id` or `etag_size`), format, format metadata below, row-count object `{value, accuracy}` where accuracy is `exact`, `estimate`, or `lower_bound`, positional field records, and safe warning codes. It does not contain bucket, key, account, role, ARN, URL, filename, extension, source timestamp, raw checksum, or provider response.

Every field record contains only:

- `position` and a synthetic structural position such as `f0001` or `f0001.f0002`;
- `field_token`, computed as HMAC-SHA-256 over the normalized full field path with the seller-owned token key, plus key version;
- `physical_type` from the allowlist `null|boolean|integer|decimal|float|string|binary|date|time|timestamp|list|struct|map|unknown`;
- `nullable_observed`;
- `non_null_count`, `null_count`, and `distinct_band` (`0|1|2_10|11_100|101_1000|gt_1000|unknown`);
- `length_band` for string/binary values (`0|1_16|17_64|65_256|257_4096|gt_4096|not_applicable`);
- zero or more `pii_class` enums (`email|phone|postal_address|person_name|government_id|financial|health|precise_location|credential|other_sensitive`) and a confidence band (`low|medium|high`); and
- safe quality flags such as `all_null`, `mostly_null`, `high_cardinality`, `mixed_physical_types`, `invalid_encoding`, or `truncated`.

Exact field names, keys, values, samples, value hashes, minimums, maximums, quantiles, regex matches, snippets, and free-text parser messages are prohibited. Counts are non-negative integers and must reconcile with rows examined. Because the HMAC key belongs to the one-to-one connection runtime, a field token is comparable only within the exact `(seller_id, connection_id, field_token_key_version)` scope. A different connection or key version must produce an unlinkable token even for the same normalized path; W3 makes no seller-wide cross-connection comparison claim.

Canonical hashes use RFC 8785 JSON serialized as UTF-8. `input_hash` covers the immutable semantic input projection: ordered selector bindings, source-key-set hash, quota profile, parser version, image digest, evidence schema version, and field-token key version; it excludes job/attempt IDs, request timestamps, and cost/runtime telemetry. `semantic_hash` is SHA-256 over exactly `semantic_evidence`, so identical input bytes, bindings, versions, key scope, and quotas produce identical canonical semantic bytes and hash. `attestation_hash` is SHA-256 over `{semantic_hash, runtime_attestation}`. `result_integrity_hash` is SHA-256 over the complete top-level object with only `result_integrity_hash` omitted.

The task uploads the closed semantic object/hash plus bounded task-observed usage. Task CPU and peak-memory fields come from fixed cgroup counters sampled by the supervisor; ECS timestamps and fixed allocation determine Fargate duration units; accepted task/runtime and audit-log byte counts determine log-ingestion units; and `interface_endpoint_processed_bytes` is a conservative model bound from the fixed ECR authentication/manifest control-byte ceiling plus closed request/response/log/KMS/Secrets byte ceilings rather than a claim of per-job provider-meter precision. Fixed image-layer bytes traverse the allowlisted regional ECR S3 layer bucket through the S3 gateway endpoint and feed the explicitly versioned in-region S3 transfer unit, not the interface-endpoint unit. `ec2_cross_az_transfer_bytes` conservatively bounds the subset that may cross an Availability Zone between a task ENI and interface-endpoint ENI, with an explicit versioned zero only where the verified placement/routing model guarantees same-AZ use. `route53_resolver_dns_firewall_queries` is the conservative bounded attempt count for every task-originated Resolver query inspected by the associated foundational rule group, including queries caused by following CNAME/DNAME chains. After the exact task reaches `STOPPED`, the broker recomputes the semantic hash, reconciles task observations with ECS state and the immutable attempt records, and constructs the final runtime attestation from provider timestamps, fixed allocation, verified runtime identity, closed application-operation counters, log-ingestion bytes, bounded DNS/interface-endpoint/cross-AZ units, and the current immutable price-table record, then computes the attestation and result-integrity hashes. The cost counters aggregate at most two attempts and are non-negative, bounded by the quotas and request graph, and contain no identifier or source-derived value. Source/task request reads and broker result/recovery reads feed `s3_get_requests`; request/result writes feed `s3_put_requests`; broker cleanup/absence proof feeds delete/list; request/result size and create-to-delete timestamps feed `control_s3_byte_milliseconds`; selected/control objects plus fixed image-layer bytes feed the explicitly versioned in-region S3 transfer unit (including a zero rate where applicable); S3 SSE-KMS calls feed `kms_generate_data_key_requests`/`kms_decrypt_requests`; Fargate storage feeds `kms_generate_data_key_without_plaintext_requests`, `kms_create_grant_requests`, `kms_retire_grant_requests`, and its decrypts; broker invocation records feed Lambda requests/allocation-duration; the task's one token-key retrieval per attempt feeds Secrets Manager requests; ECS state events and their configured target feed EventBridge units; the closed task DNS request graph feeds DNS Firewall query units; the separate task/audit log groups feed their respective ingestion-byte counters. The runtime-verification receipt separately records its bounded Lambda request/allocation-duration, `DescribeKey`/`GetKeyPolicy`, Route 53 Resolver configuration reads, and other configuration-read units for standing-cost reconciliation; those verifier-only calls are absent from the per-job usage object. Each call is attributed once to its producing principal/operation. It never edits semantic evidence. The broker persists the two subobjects immutably only after every check succeeds. W4 may reference only `semantic_hash`; timestamps, CPU/memory observations, billable duration, region, allocation, request/network/log usage, and price-table provenance never alter it. Golden fixtures pin canonical `semantic_evidence` bytes and `semantic_hash`; runtime tests pin the attestation schema and recomputation, not volatile values.

Field-token input is `seller_workspace_field_token.v1`, a NUL byte, the format enum, then for each path component a one-byte component-kind tag, four-byte unsigned big-endian UTF-8 byte length, and Unicode-NFC component bytes. CSV without a header uses only the ordinal component; headers, JSON keys, and Parquet names are used only inside this HMAC input and are then discarded. The token is lowercase hex HMAC-SHA-256. No unkeyed hash of a name/value is emitted.

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
| Fields/leaves parsed | 512 per object |
| Field records emitted | 256 per job and 88 KiB aggregate canonical JSON, whichever binds first |
| Non-field result JSON | 32 KiB maximum |
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

The 128 KiB result limit is reconciled before serialization: at most 88 KiB is available to canonical field-record arrays, at most 32 KiB to all other semantic and attestation members, and 8 KiB remains reserved for enclosing structure and hashes. The task walks objects in immutable selector order and fields in structural-position order, stopping before either the 256-record or 88-KiB field budget. It emits `truncated=true` with `field_record_count`, `field_record_bytes`, or `result_bytes` as the stable reason. Thus 256 is an upper bound, not a promise of coverage, and a wide record can make the byte budget bind first without ever exceeding 131,072 bytes.

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

Fargate, Lambda, S3/KMS/Logs, Secrets Manager, EventBridge/audit delivery, Route 53 Resolver DNS Firewall, customer-managed-key/secret storage, and required private-interface-endpoint charges accrue in the seller AWS account. Max selected D2=A: the seller pays those bounded AWS-native profiling costs. Before the stack template is exposed, the seller must receive and acknowledge the versioned standing-cost estimate; before each job, the seller must receive and acknowledge its separate versioned marginal-cost estimate. Every mandatory W3-created or W3-invoked seller-account service is included even when the current regional price table assigns an AWS-service event or allowance a zero rate; free-tier allocation is never assumed. W3 introduces no ai.market listing fee, subsidy, credit programme, or alternative funding design.

Technical controls are binding regardless of that decision:

- no service or idle task; one on-demand Fargate task per attempt;
- no Fargate Spot in W3, so interruption behavior and estimates are deterministic;
- the fixed `1 vCPU`/`4 GiB`/`20 GiB` task allocation cannot be overridden;
- 10-minute task and 20-minute job deadlines;
- one automatic infrastructure retry maximum;
- seller/connection/global concurrency and daily/monthly quotas of 20 jobs per seller per day and 100 per seller per rolling 30 days;
- before start, `POST /profile-jobs/estimates` creates the immutable marginal-cost receipt defined in section 7 and references the acknowledged standing-cost receipt. The seller sees selected object count, maximum bytes read, task size, one-minute Fargate billing minimum, maximum runtime, possible retry count, currency, and bounded AWS-cost range; `POST /profile-jobs` requires explicit acknowledgement of that exact current receipt;
- the standing model assumes no free-tier/discount allocation and versions the exact control-key month, field-token secret month, interface-endpoint count/AZ-hours/data rates, DNS Firewall foundational rule-group/association rate, exact custom-domain count and domain-name-month rate, explicit zero Advanced-rule associations, runtime-verifier Lambda request/allocation-duration, source-key count plus `DescribeKey`/`GetKeyPolicy` and Route 53 Resolver configuration-read request units, EventBridge AWS-service-event/target-delivery rates (including an explicit versioned zero where applicable), and task/audit log retention/storage inputs, regional price table, currency, and template lifetime used for its range. The marginal model similarly versions Fargate's one-minute minimum/per-second rules, fixed duration/allocation, attempt count, broker Lambda request/allocation-duration, Secrets Manager retrievals, EventBridge event/delivery units, DNS Firewall inspected-query units including redirection-follow queries, action-specific S3/KMS operation counts, transient control-object byte-duration, explicitly versioned in-region S3 transfer, task/audit CloudWatch ingestion bytes, fixed image manifest/layer bytes, interface-endpoint processed bytes, and possible EC2 cross-AZ transfer bytes. The runtime-verification receipt and job attestation record their separate closed bounded units so every displayed model component and range is exactly recomputable without changing the semantic hash. Registered source keys pre-exist W3, so their storage key-month is not an incremental W3 unit; their verification/decrypt calls are. These are conservative modeled disclosures, not a claim to reproduce taxes, negotiated discounts, credits, or the final AWS invoice;
- every job-scoped resource is tagged only with the byte-for-byte keys `ai-market:seller-workspace`, `ai-market:seller-hash`, `ai-market:connection-hash`, `ai-market:job-id`, `ai-market:attempt`, and `ai-market:runtime-version`. `ai-market:seller-workspace=w3`, `ai-market:seller-hash`, `ai-market:connection-hash`, and `ai-market:runtime-version` are stack-fixed; `ai-market:job-id` and `ai-market:attempt` are dynamic canonical safe values required to equal the validated immutable envelope. No value contains seller email or a source name; the exact set and shapes are shared by broker validation, `RunTask`, tag-on-create authorization, task-namespace IAM conditions, and result acceptance; and
- optional seller-owned AWS Budget alarms may notify or deny later launches, but AWS Budgets is not treated as an instantaneous hard stop. The broker and ai.market quotas are the launch boundary.

A stale/missing price table makes template authorization and profiling unavailable; it never silently estimates zero. Standing and marginal receipts expire after 15 minutes and are single-use for their authorization/job. A template, source-key-set, region, AZ/endpoint count, key/secret/storage/log/Lambda/EventBridge assumption, selector, runtime, quota, task allocation, retry assumption, price-table version, estimate-model version, currency, or bounded-range change requires a new applicable estimate and acknowledgement. No listing fee, ai.market infrastructure surcharge, or billing integration is introduced by W3.

## 12. Cleanup and retention

On success, failure, cancellation, expiry, parser crash, broker timeout, worker death, or task kill:

1. stop or observe termination of the exact task;
2. prevent a late result from committing after a terminal attempt;
3. delete the attempt request and result objects after terminal acknowledgement;
4. use the broker's exact-attempt, maximum-two-key prefix listing to prove both expected keys absent without reading a request body; and
5. retain only redacted audit/provenance and the allowed evidence record.

Fargate destruction removes task memory and ephemeral storage. The one-day S3 lifecycle is a recovery backstop, not proof of immediate cleanup. Control-bucket versioning, replication, Object Lock, inventory exports, access logging with object names, and backup are disabled by the W3 stack so deletion does not create retained copies. CloudWatch task logs contain only allowlisted lifecycle fields and expire after seven days. The product stack creates no Resolver query-log configuration, so source-derived DNS labels cannot become a W3 log stream. CloudTrail, Resolver query logs, and VPC Flow Logs are not W3 product-runtime resources, availability preconditions, or D2 receipt units. Gate 4's synthetic seller-account test harness temporarily creates exact scoped trail/data selectors, synthetic-only Resolver query logging, and ENI/VPC flow logs with bounded destinations/retention and a separately approved test budget, verifies the evidence below, and deletes those harness resources; any seller's pre-existing account audit remains outside W3 and must not contain request/result bodies.

Failed, cancelled, and expired job rows retain redacted state, counters, hashes, and failure code for 30 days. Successful W3 evidence expires after 30 days unless a later approved W4 record references its immutable semantic hash; W3 itself cannot create that reference. Expiry deletes the evidence payload and preserves only event identity, actor, timestamps, decision, hashes, and deletion proof under the existing audit-retention policy.

## 13. Persistence and migrations

One additive Alembic revision creates:

- `seller_workspace_profile_source_kms_key_sets`: seller/connection ownership, immutable version, zero-to-eight canonical key ARNs encrypted under the owner-only application boundary, canonical set hash, AWS account/region, created actor/time, and superseded timestamp. Raw ARNs never enter logs, evidence, allAI, or another seller response;
- `seller_workspace_profile_runtime_verification_nonces`: seller/connection/runtime ownership, nonce hash only, `pending|consumed|rejected|expired` status, issued/expiry/terminal timestamps, optional receipt hash, and terminal outcome. A unique `(seller_id, connection_id, runtime_version, nonce_hash)` constraint provides the one-use reservation; only the transactional `pending -> consumed` path may bind one valid receipt, and rows expire under the existing control-data cleanup job after the receipt window;
- `seller_workspace_profile_runtime_cost_estimates`: seller/connection ownership, source-key-set hash/count, runtime/template digests, region/AZ/endpoint count, control-key/field-token-secret months, explicit exclusion of pre-existing source-key months, endpoint-hour/data, verifier-Lambda, KMS describe/policy-read, EventBridge, and task/audit-log retention/storage units, price-table/model/currency versions, bounded low/high standing range, immutable receipt hash, disclosed/expiry timestamps, and optional authorization ID. The receipt is append-only and single-use;
- `seller_workspace_profile_runtimes`: seller/connection ownership, AWS region, status, optimistic version, encrypted or redacted broker/runtime references, verified task/image/network/role hashes, exact cluster-to-CMK and source-key-set/policy hashes, standing-cost receipt/acknowledgement actor/time/event/hash, token-key version, verified/disabled timestamps;
- `cloud_object_selectors`: seller/connection ownership, immutable selector version, encrypted object identities, version/ETag/size bindings, runtime source-key-set hash, selector hash, created timestamp;
- `seller_workspace_profile_cost_estimates`: seller, connection, runtime and selector ownership, acknowledged standing-receipt/source-key-set hashes, selector hash, region, task allocation, quota profile, retry assumption, bounded Lambda/S3-request/S3-storage-byte-duration/S3-transfer/EC2-cross-AZ-transfer/KMS/Secrets-Manager/EventBridge/task-and-audit-log/interface-endpoint units, fixed image manifest/layer bytes, regional price-table and estimate-model versions, currency, bounded low/high marginal estimate, immutable receipt hash, disclosed/expiry timestamps, and optional consumed job ID. The receipt is append-only and single-use;
- `seller_workspace_profile_jobs`: seller, connection, runtime, selector, cost-estimate receipt, acknowledgement actor/time/event and receipt hash, state, current attempt, input hash, quota profile, parser/image/evidence versions, phase/absolute deadlines, aggregate usage counters, safe failure code, evidence reference, idempotency key, timestamps;
- `seller_workspace_profile_attempts`: same-seller job ownership, attempt number, deterministic ECS client-token hash, full task ARN encrypted with the same versioned application envelope-encryption boundary as selector identities, task-ARN hash, AWS state, launch-response/binding timestamps, per-attempt bounded usage counters, terminal reason, and cleanup timestamps. The plaintext ARN exists in ai.market only in owner-authorized process memory for start/poll/cancel and is never written to ai.market logs/audit, returned to the seller UI, placed in evidence, or sent to allAI; seller-owned AWS audit remains governed by the seller's policy;
- `seller_workspace_listing_evidence`: seller/job ownership, schema versions, canonical semantic and runtime-attestation JSON payloads, semantic/attestation/result-integrity hashes, expiry and deletion timestamps; and
- nullable `profile_job_id` plus owner-preserving composite foreign key/index on `seller_workspace_audit_events`.

Database checks enforce state enums, positive versions/attempts/limits, terminal timestamps, phase deadlines not exceeding the absolute deadline, payload size, hash shapes, at most eight canonical source-key ARNs, unique `(seller_id, connection_id, source_key_set_version)`, unique runtime-verification nonce reservation, unique seller/idempotency operation, unique job/attempt and client-token hash, at most one encrypted task ARN per attempt, one authorization per consumed standing receipt, one job per consumed marginal receipt, one evidence row per successful attempt, and same-seller composite foreign keys. Historical source-key versions may repeat a canonical set hash, while only the current-set no-op rule prevents an unnecessary adjacent duplicate. Audit update/delete triggers remain append-only. Source-key set, selector, standing/marginal estimate, acknowledgement, attempt identity, and successful evidence payloads are immutable; a new template, source-key set, source object, estimate binding, or parser version creates a new applicable row.

The migration inserts no W3 rows, rewrites no W2 row, changes no existing connection status, and touches no `serials`, listing, order, delivery, or `legacy_serial` column/constraint. Downgrade is permitted only before any W3 row exists; otherwise rollback leaves the additive tables inert and flags off rather than destroying audit/evidence.

## 14. Audit and Gate 4 evidence contract

Each lifecycle action appends an ai.market audit event containing actor kind/ID, seller, connection, runtime, source-key-set hash, selector, standing/marginal estimate receipt, job, attempt, operation, prior/new state, input/selector/estimate-receipt/semantic/attestation/result-integrity hashes, applicable cost-acknowledgement actor/time/event, resource version, quota profile, price-table/estimate-model versions, currency, parser/image/task-definition digests, decision, safe outcome/failure code, and redacted evidence reference. It never contains source identifiers outside the owner-only selector store, task credentials, raw AWS errors, source content, field names, values, result-object bytes, or the field-token key.

Gate 4 is conjunctive and must produce one redacted immutable receipt binding:

- exact backend and seller-runtime source commits, built artifacts, image digest, task-definition revision, CloudFormation template digest, and deployed identities;
- default-off master/AWS-profile flags and truthful capability response before and after proof;
- synthetic seller/account/connection/runtime/job IDs and timestamps;
- synthetic Gate 4 harness CloudTrail evidence that ai.market assumed only the connection-control role and invoked only the exact verifier or broker alias required by the requested operation;
- verifier receipt and IAM evidence proving the operation-specific verifier read every required exact-stack configuration, including exact cluster-to-CMK binding, registered source-key set/policies, task/endpoint security-group egress, and exact DNS Firewall VPC association/rules/domain-list/redirection/fail-mode hash, returned only closed hashes/mismatch codes, and could not launch/stop a task, pass a role, mutate infrastructure, read a source/control object, decrypt data, or retrieve a secret value;
- IAM simulation and live positive evidence that the task retrieved only its broker-created request with the exact checksum/KMS key/tags, then uploaded only its exact SSE-KMS result with `PutObject` plus `PutObjectTagging` and the required control-key data-key operations; the broker must validate and delete both artifacts;
- IAM-policy and negative-call evidence that the ai.market connection-control, verifier, and broker roles lack `s3:GetObject`, `s3:GetObjectVersion`, `s3:GetObjectAttributes`, and `s3:GetObjectVersionAttributes` on the source and therefore cannot call source `GetObject`, `HeadObject`, unversioned `GetObjectAttributes`, or `GetObjectAttributes(versionId=...)`; that the task could not read an unselected source object or version, any result, another request/connection, or use wrong/missing tags, checksum, content type, or KMS key; and that request overwrite, result read/delete, out-of-attempt control-bucket listing, ACL, multipart/copy, and every non-allowlisted action were denied;
- start/reconciliation evidence at both crash windows proving an exact existing request is read and fully matched, a changed request fails closed, an expired original invocation is recovered by a fresh pre-deadline `reconcile_start`, the deterministic cluster-bound token returns one exact task, and no unresolved attempt permits a retry;
- `RunTask`/`TagResource`/`DescribeTasks`/`StopTask` evidence that tag-on-create succeeds only through `ecs:CreateAction=RunTask` with the exact allowed keys/fixed values/safe dynamic shapes; standalone tagging and missing/extra/wrong tags fail; only the fixed request-key/checksum bootstrap pair differs from the task definition; the verifier proves the pinned task-definition, immutable broker source-key environment, exact cluster task-namespace/resource-tag conditions, and absence of `ListTasks`; every identity-validating `DescribeTasks` request includes `TAGS`; the broker enforces the exact revision and validates the persisted exact task ARN/hash/image/Fargate-CMK/network/tags before result acceptance or stop; and attempted cross-cluster/task, command, selector-valued environment, role, image, resource, or network overrides fail before ECS action;
- ECS task/event evidence for cluster, task ARN, image digest, exact Fargate ephemeral-storage KMS key, CPU/memory/storage, private ENI, no public IP, start/stop reason, and task destruction;
- endpoint-policy, route, security-group, DNS Firewall, synthetic-only Resolver query-log, and VPC Flow Log evidence that the private task pulled the exact image through the regional `prod-${AWS::Region}-starport-layer-bucket`, resolved and reached only the exact approved source/control/ECR/Logs/Secrets-Manager/KMS names/resources, VPC resolver, S3 managed prefix list, and exact interface-endpoint security group. Positive probes cover every required direct name and full CNAME/DNAME chain. Negative probes prove `NODATA` and no network connection for an arbitrary public domain, an encoded high-entropy/tunneling label under a synthetic attacker domain, ai.market, allAI, a name that redirects to an unapproved target, another S3 bucket/key, unrelated intra-VPC ENI/service, public S3 endpoint, NAT, and internet-gateway destination; fail-mode injection proves DNS resolution blocks when DNS Firewall is unavailable;
- source-read byte counts and frozen ETag/version/size/source-encryption proof, closed per-attempt compute/Lambda/S3/action-specific KMS/Secrets Manager/EventBridge/DNS-Firewall-query/task-and-audit-Logs/interface-endpoint/EC2-cross-AZ usage counters, exact standing/marginal estimate-range recomputation including custom-domain storage and redirection-follow queries, request/result checksum/size/media-type/KMS/tag/schema validation, stable semantic hash plus separately recomputed attestation/result-integrity hashes, exact request/result cleanup timestamps, and bounded exact-attempt absence-list results after deletion;
- canary scans proving raw source rows/cells/names and seeded injection strings are absent from ai.market database, Redis/Celery payloads/results, logs, traces, errors, audit, evidence, and allAI;
- success plus parser error, quota, cancellation, timeout, worker-death, task-kill, stale-result, role-drift, image-drift, and cleanup paths;
- unchanged W2 connection management and unchanged legacy fulfillment evidence; and
- immutable seller-visible standing and marginal estimate receipts, exact acknowledgement actor/time/events and template/job bindings, plus recomputable modeled usage.

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
- two sellers plus foreign connection/runtime/selector/job/evidence IDs for runtime verify, create, owner-scoped list, read, cancel, and evidence read, with uniform non-enumerating denial; the internal retry and scheduler-driven expiry are tested through job GET/list state and do not have mutation endpoints;
- discovery and selector contracts cover owner-scoped prefix confinement, successful connection-root and nested-prefix listing under the exact anchored IAM condition, denial of empty/parent/sibling/widened/root-equivalent/cross-connection prefixes, `current|versions` modes, opaque cursor binding, 100-item pagination, explicit version/ETag freezing, re-list drift, delete markers, duplicate/missing objects, and uniform foreign/absent denial without any body read. A current object overwritten after selector freeze must fail `If-Match`; a matching current ETag/size succeeds; version-mode reads require and revalidate the frozen version ID/size;
- runtime verification covers duplicate nonce-hash reservation under concurrent ai.market transactions, fresh-nonce recovery after a lost verifier response, stateless seller-side nonce shape/issuance/expiry checks across cold starts, nonce-hash receipt coverage, atomic first-response `pending -> consumed` binding, concurrent/replayed receipt rejection, rejected/expired outcomes, exact stack-resource membership, exact cluster `Configuration.ManagedStorageConfiguration` control-key binding, zero-to-eight registered source keys and exact task-policy/key-policy/broker-environment restrictions, mutation/removal/non-canonical broker environment rejection, task/endpoint security-group rules, VPC resolver/S3 prefix-list destinations, exact DNS Firewall rule group/allow-and-block-domain-lists/VPC association/priorities/actions/redirection and `FirewallFailOpen=DISABLED`, plus absence of wildcard allows/extra associations/Advanced rules/forwarding endpoints, every required configuration read, closed receipt hashes/mismatch codes, and explicit denial of every verifier mutation, task-launch, role-pass, source/control-object read, decrypt/data-key, secret-value, or Route 53 Resolver mutation action;
- immutable envelope, fresh `reconcile_start` versus short invocation expiry, idempotency replay/conflict, optimistic version, stale attempt, late result, and terminal-transition tests;
- exact broker alias/external-ID verification and rejection of mutable versions or runtime drift;
- IAM simulation and live synthetic calls for the exact request-read/result-write success path and every forbidden action, including absent `s3:GetObject`, `s3:GetObjectVersion`, `s3:GetObjectAttributes`, and `s3:GetObjectVersionAttributes` grants plus denied source `GetObject`, `HeadObject`, unversioned `GetObjectAttributes`, and `GetObjectAttributes(versionId=...)` API calls by ai.market/verifier/broker roles; broker request reads outside exact identity-matched `reconcile_start`; task source-bucket listing; task access to an unselected object/version, sibling request/result/connection, or control-bucket list; request overwrite; result read/delete; out-of-attempt absence-list prefixes; missing/wrong KMS key, checksum, content type, or tags; and all non-allowlisted S3 actions;
- only the broker-derived request-key/checksum bootstrap pair is accepted; command, selector-valued/arbitrary environment, role, image, resource, and network overrides fail before launch;
- tagged-launch IAM tests require `ecs:RunTask` plus tag-on-create-only `ecs:TagResource`, exact tag keys/fixed values/safe dynamic shapes, and prove standalone `TagResource`, missing/extra/wrong tags, other task definitions, and other clusters are denied. `DescribeTasks`/`StopTask` tests prove the exact cluster task namespace plus stack-fixed resource tags, reject an unrelated/cross-cluster task, and require the broker's persisted exact ARN/hash plus dynamic job/attempt tag equality without `ListTasks`; every identity-validating `DescribeTasks` fixture asserts `include=["TAGS"]` and fails if tags are omitted;
- the verifier validates every pinned task-definition field, immutable broker source-key environment, exact cluster-to-CMK configuration, and exact DNS-firewall hash; broker-side `RunTask` permits that exact revision only, and `DescribeTasks(include=["TAGS"])` validates the persisted exact task ARN, revision, image, returned Fargate ephemeral-storage KMS key, network attachments, and task tags before accepting a result; the task role and task network have no ECS API path;
- crash injection after request PUT/before `RunTask` and after `RunTask` acceptance/before ARN persistence, including after the original invocation expiry, uses fresh pre-deadline `reconcile_start`, exact-key validates the unchanged request, replays the identical cluster-bound ECS token/parameters, recovers and encrypts the same exact task ARN, creates no duplicate or retry while unresolved, and permits exact poll/stop/attestation/cleanup. Changed body/checksum/media/KMS/tags/input/attempt/ARN fail closed, and neither plaintext ARN nor token appears in ai.market/application logs, audit, evidence, UI, or allAI;
- runtime verification rejects a control-key policy missing the exact Fargate `GenerateDataKeyWithoutPlaintext`, constrained `CreateGrant`/`Decrypt`, cluster account/name encryption context, or exact verifier `DescribeKey`/`GetKeyPolicy` statements; rejects broader grant operations or another cluster/account; and separately rejects a correct policy with absent/wrong cluster `FargateEphemeralStorageKmsKeyId`;
- source-key registration/verification covers zero and eight keys, alias/wildcard/duplicate/ninth/cross-account/cross-region/asymmetric/disabled keys, current-set idempotent no-op, A→B→A as three immutable versions with repeated historical set hash, wrong or broadened key policy, stale set hash, template/runtime/selector/attempt/broker-environment binding, S3-managed source success, current/versioned exact registered-key success, and missing/unregistered/different returned SSE-KMS key rejection before body parsing;
- redaction scans seed recognizable synthetic source-key ARNs through registration, authorization/template delivery, immutable seller-local broker configuration, verifier mismatch/error, broker transport, seller-control request creation/reconciliation/cleanup, and task failure paths, then prove those raw ARNs are absent from ai.market-to-broker envelopes, HTTP errors, structured logs, traces, Celery payloads/results, audit, evidence, unencrypted database JSON, result validation errors, and allAI; only owner-authorized encrypted persistence, owner-visible template instructions, immutable seller-local broker configuration, the bounded seller-control request object before cleanup, and seller-account process memory may contain them.

### 16.2 Parsers and hostile inputs

Golden deterministic CSV/TSV, JSON/JSONL, and Parquet fixtures pin canonical `semantic_evidence` bytes and `semantic_hash`. Repeated runs with different job IDs, attempts, timestamps, CPU/memory observations, and duration must preserve that semantic hash while producing separately valid attestation and result-integrity hashes. Tests cover empty input, encodings, quoting, multiline cells, duplicate/missing headers, ragged rows, duplicate JSON keys, heterogeneous objects, Unicode controls, very long scalars, deep nesting, huge numbers, malformed footer/page metadata, every supported Parquet codec, allocation/decompression bombs, formula cells, HTML/Markdown, tool syntax, prompt instructions, URLs, credentials, PII, and source strings copied into exception messages.

Tests prove names/keys/values/min/max/quantiles/samples never appear; field tokens are stable only for the same `(seller_id, connection_id, field_token_key_version)` and differ across connections, sellers, or key versions; counts reconcile; the deterministic 256-record/88-KiB emission order and every size-truncation reason are truthful; and unsupported/archive/external-reference formats fail closed. Fuzz and crash tests run each parser in the same child-process/resource-limit boundary used by the image.

### 16.3 Lifecycle, cleanup, and cost

- success, deterministic parser failure, quota exhaustion, cancellation before launch/during run/during validation, 3-minute start timeout, 10-minute task timeout, 2-minute validation timeout, 20-minute absolute deadline, broker ambiguity, Celery worker death, task SIGTERM/SIGKILL, and one permitted infrastructure retry;
- property-based transitions prove phase deadlines and the 30-second physical stop grace never exceed the absolute deadline, no nonterminal state survives it, physical `STOPPED` occurs by 20:00, and commit-versus-cancel/expiry races during validation have one transactional winner;
- concurrency and 20/day, 100/30-day quotas under races;
- task/request/result cleanup on every terminal path, exact-attempt list proof before/after deletion, denial of sibling/parent/wildcard prefixes, and one-day lifecycle backstop;
- fixed CPU/memory/storage and no override, price-table staleness, exact standing/marginal range recomputation from `price_table_version`, estimate-model version, currency, Fargate one-minute/per-second rules, all-attempt compute and broker/verifier Lambda request/allocation-duration units, action-specific S3/KMS/Secrets Manager counts including Fargate grants/data keys/decrypt/retire and standing-only verifier describe/get-policy/Route-53-Resolver reads, control-object byte-duration and in-region transfer (including an explicit zero rate where applicable), control-key/secret months, DNS Firewall foundational rule-group/association rate, custom-domain count/month rate, query count/rate including CNAME/DNAME follow-up queries and explicit zero Advanced-rule associations, explicit exclusion of pre-existing source-key months, EventBridge AWS-service-event/target units including a versioned zero rate where applicable, endpoint AZ-hours/processed bytes, fixed image manifest/layer bytes, possible EC2 cross-AZ transfer, task/audit CloudWatch ingestion/storage, retry maximum, usage reconciliation, and tag completeness; fixtures vary zero/eight keys, DNS allowlist/redirection size, control-object size/lifetime, image size/placement, and every other input without any undefined, omitted, or double-counted unit;
- standing and marginal estimate/acknowledgement tests cover exact template/source-key-set/count/region/AZ/endpoint/key/secret/DNS-domain-list/rule-group/association/Lambda/KMS-policy-read/Route-53-Resolver-read/EventBridge/S3-storage/transfer/log and selector/runtime/quota/allocation/retry/DNS-query/version/currency bindings, 15-minute expiry, single use, actor/time/event persistence, replay, stale table, template/source-key-set/selector/domain-list change, template withholding without standing acknowledgement, and launch denial without a current marginal receipt;
- task ENI/private route/VPC endpoint/security-group/DNS-Firewall tests positively resolve every exact allowlisted name and complete approved redirection chain, pull the exact digest through the required regional ECR layer bucket, and reach the exact source/control/interface-endpoint resources. They prove `NODATA` plus no connection for arbitrary public DNS, high-entropy encoded labels, ai.market, allAI, unapproved redirection targets, every other S3 bucket/key, unrelated intra-VPC ENI/service, public S3, and internet, and prove `FirewallFailOpen=DISABLED`; and
- request/result length, duplicate-key, checksum, media-type, KMS, tags, schema, unknown-field, counter, provenance, semantic/attestation/result-integrity hash, field-budget, and raw-string rejection before ai.market persistence.

### 16.4 Migration and existing behavior

- Alembic upgrade on empty and W2-populated PostgreSQL databases;
- same-seller composite foreign keys, constraints, append-only audit trigger, immutability, and downgrade-empty/refuse-nonempty behavior;
- all existing W2 Seller Workspace connection tests;
- `tests/test_delivery_endpoints.py`, `tests/test_delivery_guarantees.py`, `tests/test_delivery_service.py`, `tests/test_delivery_webhook_integration.py`, `tests/test_serial_serial_id_contract.py`, `tests/test_serial_service.py`, and `tests/test_source_delivery.py` unchanged; and
- dependency/import scans proving no AIM Data runtime, package, database, serial, tunnel, broker client, or container dependency.

## 17. Acceptance criteria

W3 may pass Gate 3 only when the exact candidate proves all of the following:

1. raw source bytes are read only by one seller-account task role and never enter ai.market;
2. only the bounded canonical semantic evidence plus the separate allowlisted runtime/cost attestation crosses the broker boundary;
3. CSV/JSON/Parquet semantic outputs and hashes are deterministic, size-limited, value-free, and injection-inert, while volatile attestation cannot perturb them;
4. every permission is role-separated and negative-call tested;
5. every job is owner-bound, immutable, quota-bound, idempotent, cancellable, and terminally cleaned;
6. worker/task death cannot leak bytes, duplicate a launch, exceed concurrency, or commit stale evidence;
7. seller cost exposure, including the closed DNS Firewall, is bounded, disclosed, tagged, measured, and recomputable, and arbitrary recursive DNS/tunneling is denied;
8. all public, AWS publish/delivery, R2, W4/W5, and AIM Data runtime capabilities remain unavailable;
9. additive migrations preserve all W2 rows and constraints; and
10. the complete unchanged `legacy_serial` test selection passes with no authority fallback or migration.

Gate 4 additionally requires the complete live synthetic evidence in section 14 on the exact reviewed/deployed identities. Customer data or a customer account is never acceptable test material.

## 18. Recorded Max product decisions

Max recorded both choices through authenticated directive event `127c8533-5f58-4b87-a8fe-3a81469d64a1`. No builder or reviewer may reinterpret or broaden them.

### D1 — May exact source field names leave the seller account?

**Decision: A.** Exact CSV headers, JSON keys, Parquet field names, and all other source field names remain inside the seller's AWS account. ai.market may receive only the bounded connection/key-version-scoped tokens, positions, types, counts/bands, classifications, and other approved value-free metadata defined by this specification. Any later W4 disclosure contract requires separate explicit authorization.

### D2 — Is seller-paid AWS execution the intended commercial experience?

**Decision: A.** The seller pays the bounded AWS-native profiling costs. Before execution, W3 shows a versioned cost estimate and requires explicit seller acknowledgement. W3 introduces no ai.market listing fee, subsidy, credit programme, or alternative funding design.

D1 and D2 are resolved only for this W3 Gate 1 candidate. Gate 2 and build dispatch remain blocked until the complete CC/GLM/DeepSeek panel authorized by event `b756003d-6d8c-4835-8c36-dc53a6f97ce1` independently approves the exact resulting digest.

## 19. Source references

- AWS ECS Fargate task definitions and networking: <https://docs.aws.amazon.com/AmazonECS/latest/developerguide/fargate-tasks-services.html>
- ECS `RunTask` idempotency and effective token lifetime: <https://docs.aws.amazon.com/AmazonECS/latest/developerguide/ECS_Idempotency.html>
- ECS `DescribeTasks` tag inclusion: <https://docs.aws.amazon.com/AmazonECS/latest/APIReference/API_DescribeTasks.html>
- ECS tag-on-create authorization with `ecs:TagResource` and `ecs:CreateAction`: <https://docs.aws.amazon.com/AmazonECS/latest/developerguide/supported-iam-actions-tagging.html>
- ECS identity-policy task/cluster examples: <https://docs.aws.amazon.com/AmazonECS/latest/developerguide/security_iam_id-based-policy-examples.html>
- AWS ECS task roles: <https://docs.aws.amazon.com/AmazonECS/latest/developerguide/task-iam-roles.html>
- AWS ECS task-execution role: <https://docs.aws.amazon.com/AmazonECS/latest/developerguide/task_execution_IAM_role.html>
- Amazon ECR private endpoint and regional S3 layer-bucket requirements: <https://docs.aws.amazon.com/AmazonECR/latest/userguide/vpc-endpoints.html>
- Fargate ephemeral-storage security: <https://docs.aws.amazon.com/AmazonECS/latest/developerguide/security-fargate.html>
- Fargate customer-managed ephemeral-storage key: <https://docs.aws.amazon.com/AmazonECS/latest/developerguide/fargate-create-storage-key.html>
- ECS cluster managed-storage configuration: <https://docs.aws.amazon.com/AmazonECS/latest/APIReference/API_ManagedStorageConfiguration.html>
- ECS task-state events: <https://docs.aws.amazon.com/AmazonECS/latest/developerguide/ecs_task_events.html>
- S3 prefix policy conditions: <https://docs.aws.amazon.com/AmazonS3/latest/userguide/amazon-s3-policy-keys.html>
- S3 API permission mapping, including the `s3:GetObject` requirement for object attributes: <https://docs.aws.amazon.com/AmazonS3/latest/userguide/using-with-s3-policy-actions.html>
- Route 53 Resolver DNS Firewall operation, rule ordering, redirection inspection, and fail mode: <https://docs.aws.amazon.com/Route53/latest/DeveloperGuide/resolver-dns-firewall-overview.html>
- Route 53 Resolver DNS Firewall walled-garden construction: <https://docs.aws.amazon.com/Route53/latest/DeveloperGuide/resolver-dns-firewall-getting-started.html>
- Route 53 Resolver DNS Firewall pricing: <https://aws.amazon.com/route53/pricing/>
- AWS Budgets limits and actions: <https://docs.aws.amazon.com/cost-management/latest/userguide/budgets-managing-costs.html>
