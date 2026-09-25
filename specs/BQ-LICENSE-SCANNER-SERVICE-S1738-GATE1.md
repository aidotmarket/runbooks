# BQ-LICENSE-SCANNER-SERVICE-S1738 Gate 1 design specification

**Status:** Proposed Gate 1 design; no Council approval, implementation, merge, or deployment is asserted.

**Build Queue entity:** `build:spec-license-scanner-service-s1738`.

**Business summary for Max:** Custom seller licence uploads currently cannot pass malware
inspection because the production backend has no ClamAV executable. A ClamAV process inside each
backend image is too slow and memory hungry. This proposal puts one continuously running scanner
beside the backend on Railway's private network, keeps uploads closed when scanning is
unavailable, and tests clean and EICAR files before any release. It adds an ongoing service
cost; the estimate and limits below need measurement before rollout.

**Decision authority:** Max's 2026-09-25 option B, Event Ledger `75245973`, directs a dedicated
ClamAV service on Railway private networking and backend `clamd` INSTREAM. This authoring
request supplies the decision and the measurements attributed to Event `b06fc964`; the Event
Ledger records were not independently read in this Gate 1 authoring pass. Council has not
approved this design. PR [#464](https://github.com/aidotmarket/ai-market-backend/pull/464) is
the rejected in-backend-image alternative and was OPEN when inspected on 2026-09-25.

**Source pins:** `aidotmarket/runbooks@b7009e89575ec0cef6b0c5e9c1a19b28848ee43a` (`origin/main`
authoring base); `aidotmarket/ai-market-backend@7643fc8b42a895f90776fd53c9784631ef21d658`
(`origin/main` inspected source). Every backend source citation below names the latter
full SHA. These are source identities, not deployed image identities. The S1656
environment/runbook and official vendor documentation are cited separately.

## 1. Problem and current contract

At the inspected backend pin, `MAX_LICENSE_BYTES` is 1 MiB. `scan_upload_for_malware()` invokes
`clamscan --no-summary -` as a subprocess, sends the upload bytes to stdin, discards process
output and imposes a 30 second timeout. Process absence, timeout and any unexpected return code
raise `LICENSE_MALWARE_SCAN_UNAVAILABLE`; return code 1 raises `LICENSE_MALWARE_DETECTED`
(`aidotmarket/ai-market-backend@7643fc8b42a895f90776fd53c9784631ef21d658:app/services/custom_license_service.py:27-28,68-81`).
The production Dockerfile installs no ClamAV package or signature database in its runtime stage
(`aidotmarket/ai-market-backend@7643fc8b42a895f90776fd53c9784631ef21d658:Dockerfile:43-65`). The reported production
consequence in Event `b06fc964` is that every custom upload fails; this document does not claim
an independently observed live request.

`inspect_custom_license()` validates nonempty size and MIME/filename first, calls the malware
scanner, then rejects secret patterns, extracts and validates text, and rejects prohibited
terms. PDF parsing walks the trailer and refuses active-content keys before text extraction.
Preserve this order and every non-malware refusal
(`aidotmarket/ai-market-backend@7643fc8b42a895f90776fd53c9784631ef21d658:app/services/custom_license_service.py:30-50,90-95,98-125,148-197`).
`store_custom_license()` reads the bounded upload into quarantine, runs inspection through
`asyncio.to_thread`, and only then seeks or writes a document
(`aidotmarket/ai-market-backend@7643fc8b42a895f90776fd53c9784631ef21d658:app/services/custom_license_service.py:200-274`).
No dirty or unscanned bytes may reach the object store or a committed `LicenseDocument`.

`POST /licenses/custom` has the authenticated seller capability check, a fail-closed
10-per-minute rate limiter and the `LISTING_LICENSES_ENABLED` guard. It maps
`CustomLicenseError` to HTTP 422 with the existing code and unexpected failures to HTTP 503
`LICENSE_UPLOAD_UNAVAILABLE`
(`aidotmarket/ai-market-backend@7643fc8b42a895f90776fd53c9784631ef21d658:app/api/v1/endpoints/licenses.py:14-17,31-59`).
Gate 2 should keep the existing API code mapping while making scanner failures consistently
reach `CustomLicenseError`.

The files are **seller-provided public licence terms, not customer data**. Scanning is a
malware/hygiene guard on these terms. This decision does not broaden custody, retention, logging
or access to customer datasets. The scanner should receive only the upload bytes, never buyer
data, seller credentials, object-store credentials or full document text in logs.

## 2. Frozen decision and authority boundary

1. Run `clamd` and `freshclam` in a dedicated Railway service in the same project and
   environment as the backend. The backend sends bytes with `INSTREAM` over the private network.
   Keep one warm signature engine and update its definitions during runtime.
2. Base the service on the official `docker.io/clamav/clamav:stable` image **pinned by OCI index
   digest** `sha256:0e31ce089574268aefa0b543767d66b70240ab51ed49eec53e07f18d5629d817`, resolved
   on 2026-09-25. The observed index included `linux/amd64` manifest
   `sha256:e8388295191bff0893fb889d9415ae975491201c989b205e30c9057b1985d36a`; verify Railway's
   selected architecture and the pulled manifest in Gate 2. The tag is descriptive; the digest
   is the build input. Replace this pin only through a reviewed image-update change with
   vulnerability and smoke evidence. [Official Docker
   image](https://hub.docker.com/r/clamav/clamav), [ClamAV Docker
   manual](https://docs.clamav.net/manual/Installing/Docker.html).
3. Keep the scanner private. Configure no Railway public domain and no public TCP proxy. Use its
   `*.railway.internal` name and TCP 3310 in the backend's
   `LICENSE_CLAMD_HOST`/`LICENSE_CLAMD_PORT` settings. Railway's private network is isolated per
   project environment and carries encrypted interservice traffic. [Railway private
   networking](https://docs.railway.com/networking/private-networking), [TCP
   proxy](https://docs.railway.com/networking/tcp-proxy).
4. Do not turn off malware scanning, return “clean” for scanner errors, raise the old 30 second
   subprocess timeout, increase the upload cap, or alter the rest of the licence inspection
   policy to make this release pass.
5. This is a design approval request. Gate 2 implementation, Railway service creation,
   production spend, feature-flag changes, merge and deployment require their own governed steps
   and evidence. Close PR #464 as superseded after this decision is recorded; do not merge its
   Dockerfile change into the backend.

## 3. Binding service design

### 3.1 Image, process and signature lifecycle

- Deploy the digest-pinned official image as a single scanner service with its default `clamd`
  and `freshclam` daemons enabled. Set `FRESHCLAM_CHECKS=4` for a six-hour update cadence. Keep
  `CLAMAV_NO_CLAMD=false` and `CLAMAV_NO_FRESHCLAMD=false`; require successful initial
  definition load before readiness. The official image runs both daemons by default and exposes
  the update-frequency control. [ClamAV Docker
  manual](https://docs.clamav.net/manual/Installing/Docker.html).
- Persist `/var/lib/clamav` in a scanner-owned Railway volume, so a service restart need not
  re-download the full database. Do not bake signatures during each backend build. Pin the
  volume to this service/environment; restore from upstream definitions, not an unreviewed
  copied database, if it is corrupt. A temporary upstream update outage may use the last
  verified definitions only while age remains within the gate below.
- Set `StreamMaxLength` to **1 MiB** to match `MAX_LICENSE_BYTES`. Leave the application's 1 MiB
  check in place; a daemon size-limit reply still fails closed. Record the exact mounted
  `clamd.conf` and `freshclam.conf` in the Gate 2 scanner infrastructure candidate. Avoid a
  hidden mutable Railway-only config that the S1656 equivalent cannot reproduce.
- Require definitions no older than **48 hours** by their database build timestamp. Read
  `VERSION` and parse/validate its database date, cross-check `freshclam` update status and
  daemon logs. If the date is absent, unparsable, in the future beyond clock tolerance, or older
  than 48 hours, readiness fails and backend scan attempts return
  `LICENSE_MALWARE_SCAN_UNAVAILABLE`; an old but responsive daemon is unavailable for admission.
  Alert at 24 hours so repair can precede refusal. A fresh update attempt alone does not reset
  age.
- Check update status every five minutes for monitoring. `freshclam` runs at its own six-hour
  cadence; monitoring must not trigger repeated upstream downloads. On a definition reload,
  preserve scan availability where the daemon remains healthy. If it blocks, crashes or becomes
  stale, admission fails closed. Record first-load time and reload peak memory before choosing
  final limits.

### 3.2 Resource and cost envelope

- Start one replica with **4 GiB memory limit and 1 vCPU limit**, no scale-to-zero. Set
  `MaxThreads=2` and a backend admission cap of two concurrent uploads per backend replica;
  measure actual CPU, latency and reload peak before increasing either. This is an initial
  ceiling, not a promise that 4 GiB always suffices.
- ClamAV's Docker guidance says the signature engine can consume over 1.2 GiB and briefly
  roughly double during concurrent reload; it recommends at least 3 GiB and prefers 4 GiB. The
  supplied Event `b06fc964` measurement found an in-backend invocation OOM at 768 MiB and pass
  at 1.2 GiB, which does not measure warm-daemon reload headroom. [ClamAV Docker
  manual](https://docs.clamav.net/manual/Installing/Docker.html).
- Railway currently bills consumed RAM at about **$10/GB-month** and CPU at **$20/vCPU-month**,
  plus any volume and egress. A warm 1.2–2 GiB working set implies roughly **$12–$20/month
  RAM**; sustained 0.1–0.5 vCPU adds roughly **$2–$10/month**. A conservative sustained 4 GiB
  plus 1 vCPU envelope is about **$60/month** before plan credit, volume and egress. These are
  order-of-magnitude estimates, not a quote: capture a week of actual Railway metrics and cost,
  including reload peaks, and confirm Max's spend authority before a permanent service. [Railway
  pricing](https://docs.railway.com/pricing/plans), [right
  sizing](https://docs.railway.com/guides/right-size-cpu-memory).
- Alert on memory above 80% of the limit outside reload, OOM/restart, scan latency and queue
  saturation. If reload requires more than the starting cap, return the measured change and cost
  to the owner; do not silently disable signature updates or scanning.

### 3.3 Isolation and trust

- Bind `clamd` to the private listener needed for Railway's internal address and port 3310.
  Verify from the platform settings that no public domain, public TCP proxy or other route
  exposes it. `clamd` TCP has **no built-in authentication or encryption**; Railway's WireGuard
  private network supplies transport protection and project/environment isolation, but does not
  authenticate an individual backend process to `clamd`. [ClamD
  protocol](https://docs.clamav.net/manual/Usage/ClamdProtocol.html), [Railway private
  networking](https://docs.railway.com/networking/private-networking).
- Accept the private network as the initial trust boundary only after inventorying every service
  in that Railway project/environment and confirming no untrusted workload can reach the
  scanner. An internal peer could otherwise send scans or daemon control commands. Do not claim
  a shared secret is enforceable by raw `clamd` TCP; it is not. If the inventory cannot support
  this boundary, Gate 2 must add an authenticated narrow proxy or service-level isolation and
  return that material design change for review before deployment.
- Keep the scanner's volume, config and outbound definition-update permissions scoped to this
  service. Do not put backend database or object-store secrets in the scanner. Log scan outcome,
  duration, definition age and a correlation ID only; omit file bytes, terms text, seller
  identity, ClamAV signature detail that might echo a filename, and the raw reply in public
  logs.

## 4. Backend client contract

### 4.1 Configuration and framing

- Add `LICENSE_CLAMD_HOST` and `LICENSE_CLAMD_PORT` to backend configuration. Port defaults to
  3310 only when a host is explicitly set; validate host and port at startup. If host is unset
  or invalid, scanner calls fail closed as `LICENSE_MALWARE_SCAN_UNAVAILABLE`. Do not silently
  fall back to `clamscan` or a public host. Use the Railway private-domain reference variable in
  production, and the scanner service name in Compose.
- Replace only `scan_upload_for_malware()`'s process seam with a synchronous bounded TCP client,
  retaining its callable shape so `inspect_custom_license()` and `asyncio.to_thread` remain
  compatible. The upload is already bounded and in memory at that seam
  (`aidotmarket/ai-market-backend@7643fc8b42a895f90776fd53c9784631ef21d658:app/services/custom_license_service.py:148-165,200-231`).
  Do not make a second unbounded copy.
- For one scan, open one TCP connection; send `zINSTREAM\0`, then each at-most-64-KiB chunk
  preceded by an unsigned 32-bit network-order length, then a four-byte zero length. Read
  exactly one bounded NUL-terminated reply and close the socket. Send the original bytes, not
  extracted text, a local path, hash, or base64. `clamd`'s protocol specifies the framing and
  reports an `INSTREAM size limit exceeded` error when over its configured cap. [ClamD
  protocol](https://docs.clamav.net/manual/Usage/ClamdProtocol.html).
- Before accepting a clean scan, issue a bounded `VERSION` command on its own connection and
  validate the database date. Do this for each upload, including immediately after a daemon
  restart; a five-minute monitoring poll alone could otherwise admit a stale scan. If the pinned
  daemon's `VERSION` format cannot provide a trustworthy age, Gate 2 must implement an equally
  fail-closed service readiness/freshness signal and return that protocol change for review. A
  `PING` or TCP connection is never a freshness certificate.
- Use a **1 second connection deadline, 5 second total scan/read deadline and 6 second overall
  wall deadline** for the client, including socket writes. These are proposed budgets for 1 MiB
  files, to be confirmed under load in Gate 2; they leave room within the current 30 second scan
  limit and the measured HTTP request budget. Do not use an independent timeout for each chunk
  that can extend the total indefinitely. A timeout at any stage closes the socket and fails
  closed.
- Bound reply bytes (for example 4 KiB), require a single well-formed terminated response, and
  reject trailing, malformed or contradictory responses. Only the exact documented clean
  `stream: OK` form is clean; `stream: <signature> FOUND` is detected. The signature name is
  diagnostic only and must not appear in the API response. Confirm actual wording against the
  pinned image in integration tests before freezing a parser.

### 4.2 Exhaustive outcome map

| Scanner/client outcome | API-level result | Storage rule |
| --- | --- | --- |
| Exact clean `stream: OK`, with fresh verified definitions | Continue secret/text/terms checks | Existing commit rules only |
| Valid `stream: ... FOUND` | `LICENSE_MALWARE_DETECTED` (existing 422 mapping) | No object or row write |
| `ERROR`, including `INSTREAM size limit exceeded`, parse error or daemon internal failure | `LICENSE_MALWARE_SCAN_UNAVAILABLE` (existing 422 mapping) | No object or row write |
| Connect refused/DNS failure, socket EOF, partial reply, unexpected reply, bad framing or oversized reply | `LICENSE_MALWARE_SCAN_UNAVAILABLE` | No object or row write |
| Connect, write or read deadline; queue wait deadline; stale/unknown signatures; unset configuration | `LICENSE_MALWARE_SCAN_UNAVAILABLE` | No object or row write |

Catch only the expected transport/protocol errors and map them deliberately to
`CustomLicenseError`. Preserve cancellation and process-level failures as such; ensure the
request cannot later commit after a cancelled or timed-out scan. Never interpret the presence of
`OK` inside an error or an EOF as clean. The endpoint's existing 422 mapping is a compatibility
contract, not proof a scanner is healthy
(`aidotmarket/ai-market-backend@7643fc8b42a895f90776fd53c9784631ef21d658:app/api/v1/endpoints/licenses.py:53-58`).

### 4.3 Concurrency and backpressure

- Bound backend in-flight scan admission to two per backend replica, with a two second queue
  wait. Reject excess as scanner unavailable before opening a connection; no unbounded thread
  accumulation or socket queue. Because `asyncio.to_thread` is the current bridge, the semaphore
  must cover the await, and cancellation must not release capacity while the worker continues to
  scan. Gate 2 must prove that ownership with a cancellation regression.
- Match daemon `MaxThreads=2`; start with one warm scanner replica. Count backend replicas and
  set an aggregate cap compatible with daemon capacity, or use a shared admission mechanism if
  backend scale exceeds one replica. Local per-process semaphores alone do not provide a global
  cap. Document the actual production replica count before release.
- Record bounded metrics: accepted, detected, unavailable by reason, queue rejection, in-flight,
  response latency p50/p95/p99 and definition age. Alert on sustained unavailable errors or
  queue rejects, not merely process health. Do not retry a scan automatically after an ambiguous
  failure, since that can multiply load and exceed the request budget; the seller can submit
  again after service recovery.

## 5. Alternatives rejected

| Alternative | Decision and evidence |
| --- | --- |
| Merge backend PR #464 installing `clamav` and `freshclam` in the runtime image | Reject. Event `b06fc964` reports 28.1–29.0 second cold `clamscan` loads per invocation on a 24-core arm64 host against the current 30 second timeout; OOM at 768 MiB and pass at 1.2 GiB; +372 MB backend image; definitions refresh only at image build and build-time `freshclam` can fail deployment. The PR's visible description independently reports the +372,169,174 byte image change and a build/scan smoke, but it does not prove acceptable live latency or memory. Close it as superseded after recording the decision. |
| Continue with absent `clamscan`, bypass scan, or mark failures clean | Reject. Custom uploads remain unusable or admit unscanned documents. Existing fail-closed policy is binding. |
| Run fresh `clamscan` in a sidecar per request | Reject. It still reloads the engine per scan and carries the measured cold-start cost. |
| Public scanner endpoint, public TCP proxy or unauthenticated cross-project connection | Reject. The protocol does not authenticate; do not expose file bytes and daemon controls to the internet or a broader network. |
| Third-party scanning API | Defer. It would transfer seller terms to another operator and add an external security, contract and cost decision not supplied by Max's option B. |

## 6. Risks and mitigations

| Risk | Gate 2 control and release blocker |
| --- | --- |
| Warm daemon OOM during signature reload | 4 GiB initial cap, reload peak test, Railway memory/OOM alert, fresh update + scan after reload; stop if peak exceeds cap. |
| Outdated or corrupted definitions | Six-hour update cadence, 24-hour alert, 48-hour refusal, persisted scanner-owned volume, `VERSION` and updater cross-check; no clean result with unknown age. |
| Scanner reachable by another project service | Verify project/environment service inventory and private-only settings; add authenticated proxy or isolate if trust cannot be established. |
| Backend timeouts or thread exhaustion under load | Absolute scan and queue deadlines, bounded admission, cancellation proof, load test with real daemon; stop if request p95 exceeds approved budget. |
| Inconsistent size limits or malformed protocol reply | Both sides pinned to 1 MiB; exhaustive fake-server matrix and real-container proof; every ambiguous result fails closed. |
| Rolling image update changes engine behavior | Digest pin, scanner-first rollout, clean/EICAR/size-limit probes after every image or definition change, revert digest if new engine fails. |
| Ongoing cost or volume growth | One replica, measured week-long RAM/CPU/volume bill, limit and alert; reauthorize any higher sustained spend. |

## 7. Acceptance criteria

| ID | Concrete pass condition | Evidence required |
| --- | --- | --- |
| AC1 | Scanner deploys from the reviewed official digest, exact platform manifest recorded; `clamd` and `freshclam` stay running through initial load and one update | Image digest, config, service identity, startup/update/reload logs, `VERSION`, memory peak |
| AC2 | Internal backend can connect to port 3310; no public domain or TCP proxy exists; project peer inventory supports the stated trust boundary | Railway service/network settings and scoped connectivity probes |
| AC3 | Clean valid text/PDF uploads succeed, EICAR text/PDF is refused as `LICENSE_MALWARE_DETECTED`, and no infected or unscanned document/object is committed | API status/body, scanner result, DB/object-store absence, deployed backend/scanner SHAs |
| AC4 | Every error row in §4.2 fails closed; secret, PDF active-content, text and prohibited-term checks retain their order and codes | Fake-server unit results, existing hygiene regressions, focused endpoint tests |
| AC5 | Definition age warning at 24 hours and refusal after 48 hours work, including missing/malformed date and updater failure | Synthetic time/date tests, real-container status and alert sample |
| AC6 | Under chosen concurrency, load and reload, no OOM, unbounded wait, thread leak or HTTP-budget overrun; backpressure is visible | Real-container load test with p95/p99 and peak RAM/CPU, queue and cancellation evidence |
| AC7 | S1656 equivalent uses the same digest and config, and S1738 licence Gate 4 exercises it before release | Environment commit/pin, Compose service and private network contract, Gate 4 receipts |
| AC8 | Production rollout respects actual `LISTING_LICENSES_ENABLED` state and leaves flag-off behavior unchanged; rollback restores fail-closed old path or disables admission | Flag state receipt, before/after route evidence, rollback rehearsal and live post-deploy probes |
| AC9 | PR #464 is closed as superseded without merge; scanner cost and owner are recorded | PR status, Railway estimated/actual usage and Max decision receipt |

## 8. Test plan and S1656 equivalent

1. Unit-test a fake `clamd` TCP server against exact wire bytes: command terminator, 64-KiB
   length prefixes, zero terminator, 1 MiB edge, chunk boundary, fragmented reply and NUL
   framing. Vary `OK`, `FOUND`, `ERROR`, size-limit, malformed, oversized, early close,
   DNS/connect refusal and each timeout. Assert one correct error code and zero post-scan writes
   on every refusal.
2. Run existing licence hygiene, upload and flag-off tests on the backend candidate and its
   pinned base. Specifically verify that size/MIME failures do not contact the daemon, scanner
   failure precedes secret/text/terms checks, and PDF active-content refusal remains. Existing
   tests inject a scanner and assert flag-off route absence
   (`aidotmarket/ai-market-backend@7643fc8b42a895f90776fd53c9784631ef21d658:tests/test_custom_license_upload.py:44-56,109-131`);
   they are a baseline, not sufficient real-daemon proof.
3. Add a real `clamav/clamav` container at the exact digest to CI or the isolated test
   environment, with a pinned configuration and fresh definitions. Submit a valid clean text
   file, a valid clean PDF, the standard EICAR test string in accepted text/PDF upload shapes, a
   limit-exceeding stream to the daemon, and a reload while scans arrive. Record engine/database
   versions, update age, latency, memory, results and DB/object absence. Keep EICAR bytes
   confined to this test; they are a harmless antivirus test pattern, not production seller
   content.
4. Extend the S1656 money-path test environment with a `license-scanner` Compose service using
   **the same image digest, `clamd.conf`, `freshclam.conf`, 1 MiB stream limit, private bridge
   and readiness contract** as production. Backend Compose config points at
   `license-scanner:3310`. No public port mapping. Pin the environment commit and image
   alongside its backend version. The existing S1656 environment uses an owned private Compose
   bridge and pinned backend
   (`aidotmarket/runbooks@b7009e89575ec0cef6b0c5e9c1a19b28848ee43a:money-path-test-environment.md:42-74`); modify the owning environment repo in
   Gate 2, not this Gate 1 artifact.
5. The S1738 licence Gate 4 uses that Compose service for seller upload, listing publication and
   buyer-facing licence notice/download assertions, including EICAR refusal and a
   scanner-down/stale case. Capture exact environment/backend/frontend/scanner pins and
   receipts. A fake server alone cannot satisfy Gate 4.

## 9. Rollout, monitoring and rollback

1. Before deployment, record Council disposition, exact scanner/backend/environment commits and
   image digests, current production `LISTING_LICENSES_ENABLED` state, backend replica count,
   Railway project/environment, private peer inventory and spend authorization. Close PR #464 as
   superseded once the reviewed replacement is accepted; never use its image as a stepping
   stone.
2. Deploy the scanner service **first**, private only, with definitions and health monitoring.
   Wait for `PING` response, valid `VERSION` database date under 48 hours, clean and EICAR
   `INSTREAM` from a scoped private operator probe, and a successful definition refresh/reload
   observation. `PING` alone proves process responsiveness, not signature readiness.
3. Deploy backend client/config next while preserving the existing flag state. With
   `LISTING_LICENSES_ENABLED=false`, prove the custom route remains absent and no upload
   behavior changes. If the flag is already true, keep seller admission controlled during
   transition and expect fail-closed errors until the scanner and client are ready; do not
   silently change the flag based on this spec.
4. With the recorded production flag state respected, run a bounded operator clean upload and
   EICAR refusal through the actual production backend only under the applicable release
   authorization. Verify zero EICAR DB/object writes and no secret/file-content logs. Record
   live backend/scanner image identities and response times. Recheck the flag, health, signature
   age and errors after a watch window; complete S1738 Gate 4 in S1656 before declaring release
   acceptance.
5. Monitor `PING`, `VERSION` database date, `freshclam` result, scanner memory/CPU/restarts,
   scan latency, error-code counts, queue rejects and cost. Alert at 24-hour signatures and
   refuse after 48 hours. A green container alone is insufficient.
6. Roll back the backend client to the last reviewed image or set
   `LISTING_LICENSES_ENABLED=false` through the approved operator path if the new path cannot
   scan reliably. The old backend with no local ClamAV remains fail-closed for custom uploads;
   do not describe that as restored upload availability. Keep the scanner private during
   diagnosis, then stop it only after no caller depends on it. Retain signed licence records and
   uploaded clean documents; do not down-migrate or delete them. Restore service availability by
   fixing scanner/definitions and repeating clean/EICAR probes, not by disabling the scan.

## 10. Open questions for Council

1. Is Railway private project/environment isolation sufficient for this unauthenticated `clamd`
   protocol after peer inventory, or must Gate 2 include an authenticated proxy or separate
   project boundary? If stronger isolation is required, review the changed design before
   implementation.
2. Is 48 hours the accepted maximum signature age for seller terms, with warning at 24 hours?
   Should a known upstream outage have any exception? This design proposes **no exception**
   without an explicit new decision.
3. Does the six-second scan wall deadline and two-scan concurrency cap meet the observed
   production request budget and seller upload volume? Gate 2 must bring measured real-daemon
   evidence if they need adjustment.
4. Who owns the scanner service, signature alerts, image digest updates and monthly spend
   review? Record a named operator and escalation path before Gate 4.
5. Does Council require a dedicated authenticated proxy to suppress `clamd` administrative
   commands from other private peers, even if all current peers are trusted?
