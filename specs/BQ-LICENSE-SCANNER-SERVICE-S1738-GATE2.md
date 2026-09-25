# BQ-LICENSE-SCANNER-SERVICE-S1738 Gate 2 detailed build specification

**Status:** Proposed Gate 2; Gate 1 passed 3/3 and merged as `aidotmarket/runbooks@a8bfaaa8d6b049c4b21d0c751e7e30c3dda85e79`. This document authorizes no build dispatch, production change, or claim of live scanner proof until the applicable gate decision. **Build Queue:** `build:spec-license-scanner-service-s1738`.

**Source baseline:** backend `aidotmarket/ai-market-backend@d9b02a5cfd816afef7dd47059ea7d02e106bb5aa` (`origin/main`, independently read for this spec); S1656 environment `aidotmarket/money-path-test-environment@3722ac6768886e0d52c3bffb9ac95e2ef2819d28` (`origin/main`, inspected `compose.yaml`). Gate 1 and its GLM, DeepSeek and Gemini R2 reviews remain binding. Re-pin all three implementation candidates and the deployed image digest at Gate 3 and Gate 4; these source pins are not deployment proof.

## 1. Outcome, authority and frozen behavior

Build a small dedicated ClamAV service on Railway private networking and replace the backend's in-process `clamscan` subprocess with a bounded `clamd` INSTREAM client. Seller licence terms alone cross this boundary; buyer data, seller credentials and object-store secrets do not. Retain the 1 MiB application cap, quarantine, MIME and hygiene order, API error codes, and scan-before-storage invariant. At the baseline, `MAX_LICENSE_BYTES` and `scan_upload_for_malware` are in `app/services/custom_license_service.py:27-28,68-81`; scan precedes secret, PDF/text and terms checks at `:148-197`; `store_custom_license` reads into quarantine, calls inspection in `asyncio.to_thread`, and writes only after inspection at `:200-273`. The endpoint has the seller guard, fail-closed rate limiter, flag, and 422/503 mappings at `app/api/v1/endpoints/licenses.py:14-17,31-59`. The backend runtime Dockerfile has no ClamAV installation at `Dockerfile:43-65`.

Gate 2 implements Gate 1, including the R2 carried items: immutable wrapper and Railway monitor invocation (GLM LOW), explicit `VERSION` grammar/timezone fixtures (GLM NIT), operator admission stop after drift (DeepSeek LOW), dual loopback/private reachability (DeepSeek NIT), probe interpreter dependencies (Gemini NIT), and commit-pinned upstream samples (Gemini NIT). No schema, runbook tooling, runbook lint rule, upload-cap increase, malware bypass, or in-backend ClamAV image change belongs to this build. PR #464's in-backend alternative remains superseded; close it under the approved replacement process, never merge its Dockerfile.

## 2. Exact three-repo chunk manifest

| Chunk | Repo and exact files | Deliverable and review boundary |
| --- | --- | --- |
| A | **New** `aidotmarket/license-scanner-service`: `Dockerfile`, `clamd.conf`, `freshclam.conf`, `healthcheck`, `monitor`, `entrypoint`, `scripts/railway_drift_check.py`, `tests/test_railway_drift_check.py`, `tests/test_probe.py`, `tests/test_container.sh`, `README.md` | Immutable wrapper image, freshness probe, private HTTP monitor and read-only Railway drift check. Drift tests cover peer inventory, public routes, image/config and backend worker/replica counts. No runtime mutable config mount. |
| B | `aidotmarket/ai-market-backend`: `app/services/custom_license_service.py`, new `app/services/license_clamd_client.py`, `app/core/config.py`, new `scripts/check_license_scanner_admission.py`, `.github/workflows/license-scanner-backend-deploy.yml`, `tests/test_license_scanner_admission.py`, `tests/test_license_clamd_client.py`, `tests/test_custom_license_upload.py`, focused endpoint/flag tests | Preserve the callable seam and API contract; replace subprocess; bound connection, reply, admission and deadlines. The rollout workflow runs admission preflight before every backend rollout. No migration or new public endpoint. |
| C | `aidotmarket/money-path-test-environment`: `compose.yaml`, `versions.env`, `tests/compose-contract.sh`, new `tests/test-license-scanner-contract.py`, S1738 licence journey tests under `browser/` or the existing contract-test tree | Pull the exact Chunk A image digest, wire `license-scanner`, and prove cold readiness, real clean/EICAR/limits and scanner-down/stale refusal. No public scanner port. |

