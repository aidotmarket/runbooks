# BQ-DATA-VERIFICATION-EVERYWHERE-S1791: Gate 1, run data verification for gateway sellers and cloud (AWS S3 / Cloudflare R2) sellers (R2)

**Author:** Vulcan, S1791, 2026-10-02. **Authority:** Max, 2026-10-02 21:11 CEST: "I want to have this available for customers who host on aws and cloudflare. I also want to be able to run this with the new gateway." Event Ledger `c01b34a7` (dedupe `s1791-data-verification-everywhere`). Standing Max principle (project record): ai.market must never read or profile seller data.
**Build record:** Living State `build:bq-data-verification-everywhere-s1791`.
**Review:** full panel (GLM, DeepSeek, codex2; current panel per Max `d0a534e6`), unanimous. This is a Gate 1 design, a set of named amendments to frozen specs (§10), and a CORE amendment (§11). All pass together or none passes.

## R2 fold log (R1 on `ed934021`: GLM REQUEST_CHANGES, DeepSeek REQUEST_CHANGES, codex2 REVISE)

| Finding | Change in R2 |
| --- | --- |
| GLM 1 (HIGH): AWS invoke right sits on a role that can read objects | AWS trigger removed. Every cloud runner now **pulls** signed work outbound (E5, §5); ai.market gains no new right in the seller's account and the delivery role is untouched. |
| DeepSeek F4: no consent gate at invoke time | Pull model (DeepSeek's own stated remedy) plus consent-bound, nonce-fresh, rate-limited specs that the runner logs in the seller's environment (E6). |
| GLM 2 (HIGH), DeepSeek F2: badge wording changes frozen S1590 §5 without saying so | §10.1 is an explicit amendment of S1590 §5 with exact per-runner attestation and disclaimer text, and legacy wording kept for legacy records. |
| GLM 3, DeepSeek F3, codex2 1 (HIGH): rename/drop map alters `column_names[]` | Removed. The scanner always reports the exact source schema; if the gateway's rename/drop map touches a file in scope, verification of that listing is **refused before the quote** (E7). The §6 manifest is unchanged in shape and meaning. |
| GLM 4: cloud source identity and commitments unspecified | §6 defines source binding, typed locator/object/content preimages, canonical order, mutation refusal and listing-version parity for `gateway_listing`, `s3_listing` and `r2_listing`, modelled on the directory-root amendment. |
| codex2 2: runner location put into the frozen `connector_type` | Runner location comes from the registered runner record, never from `connector_type`. The connector/source-kind literals that must widen are listed exactly as a CORE S3 item (§10.3). |
| codex2 3, GLM 9: egress rule contradicts S3/KMS reads | §5.4 separates seller-cloud service calls from marketplace traffic and names every allowed destination. |
| codex2 4, DeepSeek Q3: commitment-key separation overclaimed | §6.4 states purpose separation only; no unlinkability claim. |
| GLM 5, codex2 Q2, DeepSeek F6: CORE text not fully verbatim; probe not covered; roster | §11 gives exact old→new for every changed line, covers the probe, and cites `d0a534e6` for the codex2 seat. |
| GLM 6: R2 trust model "equivalent" is not a decision | §5 is one runner control plane for AWS and R2 (identity, registration token, image binding, revocation), packaging-independent. |
| GLM 7: S1717 and legacy claims false | E9 supersedes S1717 by this decision; it does not claim S1717's acceptance was met. Legacy acceptance item removed (legacy AIM Data is already archived). |
| DeepSeek F1: gateway D1 and GATE2 §7.3 reopened silently | §10.2 is an explicit amendment of gateway D1 and GATE2 §7.3. |
| DeepSeek F5: scan-spec key for the gateway | §4: delivered and rotated over the signed control channel. |
| GLM 8, codex2 packet: builder verification, budget | §13. |
| codex2 BETTER: golden oracle | Acceptance 4 uses the approved S1590 golden reports as the oracle, plus cross-runner equality. |
| DeepSeek Q4: simpler path via gateway + mountpoint-s3 | Answered in E3. |

## 1. Why

Seller-initiated data verification (S1590) is live in production with both switches on, and no seller has ever completed a run (`data-verification-seller-journey.md` §A: 0 quotes, 0 epochs). Its only runner was legacy AIM Data, which is archived (`aim-data.md`). Neither of the places sellers actually are today can run it: the gateway does three things only (CORE v9.22 line 59; gateway D1), and S1590 §2 item 1 limits coverage to AIM Data-reachable sources, which excludes Seller Workspace cloud sellers. Verification therefore has no runner at all today.

## 2. Decisions

- **E1. The product stays the S1590 product.** Seller-initiated and optional; free probe then quote; price 2x measured allAI token cost bounded USD 1-25 on the existing pay-in rails; complete-or-refuse coverage; publish-all-or-decline; withdraw/supersede; S1396 corpus feed; the §6 manifest field set and every field's meaning. The only product-visible change is the attestation and disclaimer wording, amended explicitly in §10.1. Backend quote, payment, Stage B narrative, badge, withdraw and corpus code are reused; §8 lists every backend change.
- **E2. ai.market never reads the data; the scan runs where the data is.** For every runner the scan executes inside the seller's own environment and only the §6 manifest (and the S1590 probe aggregates) crosses. ai.market holds no new right to read, list, head or invoke anything in a seller's cloud account because of this feature. W3 (ai.market-side profiling) stays parked and out of scope.
- **E3. One scanner, three runners.** The deterministic Stage A scanner (S1590 §3.1) is written once, in Go, as a package in `aidotmarket/aim-data-gateway` (Apache 2.0, reproducible, cosign-signed, SBOM). It is shipped as: (a) the gateway's fourth function; (b) the **AWS verifier**, a container-image AWS Lambda function plus a schedule, deployed into the seller's own AWS account by a CloudFormation quick-create stack; (c) the **R2 verifier**, deployed into the seller's own Cloudflare account, packaging chosen by spike S-R2 (§12); if no packaging meets E2, E5 and §5, R2 listings show "Data verification for Cloudflare R2 is coming soon" and Max's Cloudflare ask is reported as not yet met. *Simpler alternative considered (DeepSeek R1):* a cloud seller can already run the gateway with `mountpoint-s3`/`rclone` (gateway D6) and verify through it; that remains available, but it requires installing and exposing a gateway, which the cloud journey deliberately avoids ("the seller never installs AIM Data", `seller-workspace-cloud-listing-delivery.md`), so it does not meet Max's ask on its own.
- **E4. Honest wording per runner.** The attestation keeps the S1590 authorship-versus-execution distinction exactly: ai.market authored the code; the seller's own environment executed it. §10.1 gives the exact text.
- **E5. Every runner pulls; nothing pushes into the seller.** The gateway already receives work over its outbound signed control channel. The AWS and R2 verifiers do the same: on a schedule (default every minute, seller-adjustable) they call `api.ai.market` outbound, authenticated by their runner key, and ask for pending signed work. With no pending work the call returns empty. ai.market cannot start, change or reach a runner; it can only leave signed work for it.
- **E6. Consent is bound to every spec and visible to the seller.** ai.market issues a probe or scan spec only after the seller's in-session confirmation (S1590 owner authorization); the spec carries that `owner_authorization_id`, its `accepted_at_utc`, the listing version and a fresh nonce, all under the scan-spec signature. The runner refuses a spec that lacks them, is older than 24 hours, reuses a nonce or authorization, names another listing version, or exceeds a fixed local limit (10 specs per listing per day). Every spec received, accepted or refused is written to the runner's own log in the seller's environment (gateway audit log; CloudWatch Logs; Cloudflare logs), so the seller can see exactly what ai.market asked for and when. Stated honestly: the runner is ai.market-authored code and cannot independently prove the seller clicked; what the design guarantees is that nothing runs without a signed, logged, rate-limited request the seller can audit, that a probe returns only aggregates, and that the seller can remove the runner at any time (§5.5). A seller-held consent key was considered and rejected as complexity without real protection, since the browser code that would hold it is also served by ai.market.
- **E7. Exact schema or no verification.** The scanner reports the exact source column names and every statistic for every column, as S1590 §6 requires. A gateway file whose columns are renamed or dropped by the customer's D9 map is not verifiable: the website refuses the probe for that listing with "Some columns of this data are hidden in your gateway settings, so it can't be verified." No cost is incurred. Cloud runners have no rename/drop map.
- **E8. Runner location is a runner fact.** `verification_runner.kind` (`gateway | aws | r2`) and its scanner version are recorded at registration and shown on the badge; they are never written into `connector_type`.
- **E9. Supersessions, stated plainly.** Legacy AIM Data verification is archived with legacy AIM Data. `build:bq-data-verification-platform-key-distribution-s1717` is closed as **superseded by this design** (its AC-final-b needed a legacy install, which no longer exists); its key-delivery goal is carried by §4 and §5.3. The legacy `install_key_id` path in the backend is deleted when the gateway runner is live.
- **E10. One new backend concept.** `verification_runner` (kind, owner seller account, gateway id or Seller Workspace connection id, public receipt key and key id, scanner version, image digest, status, last-seen). It replaces the AIM Data install as the addressee of a scan spec.

## 3. Seller journey (all runners)

1. On a published listing the seller chooses **Verify this data**.
2. If the listing's source has no active runner:
   - gateway listing: none needed once the paired gateway reports a scanner-capable version;
   - S3 listing: **Set up the verifier** opens CloudFormation quick-create in the seller's AWS console, pre-filled with the listing's bucket, the scope prefix list, the image digest and a one-time registration token (§5.2);
   - R2 listing: the S-R2-chosen one-click equivalent.
3. **Free probe:** the seller confirms; ai.market queues a signed probe spec; the runner picks it up, checks E6 and returns only the S1590 probe aggregates; the website shows the depth class or refuses.
4. **Quote and pay:** unchanged S1590 §10; the paid scan spec carries the new owner authorization.
5. **Scan:** the runner picks up the signed scan spec, checks E6, binds the exact pinned objects (§6), traverses completely, and returns the §6 manifest and signed receipt.
6. **Narrative, publish or decline, badge, corpus:** unchanged.

## 4. Gateway runner (fourth function)

- New control-channel message types `scan_spec` (ai.market to gateway) and `scan_report` (gateway to ai.market), signed both ways and logged like every other message. `aim-gateway preview --verify <file-id>` prints the exact manifest that would be sent.
- The scan-spec public key is delivered in the pair response alongside the permission and listing keys and rotated by a signed instruction exactly as gateway D5 rotates those keys. It is never set by hand.
- The gateway generates a separate verification receipt key and a verification commitment key on its volume and registers the receipt public key over the control channel.
- Scope: the files of the active listing version, by (gateway id, file id, SHA-256). A spec naming a file outside the offer ceiling or the offerable set is refused.
- E7 check: the gateway reports whether any in-scope file is affected by the rename/drop map; ai.market refuses the probe if so, and the gateway refuses the spec independently.
- Size: Gate 2 reports measured lines and dependencies against gateway D11 and justifies any excess.

## 5. Cloud runner control plane (AWS and R2, independent of packaging)

### 5.1 Runner identity and keys
At first start the runner generates, inside the seller's account: a runner signing key (AWS: a KMS asymmetric signing key created by the stack, Ed25519 if KMS offers it in the seller's region, otherwise ECDSA P-256, recorded in the existing `signature_algorithm` field; `kms:Sign` granted only to the runner's execution role; R2: a Cloudflare secret), and a commitment/HMAC key (AWS Secrets Manager; R2 secret). Neither leaves the seller's account. The receipt signature (S1590 `install_key_id`) uses the runner key.

### 5.2 Registration
- When the seller clicks Set up, ai.market mints a registration token: 256-bit random, single use, valid 30 minutes, bound to (seller account, connection id, listing id, runner kind, expected image digest). Only its hash is stored.
- On first start the runner calls `POST /api/v1/verification-runners/register` with the token, its runner public key, a signature by that key over the request, its image digest and scanner version. ai.market accepts only if the token is unused and unexpired, the digest is on the announced allowlist, and the connection belongs to the token's seller. The response carries the scan-spec public key, which the runner pins; rotation is a spec-key-signed instruction delivered through the work call.
- A replayed, expired or mismatched token is refused and logged; a second runner for the same connection replaces the first only after the seller confirms on the website.

### 5.3 Work exchange
- `POST /api/v1/verification-runners/{id}/work` (runner-signed request, nonce, timestamp) returns zero or one signed spec, at most 64 KiB. `POST .../report` returns the manifest or a fixed-enum terminal error, at most the existing report size bound.
- Image binding: every runner request states its image digest; ai.market refuses work to a digest not on the allowlist, so an old or altered runner gets no specs. ai.market cannot change the runner's code or configuration; updating means the seller updates the stack.

### 5.4 Network
- Marketplace traffic: HTTPS to `api.ai.market:443` only, with ai.market's certificate chain pinned in the runner.
- Seller-cloud service calls the runner needs: AWS S3 (the pinned objects only), KMS (`Sign` on its own key), Secrets Manager (its own secret), CloudWatch Logs; R2 equivalents via bindings. Nothing else.
- AWS enforcement default: the execution role allows exactly those actions on exactly those resources, so even a modified runner cannot read beyond scope. Optional strict network profile (documented, seller's choice): the function in a seller VPC with S3/KMS/Secrets/Logs VPC endpoints and egress only through the seller's own egress control to `api.ai.market`. Gate 2 decides whether the strict profile is the default after costing it.

### 5.5 Revocation
The seller can delete the stack or the R2 deployment, or click Remove verifier on the website. Remove marks the runner revoked; its next work call is refused and the runner logs it. Deleting the stack ends the runner outright.

## 6. Source binding (all runners)

Modelled on `BQ-DATA-VERIFICATION-S1590-DIRECTORY-ROOT-AMENDMENT.md`. The registered root is the **version-pinned object set** of the listing's active version at spec issue; the spec names `listing_version_id` and that version's manifest hash.

### 6.1 Pinned identity per kind
- `gateway_listing`: per file (gateway id, file id, SHA-256, size), from the listing version (gateway GATE2 manifest contract).
- `s3_listing` / `r2_listing`: per object (provider, bucket, key, provider version id or else ETag, size), from the Seller Workspace listing version (`seller-workspace-cloud-listing-delivery.md` evidence rule: "Provider version ID or ETag where available, sizes, manifest hash, and selector version").

### 6.2 Typed preimages (NUL-framed, UTF-8 NFC; HMAC with the runner's commitment key)
- `artifact_locator_commitment`: `<kind>\0<root id>\0<manifest_hash_hex>`, where root id is the gateway id for `gateway_listing`, or `<bucket>` for cloud kinds.
- `objects[].object_id`: `object\0<kind>\0<root id>\0<member identity>\0<member sha256_hex>`, where member identity is the gateway file id, or `<key>\0<version id or etag>` for cloud kinds.
- `content_sha256`: SHA-256 over the concatenation, in ascending canonical member-identity order, of `u64-be(len(identity)) || identity || u64-be(size) || sha256(member bytes)` for every member (directory-root §1.3(c) framing).

### 6.3 Binding before and during reading
Before any fact, the runner checks every pinned member: same size, and same version id or ETag for cloud kinds (a HEAD by the runner in the seller's account), same SHA-256 for gateway files. During the fact read it hashes each member and requires the hash to stay constant across both passes. Any mismatch, missing member or member outside the pinned set ends the scan `FAILED_VOIDED` with no partial report and no charge capture (S1590 terminal rules). Report ordering is ascending `object_id`, as today.

### 6.4 Key purposes
The commitment key is separate from the receipt key (S1590 §6 requirement) and, in the gateway, separate from the D9 file-id secret. This is purpose separation so one key's compromise or rotation does not affect the other; it is **not** a claim that ai.market cannot associate a report with a listing file, because ai.market names the listing version in the spec and later sees content hashes.

### 6.5 Parity
As in directory-root §2.6: the scanned set equals the delivered set exactly when `scan.listing_version_id == order.purchased_version_id`. The badge names the version it covers.

## 7. Security boundaries

- No runner sends cell values, rows, samples, min/max, top values, paths, object keys, bucket names, error strings or free text (S1590 §6 prohibited list); no runner accepts free-form commands.
- ai.market gains no right in a seller's cloud account. It can leave signed, consent-bound work; the runner checks it, logs it in the seller's environment and rate-limits it (E6).
- The §6 reconstruction release gate in S1590 is re-run on the Go scanner's output before first release.
- Residuals disclosed, as in S1590 §5: a seller controls the environment and could alter the runner; curated sources and post-scan replacement cannot be detected.

## 8. Backend changes

1. `verification_runner` table, registration, work and report endpoints (§5), token minting, digest allowlist, revoke.
2. Scan-spec issuer addresses a runner; spec gains `listing_version_id`, `manifest_hash`, `source_kind` (S1590 directory-root precedent) and the E6 consent binding.
3. Report validator: the widened literals in §10.3 only; everything else unchanged.
4. Badge copy per §10.1; runner kind and scanner version shown from `verification_runner`.
5. Website: the setup step, E7 refusal message, Remove verifier.
6. Delete the legacy AIM Data install addressing once the gateway runner is live (E9).

## 9. Acceptance (Gate 1 level)

1. Gateway seller (Max's Sentineldata tester): probe, quote, paid scan, publish from the website; badge shows the gateway wording; nothing set by hand on the gateway.
2. S3 seller: one-click setup, probe, quote, paid scan, publish. CloudTrail in the seller account shows object reads only by the runner's execution role, and **no** call by any ai.market principal for the whole flow.
3. R2: same as 2, or the honest "coming soon" if S-R2 fails.
4. Oracle: for the approved S1590 golden fixtures, the Go scanner reproduces the approved golden fact payloads; for shared fixtures, all three runners' manifests are byte-identical except `install_key_id`, timestamps, commitments and the §10.3 source-kind literal.
5. Consent: a spec with a missing, unsigned, expired, replayed, over-limit or wrong-version authorization is refused by every runner, and every spec appears in the runner's log in the seller's environment.
6. Mutation: changing one pinned object after publish voids the scan before any fact or capture.
7. E7: a gateway file with a renamed or dropped column cannot be probed; nothing is charged.
8. Network: each runner's traffic, captured in a test account, contains only §5.4 destinations; marketplace-bound bodies contain only approved control and report data.
9. Revocation: Remove verifier stops work at the next poll; a deleted stack registers nothing.
10. Runbooks: `data-verification-seller-journey.md` rewritten; `aim-data-gateway.md` and `seller-workspace-cloud-listing-delivery.md` updated.

## 10. Named amendments to frozen specs (voted with this Gate 1)

### 10.1 S1590 Gate 1 §5 attestation and disclaimer (and GA amendment's binding wording)
Records completed by legacy AIM Data keep their original §5 text. New records use, by `verification_runner.kind`:

- Attestation: "On [scan date and time], at the data owner's authorization and expense, ai.market directed a scan of the seller-designated source for this listing inside the owner's own [self-hosted AIM Data gateway | AWS account | Cloudflare account]; the structural facts below were computed by ai.market-authored open-source scanner code (version [x.y.z]) executed in that owner-controlled environment, and the findings are published unedited."
- Disclaimer: "This is a seller-published, point-in-time scan of what the seller-designated source exposed to the scanner in the owner's own [self-hosted AIM Data gateway | AWS account | Cloudflare account] on [scan date]; the source may change at any time, and this is not a continuing audit, warranty, compliance certification, or guarantee that data delivered later will match or remain available, accurate, complete, or unchanged. Verification does not assess data accuracy, legality, or fitness for any purpose."

Every other §5 sentence, the "does not attest" list, the badge title `Scan findings — [UTC date]`, and the GA amendment's requirement that the authorship-versus-execution caveat is prominent remain unchanged. Golden public-copy tests cover all three runner strings and the legacy string.

### 10.2 Gateway S1741 Gate 1 D1 and Gate 2 §7.3
- D1 becomes "**Four functions only**", adding "(d) when the seller requests it, it runs a data verification probe and scan in place under BQ-DATA-VERIFICATION-EVERYWHERE-S1791 and sends only the approved aggregate findings".
- GATE2 §7.3's message-type lists gain `scan_spec` (server to gateway) and `scan_report` (gateway to server); the pair response gains the scan-spec public key (§4).

### 10.3 S1590 §6 / connector contract (CORE S3 item)
No field is added, removed or repurposed. Exactly these literal sets widen, for the new kinds only: `connector_type` gains `aim_gateway`, `aws_s3_verifier`, `r2_verifier` (describing how the scanner accesses the source, not where it runs; runner location stays in `verification_runner`); `connector_version` gains the matching `-v1` values; the scan spec's source kind gains `gateway_listing`, `s3_listing`, `r2_listing`; and, only if S-AWS finds Ed25519 unavailable in KMS, `signature_algorithm` gains `ecdsa-p256-sha256`. Existing values keep their meaning.

## 11. CORE amendment (exact text)

Base: CORE v9.22, `ai-market-backend@a3a8a754bfc2f6b3cd876e4a1771134bf9dcd27a:docs/core/CORE.md`. Exactly two blocks change. The §3 communications marker text is untouched. The boot kernel's P7 is regenerated by the normal projection and checked against its character budget at application (E-03/E-04).

### 11.1 Lines 3-4 become lines 3-5

Old (lines 3-4, verbatim):

```text
**Version:** 9.22
**Last Updated:** 2026-09-23 (S1738 — follow-up fixes after a Council review: a gate's first review of a design, spec or build still goes to all three voters; a fix that only answers findings is confirmed by the voter or voters who raised them, and goes back to all three only when it changes the design or answers a HIGH or CRITICAL finding. Max's direct decision, superseding the Council for this amendment under §5; Event Ledger 936e32cb; Max approved the exact wording.)
```

New (lines 3-5):

```text
**Version:** 9.23
**Last Updated:** [APPROVAL DATE] (S1791 — the AIM Data gateway gains a fourth function: a seller-requested data verification probe and scan run in place, sending only signed aggregate findings. Unanimous Council under the panel Max set in d0a534e6: GLM [GLM RESPONSE ID], DeepSeek [DEEPSEEK RESPONSE ID], codex2 [CODEX2 RESPONSE ID]; Max approved the exact wording, Event Ledger [MAX APPROVAL EVENT ID].)
**Prior:** 9.22, 2026-09-23 (S1738 — follow-up fixes after a Council review: a gate's first review of a design, spec or build still goes to all three voters; a fix that only answers findings is confirmed by the voter or voters who raised them, and goes back to all three only when it changes the design or answers a HIGH or CRITICAL finding. Max's direct decision, superseding the Council for this amendment under §5; Event Ledger 936e32cb; Max approved the exact wording.)
```

The existing `**Prior:**` lines (from current line 5 on) follow unchanged. Placeholders are filled mechanically: `[APPROVAL DATE]` is Max's E-02 approval date as YYYY-MM-DD; each response id is the final approving response file's timestamp id (format `YYYYMMDD-HHMMSS-NNNNNN`); the event id is Max's E-02 approval event. Nothing else is substituted.

### 11.2 Line 59 fragment

Old (exact substring, occurs once):

```text
It does three things only: it describes the seller's data where it sits to ai.market with structural metadata only (never data values, and nothing identifying until the seller chooses to send it), plus a public sample only when the seller explicitly chooses one; it serves purchased files directly to the buyer through a single delivery endpoint that the seller's own IT exposes, admitting only download permissions signed by ai.market, each for one file of one order; and it reports each delivery to ai.market for billing and payout.
```

New:

```text
It does four things only: it describes the seller's data where it sits to ai.market with structural metadata only (never data values, and nothing identifying until the seller chooses to send it), plus a public sample only when the seller explicitly chooses one; when the seller requests it, it runs a data verification probe and, once the seller has paid, a full verification scan in place under an ai.market-signed scan specification, sending only the approved aggregate findings and never data values; it serves purchased files directly to the buyer through a single delivery endpoint that the seller's own IT exposes, admitting only download permissions signed by ai.market, each for one file of one order; and it reports each delivery to ai.market for billing and payout.
```

No CORE text is added for the cloud runners: they are ai.market website software running in the seller's account that send only approved metadata, so CORE S1/P2 already govern them, and ai.market gains no access into the seller's systems (E2, E5). R1 voters agreed (DeepSeek Q2, codex2 Q2); GLM raised no objection to this point.

## 12. Spikes Gate 2 must close

- **S-R2:** the shared scanner on R2 in a seller-owned Cloudflare account as (a) Cloudflare Containers and (b) a WebAssembly Worker, on the Parquet and large-CSV fixtures: cold start, CPU and memory limits, largest object completely traversable, scheduled pull support, secret storage, and whether marketplace egress can be pinned to `api.ai.market`. Pick one or defer R2 (E3).
- **S-AWS:** Lambda's 15-minute limit against complete-or-refuse: a deterministic multi-invocation traversal with a merged canonical fingerprint, or a depth class that refuses sources too large for one invocation; Ed25519 availability in KMS; and the cost of the strict network profile (§5.4).
- **S-Size:** gateway lines and dependencies with the scanner added.

## 13. Builder verification for this candidate

Documentation-only candidate. Run at the candidate SHA in the runbooks checkout: `python3 scripts/index.py && python3 scripts/check.py` (both must report all runbooks indexed and checked); `git diff --check <base>..<candidate>`; and a byte check that each §11 "Old" block occurs exactly once in `git show a3a8a754bfc2f6b3cd876e4a1771134bf9dcd27a:docs/core/CORE.md`. Results are in the review request. Reviewer budget: 20 tool turns.
