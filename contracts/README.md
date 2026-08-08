# Deployed gateway contract pins

This directory is the reviewed, local trust boundary for the gateway contract
validator. It deliberately contains no mutable `latest` convention.

The validator expects `deployed-tool-contract.pin.json` with exactly these
keys:

```json
{
  "artifact_path": "contracts/deployed/<artifact_sha256>.json",
  "artifact_sha256": "<SHA-256 of RFC 8785 artifact payload>",
  "audience": "runbooks-ci",
  "envelope_sha256": "<SHA-256 of exact canonical signed-envelope bytes>",
  "handler_sha": "<full 40-hex deployed handler commit>",
  "issuer": "ai.market-gateway-deployer",
  "pin_format_version": "1",
  "policy_revision": "<exact deployed policy/config revision>",
  "proxy_release_identity": "<exact deployed proxy release identity>",
  "trust_store_path": "contracts/deployed-tool-contract.keys.json",
  "trust_store_sha256": "<SHA-256 of exact trust-store bytes>"
}
```

The trust store has `trust_store_format_version`, `keys`, and `revoked_kids`.
Each key has exactly `kid`, `algorithm` (`Ed25519`), an unpadded 32-byte
`public_key_base64url`, `issuer`, `audiences`, `valid_from`, `valid_until`, and
nullable `revoked_at`. Rotation is represented by overlapping valid key rows;
revocation is explicit. The pin binds the exact trust-store bytes.

The artifact file is the canonical JSON signed envelope described by
[`schemas/deployed_tool_contract.schema.json`](../schemas/deployed_tool_contract.schema.json).
Its Ed25519 signature covers the RFC 8785 canonical bytes of:

```json
{"artifact": {"...": "..."}, "signature_metadata": {"...": "..."}}
```

The envelope itself is also canonical JSON. Both its exact byte digest and the
canonical artifact-payload digest are pinned. Binary64 values use RFC 8785's
ECMAScript number presentation; integers are limited to I-JSON's exact safe
range. Non-finite values and unsafe integers fail closed.

Artifact format version `3` admits only the one-way runbook-first lifecycle.
There is no signature-valid legacy lifecycle profile. Every tool descriptor
contains both its exact
`inputSchema` and exact `outputSchema`, plus server-owned `effect` metadata:

- `read_only` has a `none` default risk;
- a whole-tool `mutating` classification explicitly selects `low`, `medium`, or
  `high` risk; and
- `action_discriminated` names one input enum, classifies every advertised
  action exactly once, and makes any unrecognized/future action fall through to
  `mutating` / `high`.

The effect object and every action also state whether backend exact-argument
binding is required. Every declared high-risk mutation and the high-risk
action-discriminator fallthrough uses `exact_arguments`, but callers never pass
an `action_receipt` and tools never return `ACTION_CONTEXT_REQUIRED`. The
trusted shared execution boundary records intent before execution and the
provider-observed terminal result afterward, bound to session, actor, handler,
canonical arguments, component, policy revision, action identity, and exact
non-default remote candidate when applicable. Background work remains pending
until its supervisor records a terminal outcome. Explicit low/medium mutations
are not silently promoted to high risk.

The top-level `runbook_lifecycle` projection is also signed. It names the exact
plan and close tools, one-call automatic delivery, exact-retry behavior,
physical legacy absence, typed outcomes, no-prior-write claims, binding class,
  receipt fields, obligation transaction, action evidence, exact-source fetch,
  complete obligation pagination, verifier runtime identity, and one-way
  cutover proof. The version-3 target field contract is:

- `kd_session_plan` accepts no runbook path, reference, consultation, gap,
  attestation, waiver, synthesis, or desired-impact field. Its required
  `PLAN_ACCEPTED` result conditionally requires both the accepted plan receipt
  and complete runbook context. The context carries exact activation, catalog,
  manifest, inventory and response identities, singleton `complete: true`, an
  exact byte count bounded to 40,000 bytes, delivery digest, complete paged
  OPEN-obligation subjects, and a ranked record for every objective. Each
  candidate carries stable section/source identity, path, heading, bounded
  excerpt/digest, rank, policy lane, advisory precedence, and match evidence.
  The accepted receipt binds plan revision, session, instance, request/context
  digests, activation, time, and immutability. The
  contract asserts byte-identical response content for an unchanged lost-response
  retry and rejection of a changed request.