Build A, then B, then C; review each exact candidate and integrated pinned set before Railway rollout. `versions.env` records the scanner wrapper digest and source SHA alongside the existing backend/frontend pins. Never substitute a locally rebuilt tag for the reviewed digest.

## 3. Chunk A — scanner wrapper and executable contract

### 3.1 Image and process

`Dockerfile` begins with `FROM docker.io/clamav/clamav-debian@sha256:df80497be841a8ad57f95e04f978216241457f8f8ad608f1f682e3cd0fe63c45`. The verified index includes native amd64 `sha256:a1ebc843a1bf773c442a0739778d30e9072da7c52417ab7d805942510fa88394` and arm64 `sha256:32770534ece41601bed0005be5d1e1b7a76d734255c0ad02ad52f9281eb30418`. Copy the exact files below into the base image's effective `/etc/clamav/clamd.conf` and `/etc/clamav/freshclam.conf`, and copy executable `healthcheck` and `monitor` to `/opt/license-scanner/`. Verify those are the paths the pinned image entrypoint actually reads; a mismatch blocks the image build. Keep its vendor startup of both `clamd` and `freshclam`, `CLAMAV_NO_CLAMD=false`, `CLAMAV_NO_FRESHCLAMD=false`, `FRESHCLAM_CHECKS=4`, and a scanner-owned `/var/lib/clamav` volume. Do not bake signatures into each backend build or set an update bypass. Set `TZ=UTC` and `LC_ALL=C` in the wrapper for deterministic `VERSION` dates.

