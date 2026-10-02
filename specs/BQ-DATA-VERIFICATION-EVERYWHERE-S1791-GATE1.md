# BQ-DATA-VERIFICATION-EVERYWHERE-S1791: Gate 1, run data verification for gateway sellers and cloud (AWS S3 / Cloudflare R2) sellers (R1)

**Author:** Vulcan, S1791, 2026-10-02. **Authority:** Max, 2026-10-02 21:11 CEST: "I want to have this available for customers who host on aws and cloudflare. I also want to be able to run this with the new gateway." Event Ledger `c01b34a7` (dedupe `s1791-data-verification-everywhere`).
**Build record:** Living State `build:bq-data-verification-everywhere-s1791`.
**Companion CORE amendment:** §9 of this document. The amendment and this design are voted in the same round and neither passes without the other.
**Design authority this builds on (not reopened):** `specs/BQ-DATA-VERIFICATION-S1590-GATE1.md` and its amendments (the product, trust, wire, payment, badge and corpus rules), `specs/BQ-AIM-DATA-GATEWAY-S1741-GATE1.md` / `-GATE2.md` (the gateway), and `seller-workspace-cloud-listing-delivery.md` (cloud sellers).
**Review:** full panel (GLM, DeepSeek, codex2), unanimous. This touches customer data boundaries (CORE S3) and CORE text (H6).

## 1. Why

Seller-initiated data verification (S1590) is live in production with both switches on, and no seller has ever completed a run (`data-verification-seller-journey.md` §A: 0 quotes, 0 epochs). The only place the scan can run is legacy AIM Data, which is frozen and being retired (CORE v9.21; Max 2026-10-01 GO to archive `aidotmarket/aim-data`). Neither of the two places sellers actually are today can run it:

| Seller | Where the data is | Can verify today? |
| --- | --- | --- |
| Self-hosted | Behind the AIM Data gateway | No. The gateway does three things only (CORE P7, gateway D1); verification is not one of them. |
| Cloud | Their own AWS S3 or Cloudflare R2, connected through Seller Workspace | No. S1590 §2 item 1 limits coverage to AIM Data-reachable sources. |
| Legacy AIM Data | Old install | Technically yes, but that product is being archived. |

So, as things stand, verification has no future home. The open platform-key bug (`build:bq-data-verification-platform-key-distribution-s1717`) is about the legacy runner only.

## 2. Decisions

- **E1. The product does not change.** Everything S1590 froze stays as it is: seller-initiated and optional, free probe then quote, price 2x measured allAI token cost bounded USD 1-25 on the existing pay-in rails, complete-or-refuse coverage (§9 there), publish-all-or-decline, the dated badge and its disclaimer, withdraw/supersede, the S1396 corpus feed, and the exact §6 wire manifest. The backend verification service, quote, payment, Stage B narrative and badge code are reused unchanged except where §5 says.
- **E2. ai.market never reads the data. The scan always runs where the data is.** Max's standing principle: ai.market must not read or profile seller data (the AWS profiling work W3 stays parked and is not revived here). For every seller type the scan runs inside the seller's own perimeter, and only the §6 manifest crosses. This holds S1, P2 and P8 without exception.
- **E3. One scanner, three runners.** The deterministic Stage A scanner (S1590 §3.1: signed spec in, §6 manifest and signed receipt out) is written once, as a library inside `aidotmarket/aim-data-gateway` (Go, open source, Apache 2.0, reproducible build, cosign-signed). It is packaged three ways:
  - **(a) Gateway runner:** a fourth gateway function, `verify`, in the gateway binary.
  - **(b) AWS runner:** the same scanner as a container-image AWS Lambda function, deployed into the seller's own AWS account by a CloudFormation quick-create link.
  - **(c) R2 runner:** the same scanner deployed into the seller's own Cloudflare account. The packaging (Cloudflare Containers versus a WebAssembly build in a Worker) is decided at Gate 2 by spike S-R2 (§8); if neither can meet E4, R2 verification ships later and the website says so honestly.
  The scanner's phase-2 describe code (gateway D9) and verify code share parsers (CSV/TSV, JSON Lines, Parquet) so the two never disagree about a file's columns or row count.