- `kd_session_close` accepts no runbook decision, impact, evidence, exit,
  discharge, or waiver object. Its `COMMITTED` outcome conditionally requires
  both `close_receipt` and `obligation_outcomes`. `close_receipt` requires
  singleton `COMMITTED` status, transaction ID, close-request ID, request and
  evidence-freeze digests, session ID, commit time, signature identity, and
  singleton `immutable: true`. Obligation outcomes bind the canonical obligation,
  status, occurrence result, and coverage result when present.
- `runbook_context_fetch` is read-only and returns exact pinned section or
  full-runbook pages with byte bounds, page and whole-source digests, total
  length, and a stable continuation cursor.
- Target delivery is rollout-ready only with automatic delivery required,
  legacy inputs absent, a positive bounded context limit, unconditional
  public signed cutover-status validation, and every high-risk/action
  publication binding. The signed cutover proves legacy runtime, local
  authority, and fallback absence, database freeze, and `new_path_only`
  rollback. Close uses a typed transaction-scoped receipt and the atomic backend
  obligation/outbox transaction.
- `runtime_identity` separately binds the exact verifier tree, artifact
  manifest, dependency lock, Python runtime, verified module origins, and
  workflow. Hashing a contract label is not an artifact identity.

A pre-cutover artifact that names caller-authored `runbook_consultation`,
`runbook_refs`, `runbook_impact`, legacy `runbook_exit`, local authority, or the
old selection/action-context round trips is schema-invalid even if its old
signature verifies. It cannot be selected before or after one-way activation.
Conversely, a target projection over legacy tool schemas, minimal
discriminator-only outputs, an optional startup guard, or an unbound high-risk
mutation is invalid rather than a readiness waiver.

Runbooks that state a current Council roster or role in §C, §D, §E, §H, or §I
must include one `yaml deployed-contract-roles` fenced block. The complete
machine-readable shape is documented in
[`runbook_tools/deployed_contract.py`](../runbook_tools/deployed_contract.py).
The member sets and contract digest must match the pinned artifact exactly (list
order is not treated as role semantics). Prose is never mined to invent a
roster or certified merely because a correct block exists elsewhere: any
current role claim outside the block is emitted as
`UNCHECKED_CURRENT_ROLE_CLAIM` and fails validation.

§E gateway calls use the structured `tool(arg=value, ...)` form at the start of
an endpoint or after a top-level `then`, `plus`, `+`, or `;` composition
boundary. This keeps SQL functions and shell substitutions out of the gateway
namespace. A wholly non-gateway endpoint may be explicitly prefixed
`external::`; a mixed endpoint may use `mixed::`. §I tool-call
answers use `tool`, `argument_keys`, and optional literal `argument_values`.
Placeholders may defer value checks but not unknown keys or missing required
keys. Other explicitly executable gateway examples use a fenced
`yaml deployed-contract-call` object (or list):

```yaml
tool: state_request
argument_keys: [action, key]
argument_values:
  action: get
  key: <server-owned-key>
```

Balanced, non-nested `catalog:historical` spans are excluded before this
comparison. Malformed historical markers fail, and current §E/§I forms remain
in scope.

Run the validator with:

```sh
python -m runbook_tools.deployed_contract --repo .
```

To make target lifecycle readiness a blocking deployment/rollout check, run:

```sh
python -m runbook_tools.deployed_contract \
  --repo . \
  --artifact-only \
  --require-runbook-lifecycle-ready
```

Without the readiness flag, JSON and text reports still expose `READY` or
`NOT_READY` plus deterministic reason codes. With the flag, any `NOT_READY`
artifact exits 1 with `RUNBOOK_LIFECYCLE_NOT_READY`. Missing trust material
remains an infrastructure exit 2.

Until bootstrap deployment publishes and the reviewed pin vendors a signed
artifact, the command exits 2 with `CONTRACT_PIN_MISSING`. There is no unsigned
or mutable-alias fallback.