The wrapper installs `python3-minimal` and `ca-certificates` in its build layer, then asserts `/usr/bin/python3` exists, imports only Python standard-library modules used by the probe, executes the probe, and verifies the final image contains both config files. `healthcheck` has `#!/usr/bin/python3`, executable mode 0755, and no `bash`, `nc`, `curl`, `/dev/tcp`, external package or network download dependency. The final wrapper OCI digest, source commit, base index digest, pulled native platform manifest, SHA-256 of both configs and both executables are a single release identity. An image update changes that identity and needs review, vulnerability scan and full container smoke proof. Pin upstream sample references by commit, for example [clamd sample](https://github.com/Cisco-Talos/clamav/blob/72cd48c9faed4fa4afc22bc4ed0b9b19f8d3f8f7/etc/clamd.conf.sample) and [freshclam sample](https://github.com/Cisco-Talos/clamav/blob/72cd48c9faed4fa4afc22bc4ed0b9b19f8d3f8f7/etc/freshclam.conf.sample); confirm the files exist at that immutable commit during build review. Samples explain directives; the reviewed files below are authoritative.

`clamd.conf` is the complete intended effective configuration (no vendor default may override a listed directive):

```conf
DatabaseDirectory /var/lib/clamav
Foreground yes
TCPSocket 3310
TCPAddr 0.0.0.0
StreamMaxLength 1M
MaxScanSize 16M
MaxFileSize 8M
MaxRecursion 8
MaxFiles 1000
AlertExceedsMax yes
HeuristicAlerts yes
HeuristicScanPrecedence yes
EnableShutdownCommand no
EnableStatsCommand no
EnableReloadCommand no
EnableSelfCheckCommand no
EnableVersionCommand yes
SelfCheck 60
MaxThreads 2
```

`TCPAddr 0.0.0.0` is container-local binding to both loopback and Railway's private interface; the service has **no public ingress**. Smoke-test local `127.0.0.1:3310` and a second private-network container at the service name simultaneously. `freshclam.conf` is:

```conf
DatabaseDirectory /var/lib/clamav
DatabaseOwner clamav
DatabaseMirror database.clamav.net
Checks 4
Foreground yes
```

No `NotifyClamd`: `SelfCheck 60` observes definition updates and reloads. The builder must prove the pinned image starts both daemons with these exact files, a successful freshclam update leads to a clamd reload and changed `VERSION` database date, and clean/EICAR scans still work. If the vendor entrypoint requires a different foreground setting or configuration path, stop and return the exact image behavior for Gate 2 review; do not silently alter the contract.

Chunk A build qualification records the pinned image's actual `/init` ENTRYPOINT/CMD, effective configuration paths, observed `VERSION` bytes and parser match, and both daemon lifecycles. It also proves Railway routes the internal `/ready` deployment check to port 8081 while 3310 stays private. If that fails, use the reviewed private operator-job fallback in §3.2 and return the exact platform result for review before release. Neither item is an owner policy decision.

### 3.2 Freshness probe and Railway invocation

`healthcheck` makes one bounded TCP connection to `127.0.0.1:3310`, sends `zVERSION\0`, reads at most 4 KiB through one NUL terminator, rejects trailing bytes, and exits zero only when the parsed database timestamp is at most 48 hours old and no more than five minutes in the future. It uses a one-second connect and two-second total deadline. `PING` is never a substitute; it never runs freshclam. The accepted fixture grammar is `ClamAV <engine>/<decimal-db-version>/<Ddd Mmm [ ]d HH:MM:SS YYYY>\0` with English ASCII weekday/month tokens and one- or two-column day, exactly as emitted by the pinned image. Pin `TZ=UTC`, parse with an explicit English month table, validate weekday/date/calendar and interpret the no-offset timestamp as UTC; do not use host locale or local timezone. A nonconforming real image reply blocks release pending a reviewed parser revision. Fixtures cover UTC host vs non-UTC caller, locale variation, leap/day boundaries, absent/malformed/extra fields, stale at 48h plus one second, exactly 48h, future beyond five minutes, EOF, timeout and oversized reply. The backend client uses the same grammar and age policy, with independently maintained tests so the two implementations cannot mask each other's defect.

`monitor` is a second executable using the installed Python interpreter. It invokes `/opt/license-scanner/healthcheck` directly every 300 seconds and serves HTTP `GET /ready` on container port 8081, returning 200 solely for the latest successful probe whose result is less than five minutes old, and 503 otherwise; it logs only age/status/latency and emits a 24-hour warning event to the trusted operations collector for an on-call alert receipt. Port 8081 is reachable only inside the reviewed Railway private environment: no public domain or TCP proxy is created for either listener. The `entrypoint` starts the monitor, invokes the pinned image's actual vendor init command with its original arguments, forwards SIGTERM, and exits nonzero if either process dies; the build first inspects and records the base image's ENTRYPOINT/CMD rather than guessing them. Container tests terminate each process in turn and prove `/ready` becomes non-200 and the container exits. Railway sets `PORT=8081`, deployment healthcheck path `/ready`, and a timeout long enough for the measured cold definition load. [Railway healthcheck documentation](https://docs.railway.com/deployments/healthchecks) says this HTTP check gates deployment, uses `PORT`, and does not monitor after deployment. Continuous freshness comes from the running monitor loop and a same-project trusted operations collector scheduled as an operations job, documented in Chunk A `README.md`, polling `http://license-scanner.railway.internal:8081/ready` every five minutes and consuming the 24-hour warning event. It alerts on that warning, non-200, missed poll or stale probe and records delivery receipts. If Railway cannot keep 3310 private while using an internal HTTP deploy check, leave the Railway deploy check unset and gate deployment with the exact `/opt/license-scanner/healthcheck` invocation via a private scoped operator job; return that platform finding for review before release. Backend per-upload freshness remains mandatory regardless of monitor state. The image's Docker `HEALTHCHECK` also invokes `/opt/license-scanner/healthcheck` every 10 seconds with 5-second timeout, 120-second start period and 18 retries. Cold empty volume, malformed/stale date and daemon-down tests must turn all three signals non-ready.

The `VERSION` sample parser must be tied to the pinned image's observed output, not an assumed current stable tag. Record the actual engine version and immutable corresponding upstream source commit in the build receipt.

### 3.3 Scanner behavior qualification

Run on both native platform manifests where available, recording Titan-1 and Railway host architecture and pulled manifest. Emulated timing does not size Railway. Test clean file, EICAR, exactly 1 MiB, over-1-MiB stream, MaxScanSize, MaxFileSize, MaxRecursion and MaxFiles compressed fixtures. Every incomplete/limited scan must be `FOUND` and refused, or `ERROR` and unavailable; an `OK` on any limit fixture blocks Gate 2 acceptance. Specifically prove `MaxFiles 1000` exceedance on this engine; `AlertExceedsMax` documentation does not guarantee it. Repeat scans through a reload. Probe `zSHUTDOWN\0`, `zSTATS\0`, `zRELOAD\0`, `zSELFCHECK\0` from an approved private peer and require `COMMAND UNAVAILABLE`. Keep fixture bytes in the test environment only and never log raw scanner replies in public logs.

## 4. Chunk B — backend client and no-write mapping

In `app/core/config.py`, beside `LISTING_LICENSES_ENABLED` (`:188-190`), add `LICENSE_CLAMD_HOST: str | None` and `LICENSE_CLAMD_PORT: int | None`. Bind the accepted destination to the reviewed environment configuration: S1656 accepts only the exact Compose service name `license-scanner` at port 3310; production accepts only `license-scanner.railway.internal` at port 3310, where `license-scanner` is the exact approved Railway service name in the production project/environment. The environment-specific host allowlist is fixed in reviewed configuration, not derived from an untrusted host value or a generic `*.railway.internal` suffix. An absent port resolves to 3310 only for an allowlisted host. Reject public DNS names, URL/scheme forms, literal public IPv4/IPv6 and other IP literals, unapproved `.internal` names, paths, embedded ports, and any port other than 3310 before opening a scan connection or sending upload bytes. An unset/invalid destination yields `LICENSE_MALWARE_SCAN_UNAVAILABLE` on upload without fallback or startup failure that breaks flag-off operation. Railway private routing and the no-public-route drift check remain separate network controls. No secret belongs in the host name. Keep `WORKERS=1` and exactly one backend replica for this release: the production command reads `${WORKERS:-1}` in `Dockerfile:100-103`.

`aidotmarket/ai-market-backend:scripts/check_license_scanner_admission.py` is the exact read-only preflight artifact. The new `aidotmarket/ai-market-backend:.github/workflows/license-scanner-backend-deploy.yml` rollout workflow invokes it as a required, fail-closed step immediately before **every** Railway backend rollout, including image rollback, and cannot deploy when it fails. It verifies the effective `WORKERS` value and live backend replica count are both exactly one and records the Railway project/environment and deployment identity. Disable any automatic or alternate backend rollout path that bypasses this required step before activation; a direct/manual rollout must invoke the same gate and retain its receipt. `tests/test_license_scanner_admission.py` covers missing/invalid counts, zero, two or more, API failure and accepted 1/1. Scaling requires reviewed shared cross-process admission and renewed A6 proof.

In new `app/services/license_clamd_client.py`, implement synchronous `scan(data: bytes, host, port) -> None` and a process-owned semaphore of capacity two. Its two-second queue deadline and six-second overall wall deadline cover queue, both `VERSION` checks, connect, writes and reply; connection deadline is one second and scan/read budget five seconds. Use monotonic absolute deadlines, not per-chunk resets. The caller already has bounded `bytes`; frame `zINSTREAM\0`, at-most-64-KiB memoryview chunks each with unsigned network-order 32-bit length, and one zero-length terminator. The pre-scan `zVERSION\0` uses its own connection and the §3.2 parser before **any** upload byte; immediately open the scan connection and refuse if the verified deadline/freshness expires. After an exact clean scan reply, perform a second `zVERSION\0` on a new connection with the §3.2 parser before returning clean; arithmetic on the pre-scan timestamp is not a recheck. A stale, malformed or timed-out post-scan reply raises `LICENSE_MALWARE_SCAN_UNAVAILABLE` with zero writes. Read exactly one bounded NUL-terminated scan reply (4 KiB maximum) and reject trailing/partial/contradictory data. Only exact `stream: OK` with fresh definitions returns; exact `stream: ... FOUND`, including `Heuristics.Limits.Exceeded.*`, raises detected. `ERROR`, including stream-size limit, raises unavailable. Never return clean on an ambiguous reply, early close or partial scan.

Map expected `OSError` (DNS failure, refused connection, `BrokenPipeError`, `ConnectionResetError`), socket timeout, malformed protocol, missing configuration and queue timeout to `CustomLicenseError("LICENSE_MALWARE_SCAN_UNAVAILABLE")`; map valid `FOUND` to `CustomLicenseError("LICENSE_MALWARE_DETECTED")`. Preserve cancellation and process-fatal exceptions instead of swallowing them. In `app/services/custom_license_service.py`, replace only the body of `scan_upload_for_malware` (`:68-81`) with the new client call, remove `subprocess` import (`:10`) and all in-process `clamscan` execution. Keep `inspect_custom_license(... malware_scanner=scan_upload_for_malware)` injection (`:148-165`) and `store_custom_license`'s `asyncio.to_thread` boundary (`:200-231`). To prevent a cancelled request's worker thread later committing, the thread owns scan and hygiene only; the event-loop caller cannot proceed to DB/object writes after cancellation (`:232-273`). Confirm with cancellation while the fake daemon blocks. Preserve endpoint `CustomLicenseError` 422 mapping and unexpected 503 (`app/api/v1/endpoints/licenses.py:53-58`). No signature name, raw reply, file bytes, terms, seller identity or secrets in logs/API. `app/services/license_clamd_client.py` emits bounded runtime metrics for accepted, detected and unavailable by reason, queue rejection, in-flight scans, response latency p50/p95/p99 and definition age; scoped tracing carries correlation ID only. Test each metric class without exposing content.

Required tests in `tests/test_license_clamd_client.py`: fake daemon exact clean and EICAR `FOUND`; every `ERROR`/limit-exceeded response; clean-looking prefix with trailing bytes; missing terminator, oversize reply, early daemon close on write, reset, EOF, timeout at connect/write/read/queue, DNS failure, unset/invalid config; destination matrix accepting only the configured S1656 or production host at 3310 and rejecting public DNS, URL forms, public IPv4/IPv6, other IP literals, unapproved `.internal`, paths, embedded ports and other ports before any upload bytes; stale/malformed/future `VERSION` before any INSTREAM bytes; fresh-before/clean-INSTREAM/stale-after, fresh-before/clean-INSTREAM/malformed-after and fresh-before/clean-INSTREAM/post-`VERSION`-timeout, each unavailable with zero writes; UTC/timezone/locale fixtures; 1 MiB accepted framing with exact byte equality and 1 MiB + 1 rejected by the application before a socket; two admitted, third refused after two seconds; overall deadline cannot be prolonged chunk by chunk. In `tests/test_custom_license_upload.py` retain the existing fake-scanner seam and flag-off route test (`:44-56,109-131`); add those three post-scan sequences to upload/no-write tests, plus detected/unavailable/no-write and cancellation cases, PDF object-store no-write, and existing secret/PDF/text/terms code/order regressions. Exercise the endpoint's actual 422 code shape, flag-off 404, seller capability and rate limiter. A fake daemon unit pass does not replace real Chunk A/S1656 tests.

## 5. Chunk C — S1656 equivalent and contract tests

At S1656 baseline `compose.yaml:23-124`, backend uses a private bridge, `LISTING_LICENSES_ENABLED=true`, pinned backend build and existing postgres/redis healthy dependencies. Add the scanner without removing those dependencies:

```yaml
services:
  license-scanner:
    image: ${LICENSE_SCANNER_IMAGE:?reviewed wrapper digest required}
    environment:
      TZ: UTC
      LC_ALL: C
      CLAMAV_NO_CLAMD: "false"
      CLAMAV_NO_FRESHCLAMD: "false"
      FRESHCLAM_CHECKS: "4"
    volumes:
      - license-scanner-definitions:/var/lib/clamav
    networks: [private]
    healthcheck:
      test: ["CMD", "/opt/license-scanner/healthcheck"]
      interval: 10s
      timeout: 5s
      start_period: 120s
      retries: 18
    restart: unless-stopped
  backend:
    environment:
      LICENSE_CLAMD_HOST: license-scanner
      LICENSE_CLAMD_PORT: "3310"
      WORKERS: "1"
    depends_on:
      license-scanner:
        condition: service_healthy
volumes:
  license-scanner-definitions:
```

Merge those mapping fragments into the existing Compose file; keep postgres/redis dependencies and all existing backend environment entries. There is no scanner `ports:` mapping. Add label/pin checks in `tests/compose-contract.sh`; contract tests assert identical wrapper digest/config hashes, native platform, no public port, healthcheck command/timing, backend `service_healthy`, host/port and worker count. On an **empty** scanner volume, backend must wait until signatures load and a valid fresh `VERSION` is available; a cold timeout is a failure to diagnose, never an invitation to increase retries without evidence. Test scanner down, stale/invalid date, clean terms, EICAR refusal with no `LicenseDocument`/object-store write, limit fixtures, seller upload and listing publication, and buyer notice/download through the real S1656 service. Record backend, frontend, environment and scanner source/image pins, container identities, actual requests, database/object-store absence for refusals and browser receipts. S1656 uses its own private bridge and test credentials; production credentials never enter it.

## 6. Railway deployment, drift control and operations

Create `license-scanner` in the **same production Railway project and environment** as the backend from the reviewed wrapper image digest. Set one replica, 4 GiB memory, 1 vCPU, no scale-to-zero, scanner-owned `/var/lib/clamav` volume, `PORT=8081`, healthcheck path `/ready`, and private DNS. Do not create a public domain, public TCP proxy, public port, or backend/object-store/DB secret. Set only nonsecret daemon variables and private image identity via the approved Infisical-to-Railway path; store Railway API/monitor credentials in Infisical only, never in Git, Compose or receipts. Backend `LICENSE_CLAMD_HOST` is exactly `license-scanner.railway.internal`, `LICENSE_CLAMD_PORT=3310`, `WORKERS=1`, one replica. Check the existing production `LISTING_LICENSES_ENABLED` value before changing anything. The first week records actual memory including first load and reload peak, CPU, latency, queue rejects, volume/egress and cost. Increase limits only after measured review and spend authority; the 4 GiB/1 vCPU values are starting caps, not a guaranteed cost.

The **deployment gate and recurring daily operations job** run `aidotmarket/license-scanner-service:scripts/railway_drift_check.py` read-only in the approved operator environment using a scoped Railway API identity from Infisical. Before build, **Mars** records the exact current production project/environment service inventory from read-only `railway status` and service list, with secrets suppressed, in the scanner deployment manifest; Max ratifies the peer allowlist before deployment. Candidate expected peers are the current backend, Postgres, Redis and frontend services, but exact live service identities must replace these labels; the new `license-scanner` is added explicitly. Compare project/environment service inventory with that approved allowlist; scanner public domains and TCP proxies with the empty set; image digest, startup command, Docker/HTTP healthcheck invocation, mounted volume and private DNS; and effective admin-command responses from a trusted private peer. Also compare the backend effective `WORKERS` and live replica count with exactly one. Missing, unreadable, zero or any count other than one fails the deployment gate and triggers the recurring admission stop; increasing either count requires reviewed shared admission and renewed A6 evidence. `tests/test_railway_drift_check.py` covers changed peers/routes/config, missing counts, zero/two-or-more workers or replicas, API failure and 1/1 acceptance. A mismatch fails the deployment gate immediately. For backend worker/replica mismatch, the daily job synchronously blocks `/api/v1/licenses/custom` admission through the existing authenticated edge control and verifies refusal before reporting the check complete; there is no 15-minute grace for that count mismatch. The daily job alerts the on-call operator immediately and opens an incident; the operator disables `LISTING_LICENSES_ENABLED` through the existing approved Railway/Infisical flag path within **15 minutes of alert receipt**, verifies the new backend deployment and route/admission refusal, and keeps it off until peer/route/config review and clean/EICAR requalification. If the flag cannot be changed inside that window, block backend ingress to `/api/v1/licenses/custom` via the existing authenticated edge control and verify refusal; escalate to the production owner. This is the concrete drift-to-admission stop. No automated agent may silently delete a peer or mutate Railway networking. The incident receipt names the owner, detection time, flag/edge action time, deployment identity and retest. The scanner's unauthenticated TCP remains acceptable only under the reviewed private peer boundary; failure to maintain it requires a separately reviewed authenticated proxy or isolation design.

The monitor polls every five minutes and alerts for missing/non-200 readiness, definitions older than 24 hours, freshclam failure, restart/OOM, memory above 80% outside reload, scan p95/deadline breaches, queue saturation and `LICENSE_MALWARE_SCAN_UNAVAILABLE` spikes. At 48 hours backend and healthcheck refuse regardless of alert state. Monitoring never triggers repeated freshclam downloads. Dashboard/log labels carry correlation ID, status, duration and age only. Record on-call owner and escalation destination before deployment.

Rollout order: (1) obtain approved Gate 2/build/Gate 3 and spend receipts, inspect production flag/worker/replica/peer/architecture; (2) deploy scanner **first** at exact wrapper digest, validate private-only settings, cold health, fresh `VERSION`, freshclam update/SelfCheck reload, clean and EICAR, and disabled admin commands; (3) deploy backend client with **unchanged flag state**, verify flag-off route absence if off or controlled fail-closed admission if already on; (4) only under applicable release authority perform bounded real-backend clean/EICAR uploads and no-write checks; (5) complete S1656 Gate 4 and observe alert/cost window before completion. Railway lacks Compose `depends_on`; scanner-first plus per-upload freshness and fail-closed mapping is the production equivalent.

Rollback: switch the flag off using the approved path or restore the last reviewed backend image, verify route absence or `LICENSE_MALWARE_SCAN_UNAVAILABLE` and no writes. The old image has no local ClamAV, so it does **not** restore custom upload availability. Keep the scanner private during diagnosis, then stop it only after callers are removed; retain clean documents and signed records, no down-migration. To restore uploads, fix definitions/service, repeat real clean/EICAR and freshness proof, and re-enable only under release authority. A scanner image rollback uses the prior reviewed wrapper digest with the scanner-owned volume retained and freshness requalified.

## 7. Acceptance manifest and open decisions

| Gate 4 criterion | Required evidence |
| --- | --- |
| A1 immutable native image and lifecycle | A/B/C commits, wrapper OCI digest, base index and selected platform manifests for Railway and Titan-1, architecture, config/executable hashes, first load, freshclam update, SelfCheck reload, `VERSION`, peak memory, clean/EICAR |
| A2 private trust boundary | Mars's read-only production service inventory, Max-ratified peer allowlist, Railway project/environment, empty public domain/TCP proxy, private `VERSION`/INSTREAM, four admin commands returning `COMMAND UNAVAILABLE`, drift-script tests, deployment and daily drift receipts, admission-stop rehearsal |
| A3 complete scan and limits | Exact 1 MiB boundary; clean/EICAR; MaxScanSize, MaxFileSize, MaxRecursion, MaxFiles and stream limit; reload repetition; every partial/ambiguous response refuses, zero object/row writes |
| A4 backend errors and policy | Fake-daemon matrix, real daemon endpoint 422 codes, connection/timeout/DNS/early-close/cancellation, unchanged secret/PDF/text/terms order, flag-off route absence, seller guard and limiter |
| A5 freshness and monitoring | UTC grammar fixtures, delivered 24h alert and 48h refusal, stale/malformed/future before INSTREAM, fresh-before/clean-INSTREAM/stale-after, malformed-after and post-`VERSION`-timeout fake-daemon plus upload zero-write receipts, freshclam/daemon log cross-check, Railway deploy/readiness and five-minute operations poll receipts |
| A6 aggregate admission | Required backend rollout workflow and preflight location/invocation receipt on every rollout; `WORKERS=1`, one backend replica, tests refusing any other/missing count; daily drift detection and admission-stop rehearsal for worker/replica change; two simultaneous scans and third queue refusal, runtime accepted/detected/unavailable-by-reason, queue rejection, in-flight, p50/p95/p99 latency and definition-age metrics, measured peak and request deadline; shared admission review and renewed evidence before scale |
| A7 S1656 and customer journey | Empty-volume cold Compose startup and healthy dependency, exact scanner/backend/frontend/environment pins, seller clean upload/listing publication, EICAR and scanner-down/stale refusal, buyer notice/download, no-write evidence |
| A8 production and rollback | Existing flag state, scanner-first/backend deployment identities, live private probes, bounded real-backend clean/EICAR if authorized, rollback rehearsal, post-deploy watch and actual cost; PR #464 closed as superseded and unmerged with status/merge receipt |

**Remaining Max decisions (recommended defaults):** ratify Mars's recorded exact production peer allowlist before deployment (default: only current reviewed backend, Postgres, Redis, frontend and new scanner identities); name the on-call operator and alert escalation destination (default: existing production on-call rotation); approve scanner spend authority after the measured first-load/reload and cost receipt (default: hold rollout until approved). The 48-hour no-exception limit stays as approved in Gate 1. The six-second/two-scan contract stays fixed unless real-daemon measurements require a separately reviewed revision. Chunk A qualifies image entrypoint/`VERSION` and Railway internal health routing with the pass criteria above. Any answer changing the trust boundary, freshness guarantee, scan-limit refusal or backend deadline returns to review before build/release.

## 8. Round 1 disposition

| Council finding | Disposition in this Gate 2 revision |
| --- | --- |
| GLM MEDIUM destination validation | Exact environment-bound `license-scanner:3310` and `license-scanner.railway.internal:3310` allowlist; reject all other destinations before bytes; config matrix in Chunk B. |
| GLM MEDIUM post-scan freshness | New independent `zVERSION` connection after clean scan; three fake-daemon and upload zero-write sequences; A5 receipts. |
| GLM MEDIUM aggregate admission | Backend preflight script and required rollout workflow; daily drift checks effective `WORKERS` and replicas at 1/1; tests and A6 stop/scale evidence. |
| GLM LOW PR #464 closure | A8 requires closed, superseded, unmerged receipt. |
| Gemini LOW drift artifact and allowlist | Chunk A drift script/tests; Mars-owned read-only production inventory before build and Max ratification before rollout. |
| Gemini LOW technical qualification | Chunk A image and Railway routing pass criteria; removed from owner decisions. |
| Gemini NIT poller and preflight | Operations job in Chunk A `README.md`; exact backend preflight file and required rollout workflow. |
| DeepSeek LOW/NIT post-check, metrics, 24h alert, owner list and host claim | Fresh second `VERSION`, named backend metric emitter/tests and A6 receipt, delivered 24h alert/A5 receipt, narrowed owner decisions, exact allowlist plus separate network controls. Informational controller metadata requires no spec change. |
