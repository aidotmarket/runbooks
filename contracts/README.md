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

Artifact format version `2` separates cryptographic integrity from runbook
lifecycle rollout readiness. Every tool descriptor contains both its exact
`inputSchema` and exact `outputSchema`, plus server-owned `effect` metadata:

- `read_only` has a `none` default risk;
- a whole-tool `mutating` classification explicitly selects `low`, `medium`, or
  `high` risk; and
- `action_discriminated` names one input enum, classifies every advertised
  action exactly once, and makes any unrecognized/future action fall through to
  `mutating` / `high`.

The effect object and every action also state whether an exact-argument context
receipt is required. In a target lifecycle artifact, each declared high-risk
mutation and the high-risk action-discriminator fallthrough must use
`exact_arguments`. Its tool input exposes an optional, satisfiable non-empty
string `action_receipt`; making that token required would prevent the first
stage from obtaining context. Its result
has required `outcome` including `ACTION_CONTEXT_REQUIRED`; and its
`action_context` schema requires `context_id`, the canonical-argument SHA-256,
session, component, policy revision, and expiry. Explicit low/medium mutations
are not silently promoted to high risk, which prevents plan or close from
requiring a circular action receipt before their own protocol can run.

The top-level `runbook_lifecycle` projection is also signed. It names the exact
plan and close tools, protocol family, deployed delivery modes, typed outcomes,
no-write claims, binding class, receipt fields, obligation transaction, and
exact-argument action-receipt capability. The version-2 target field contract is:

- `kd_session_plan` accepts optional `consultation_ids` and `gap_ids` as unique
  arrays of non-empty strings, so the first-stage request remains callable. Its required
  `outcome` includes `RUNBOOK_CONTEXT_SELECTION_REQUIRED` and `PLAN_ACCEPTED`.
  The output schema conditionally requires the corresponding payload for each
  outcome; the condition must be the exact required outcome discriminator and
  the complete outcome-plus-payload instance must be satisfiable. Merely
  declaring the discriminator values or hiding an impossible condition behind
  `if` is insufficient.
  `selection_set` requires selection-set identity, catalog SHA and digest,
  singleton `complete: true`, exact byte count bounded to 40,000 bytes,
  delivery digest, and per-objective
  candidate/gap records. Each candidate carries a consultation ID, runbook and
  stable-section identity, path, heading, bounded excerpt and digest, rank, and
  match evidence. `accepted_plan_receipt` requires the plan revision, session,
  instance, objective digest, work type, selection-set ID, catalog SHA, request
  digest, and delivery digest.
- `kd_session_close` accepts an optional, satisfiable object `runbook_impact`.
  Its required `outcome` includes
  `COMMITTED`, which conditionally requires both `close_receipt` and
  `obligation_outcomes`. `close_receipt` requires `COMMITTED` status, transaction ID,
  close-request ID, request digest, session ID, commit time, and
  singleton `immutable: true`. The receipt status is singleton `COMMITTED`, not
  an enum that also admits a non-committed state. `obligation_outcomes` requires an obligation ID, status,
  and occurrence-recorded result for every returned row.
- Target delivery is rollout-ready only with
  `candidate_delivery_mode=required`, `legacy_consultation_mode=reject`, and a
  positive bounded candidate limit. The plan IDs bind session, instance,
  objectives, work type, revision, catalog, and excerpt digest. Close uses a
  typed transaction-scoped receipt and the atomic backend obligation/outbox
  transaction. Action receipts are one-use, expiring, and bound to canonical
  tool arguments, session, component, and policy revision.

An honestly labeled `legacy` projection still requires real input and output
schemas and effect metadata. It names caller-authored `runbook_consultation`,
legacy `runbook_exit`, no typed selection/committed receipt, and no action
receipt protocol. A valid signature over that truth is integrity-valid but its
deterministic lifecycle assessment is `NOT_READY`; a signature is never rollout
evidence by itself. Conversely, a `target` projection over legacy tool schemas,
minimal discriminator-only outputs, or an unbound high-risk mutation is an
invalid contract rather than a readiness waiver.

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