- **E4. Same honesty everywhere.** Each runner meets every S1590 trust anchor (§3.3 there) that applies to it, and the badge says where the scan ran: "Scanned on [UTC date] by the open-source ai.market scanner vX.Y.Z in the seller's own environment ([self-hosted gateway | AWS account | Cloudflare account])". No runner may claim more than the S1590 point-in-time claim. Hardware attestation stays deferred, as S1590 §3.3 already says.
- **E5. Who triggers the scan, and how bytes stay put.**
  - **Gateway:** unchanged gateway rules. The signed scan spec arrives over the existing signed control channel. The gateway still has no inbound path besides the door, makes no new outbound connection, and reads only what the customer mounted.
  - **AWS:** the seller's existing Seller Workspace connection role gains exactly one permission, `lambda:InvokeFunction` on the one verifier function the stack created, which ai.market calls with the signed spec. The function's own execution role (created by the seller's stack, not trusted by ai.market) has read-only access to the selected scope and nothing else, and no network egress except to `api.ai.market:443` (Gate 2 picks the enforcement). The function returns only the §6 manifest and receipt as the invoke response. ai.market's role cannot change the function's code or configuration.
  - **R2:** equivalent: ai.market can trigger the seller-deployed runner, cannot change its code, and receives only the manifest.
- **E6. Per-runner signing keys, held by the seller.** The receipt signature key (S1590 §6 `install_key_id`) and the commitment/HMAC key are generated inside the runner's environment and never leave it: gateway volume (a separate verification key alongside the existing D10 identity key), an AWS KMS asymmetric key plus a Secrets Manager secret created by the seller's stack, or the Cloudflare secret store for R2. The public receipt key is registered with ai.market once at deploy or pairing, bound to the seller account and the connection or gateway. The scan-spec signing key is the existing platform scan-spec key; its public half reaches every runner inside the authenticated scan-spec response, as already implemented for S1717 (`data-verification-scan-spec-response-v2`), so no runner needs a key set by hand.
- **E7. Cloud runners are ai.market software, not AIM Data.** The AWS and R2 runners are part of the ai.market website's Seller Workspace feature, branded "ai.market verifier". They are not the AIM Data product and do not change CORE's AIM Data definition. They are optional: a cloud seller who never verifies never deploys anything.
- **E8. Scope and order.** Ship in this order, each releasable on its own: (1) shared scanner library plus the gateway runner; (2) the AWS runner; (3) the R2 runner after S-R2. Legacy AIM Data verification is not extended; it retires with legacy AIM Data. `build:bq-data-verification-platform-key-distribution-s1717` is closed as superseded once runner (1) completes its first production run, because its definition of done (a released install completes a run without hand-set keys) is then met by the gateway.
- **E9. Simplest thing that works.** No new UI outside the existing verification flow on the listing page. No new payment code. No new corpus code. One new backend concept only: a `verification_runner` record (kind `gateway | aws | r2`, public receipt key, owner, connection or gateway id, scanner version, status) that replaces the AIM Data install as the thing a scan spec is addressed to.

## 3. How it works (all runners)

1. The seller opens a published listing and chooses **Verify this data** (existing S1590 entry point, moved to the website for gateway and cloud listings).
2. If no runner exists for the listing's source, the website shows one setup step:
   - gateway listing: nothing to do, the paired gateway is the runner once it reports a scanner-capable version;
   - AWS listing: **Deploy the verifier** opens the CloudFormation quick-create page in the seller's console with the stack pre-filled for the selected scope; the stack registers its public receipt key with ai.market when it finishes;
   - R2 listing: equivalent one-click deployment chosen at Gate 2.
3. **Free probe** (S1590 §9): ai.market sends a signed probe spec to the runner; the runner returns only the probe aggregates; the website shows the depth class or refuses.
4. **Quote and pay** (unchanged S1590 §10).
5. **Scan** (Stage A): signed spec in, complete traversal of the selected scope, §6 manifest plus signed receipt out. Bytes never leave the runner's environment.
6. **Narrative and decision** (Stage B, publish/decline, badge, corpus): unchanged.

## 4. Gateway runner (fourth function)

- New control-channel message pair `scan_spec` (ai.market to gateway) and `scan_report` (gateway to ai.market), signed both ways like every other gateway message, and logged in the gateway's local audit log like every other outbound body. `aim-gateway preview --verify <file>` prints the exact manifest that would be sent, without sending it.
- Scope is the files of the listing version being verified, looked up by (gateway id, file id, SHA-256) exactly as permissions are (gateway D9/D12). A spec that names a file outside the offer ceiling is refused.
- Column names in the manifest pass through the customer's existing rename/drop map (gateway D9), so verification never reveals a column the customer chose to hide in describe. The manifest otherwise keeps the S1590 §6 field list exactly; locator and object commitments use the verification commitment key, not the D9 file-id secret, so the two identifiers cannot be joined by ai.market.
- Budget: the scanner adds to the gateway's D11 size target; Gate 2 states the measured line and dependency count and justifies any excess (shared parsers mean the addition should be small).
- Version: ai.market issues scan specs only to gateways at or above the announced minimum scanner version.

## 5. Backend changes

- `verification_runner` (E9) and its registration endpoints: gateway runners register over the control channel; AWS/R2 runners register once from their deployment, authenticated by a one-time registration token minted when the seller clicks Deploy.
- The scan-spec issuer addresses the spec to a runner instead of an AIM Data install. Quote, payment, Stage B, badge, withdraw and corpus code are reused.
- For AWS: the Seller Workspace connection template gains the single invoke permission (E5) as a new template version; existing connections keep working and are offered the update only when the seller first chooses Verify.
- Badge wording gains the runner location (E4). This is a wording change inside the existing frozen badge structure and is reviewed here.

## 6. Security and trust boundaries

- No runner, in any environment, sends cell values, rows, samples, min/max, top values, paths, object keys, bucket names or error strings (S1590 §6 prohibited list), and no runner accepts free-form commands.
- ai.market can trigger a scan; it cannot read objects through the runner, change runner code, widen scope, or receive anything but the manifest.
- The seller can delete the runner at any time (delete the stack, unpair the gateway, remove the R2 deployment); ai.market then marks the runner revoked and issues no further specs.
- The §6 reconstruction release gate in S1590 still applies to the shared scanner and is re-run once on its output, because the code is new.

## 7. Acceptance (Gate 1 level)

1. A seller with a paired gateway (Max's Sentineldata tester) runs probe, quote, paid scan and publish from the website; the badge appears; nothing was hand-configured on the gateway.
2. A seller with an S3 Seller Workspace listing deploys the verifier from one click, runs probe, quote, paid scan and publish; CloudTrail in the seller account shows only the verifier reading objects; ai.market's role has no object reads during the scan.
3. Same as 2 for R2, or an honest "coming soon" on R2 listings if S-R2 fails E4.
4. The manifest from all three runners for the same fixture files is byte-identical apart from runner-specific identity fields (`install_key_id`, `connector_type`, timestamps, commitments).
5. Network capture on each runner shows no outbound traffic except to `api.ai.market:443` (gateway, R2) or the Lambda invoke response (AWS).
6. Deleting a runner revokes it within one control-channel cycle; a later spec is refused.
7. Legacy AIM Data verification still works until legacy retirement and is then removed with it.
8. Runbook `data-verification-seller-journey.md` rewritten for the three runners; `aim-data-gateway.md` and `seller-workspace-cloud-listing-delivery.md` updated.

## 8. Spikes Gate 2 must close

- **S-R2:** run the shared scanner against R2 in a seller-owned Cloudflare account, as (a) Cloudflare Containers and (b) a WebAssembly Worker, on the Parquet and large-CSV fixtures; report cold start, CPU/memory limits, maximum object size for complete traversal, and whether outbound can be restricted to `api.ai.market`. Pick one or defer R2.
- **S-AWS:** the Lambda 15-minute limit against the S1590 complete-or-refuse rule: either a deterministic multi-invocation traversal with a merged canonical fingerprint, or a depth class that refuses sources too large for one invocation. Also the outbound restriction mechanism for the function.
- **S-Size:** measured gateway line and dependency count with the scanner added.

## 9. CORE amendment (exact text)

Base: CORE v9.22, `ai-market-backend@a3a8a754bfc2f6b3cd876e4a1771134bf9dcd27a:docs/core/CORE.md`. Only these lines change. The boot kernel's P7 is regenerated from the amended text by the normal projection.

**Line 59, old fragment:**

```text
It does three things only: it describes the seller's data where it sits to ai.market with structural metadata only (never data values, and nothing identifying until the seller chooses to send it), plus a public sample only when the seller explicitly chooses one; it serves purchased files directly to the buyer through a single delivery endpoint that the seller's own IT exposes, admitting only download permissions signed by ai.market, each for one file of one order; and it reports each delivery to ai.market for billing and payout.
```

**Line 59, new fragment:**

```text
It does four things only: it describes the seller's data where it sits to ai.market with structural metadata only (never data values, and nothing identifying until the seller chooses to send it), plus a public sample only when the seller explicitly chooses one; when the seller requests and pays for it, it runs a data verification scan in place under an ai.market-signed scan specification and sends only the signed aggregate findings, never data values; it serves purchased files directly to the buyer through a single delivery endpoint that the seller's own IT exposes, admitting only download permissions signed by ai.market, each for one file of one order; and it reports each delivery to ai.market for billing and payout.
```

**Lines 3-5, version header:** `**Version:** 9.23`; `**Last Updated:** [APPROVAL DATE] (S1791 — the AIM Data gateway gains a fourth function: a seller-requested, seller-paid data verification scan run in place, sending only signed aggregate findings. Unanimous Council: GLM [ID], DeepSeek [ID], codex2 [ID]; Max approved the exact wording, Event Ledger [ID].)`; the current Version/Last Updated pair moves down to a new `**Prior:**` line above the existing ones, unchanged.

No other CORE text changes. In particular the AIM Data "IS NOT" line already holds ("Never sends data values or file bytes to ai.market other than the seller-chosen public sample"), and the cloud runners need no CORE text because they are an ai.market website feature that keeps S1/P2 (E2, E7). Reviewers are asked to confirm or reject that last judgment explicitly.

## 10. Out of scope

- ai.market-side profiling or sampling of seller data (W3), in any form.
- Any change to the S1590 manifest field list, price, payment, badge structure or corpus rules.
- Sources other than gateway-mounted files, S3 and R2.
- Hardware attestation of runners (deferred, as in S1590).
- Extending legacy AIM Data.

## 11. Questions for the panel

1. Is E5's single `lambda:InvokeFunction` permission on ai.market's role the simplest safe trigger, or should the AWS runner instead pull signed specs outbound (no new trust from the seller's account to ai.market, at the cost of polling)?
2. Does E7 hold: can the cloud runners live under the ai.market website without CORE text, or must CORE say something about ai.market code running in a seller's cloud account?
3. Is the §4 separation of the verification commitment key from the gateway D9 file-id secret necessary, or does it add a key for no gain?
4. Is anything here more than the simplest design that meets Max's two asks?
