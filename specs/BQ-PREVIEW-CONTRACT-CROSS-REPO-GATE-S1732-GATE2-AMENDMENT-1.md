# BQ-PREVIEW-CONTRACT-CROSS-REPO-GATE-S1732 — Gate 2 Amendment A2

**Status:** proposed Gate 2 amendment for Council review. This is specification authoring only. It authorizes no implementation, provider mutation, protection change, merge, deployment, credential use, or customer-data access. The approved [Gate 2 specification](BQ-PREVIEW-CONTRACT-CROSS-REPO-GATE-S1732-GATE2.md) remains binding except for the clauses explicitly amended below. The Gate 1 design, wire format, two-repository isolated execution, merge order, raw-byte approval, protection requirements, and Gate 3 review requirement are unchanged.

## 1. Failure and decision

The original backend anchor `A=224b85a4153613350fcf0f53203a4940a2dd0ade` is immutable and already pinned by merged AIM Data `B=bf80d08f8a6d01bee0872885172f5722980870ac` (AIM PR #80; merge of `6529e1ed` and `19d093fb`; manifest begins `45f9d6a1`). AIM `main` passed its new job; its protection was applied and read back. A disposable mutation PR #81 failed that check, and an administrator merge was refused with HTTP 405. The two target-only read-only deploy keys, Infisical entries, and holder secrets exist and passed the meaningful smoke tests described in §4.

Backend PR #456 has `A` followed by reverse-pin commit `5cf0e346` (`aim_data_sha=B`, `contract_anchor_sha=A`, lock only). Its required job run `35833365991` failed at **Focused regressions** for two independent reasons:

1. Gate 2 §5.2 sets `DATABASE_URL=sqlite+aiosqlite:////tmp/preview-contract/backend.db`. `app/core/database.py` creates an async engine with `pool_size`, `max_overflow`, and `pool_timeout`; SQLite rejects those arguments during import, so `tests/test_listing_preview_database.py` cannot collect. A nonconnecting PostgreSQL URL merely hides the problem: 62 database tests skip with `required disposable PostgreSQL is unavailable`.
2. Two tests in anchor `A` read the *current* lock while asserting its *initial* values. `test_lock_schema_and_pinned_initial_values` expects the initial AIM SHA and placeholder anchor, and `test_anchor_only_installation_fails_backend_transition_at_reverse_pin` expects `aim_lock_missing_or_not_anchor`; after the legitimate reverse pin, the latter reaches `aim_checkout_sha`. Gate 2 §4 requires fixtures for both exact initial and follow-up values, but the implementation accepts only the initial state.

`tests/test_preview_contract_cross_repo.py` is a protected `BACKEND_CONTRACT_PATHS` entry. The post-anchor `anchor-diff` rule permits only the lock and workflow to change. AIM's `aim-transition` also rejects a same-manifest pin-only replacement anchor. A test-only edit after `A` therefore cannot pass by either path. Do not rewrite or delete `A`, turn a red job green through skipped tests, or relax a pin to manufacture a pass.

### 1.1 Options

| Option | Security effect | Cost |
|---|---|---|
| **A. New paired anchor `A2` (recommended).** Keep backend PR #456 open. Commit an `A2` descending from `A` and `5cf0e346`, with the two test repairs, the new-anchor transition rule, synchronized reviewed-ID inventory/count changes, and at least one useful new corpus vector. The reviewed vector changes the manifest digest. AIM opens a new PR pinning `A2` and its new digest, merges as `B2`; the backend adds one reverse-pin follow-up naming `B2` and `A2` and merges with both `A` and `A2` in ancestry. | Preserves immutable reviewed `A`, corpus-based anchor declaration, and the protected test path. Both repositories re-execute a newly reviewed byte corpus. | Two more reviewed commits/PR phases, raw-byte row review, new AIM main and backend job evidence, and another Gate 3 audit of the exact code candidate. |
| **B. Erratum allowing the reverse-pin follow-up to edit the test file.** Change the `anchor-diff` allowed set in `scripts/preview_contract_gate.py` and then repair the tests. | Weaker: the gate would relax its own post-anchor confinement to let a protected test file change after AIM had pinned `A`. A passing result would no longer prove that the reviewed anchor's tests remained fixed. | Smaller apparent corpus/re-pin work, but a new exception and proof burden in both workflow and gate-script review; it cannot be treated as a mere workflow edit. |
| **C. Restart the pair from a fresh backend PR and fresh anchor.** Rebuild the backend candidate with the repairs and a reviewed corpus change, then have AIM repin it before the backend merge. | Can retain the same immutable-anchor rule, but yields no stronger proof than A. The already reviewed `A` stays historical evidence and must not be rewritten. | Repeats branch/PR setup and migration of review evidence; no smaller correct path is established. |

Choose **A**. A cosmetic manifest edit or duplicate vector is not a legitimate new anchor. The new row must catch an uncovered behavior and receive the existing §2.2 per-row raw-byte Council approval **before** its corpus files are copied to the committed backend tree. Candidate rows from §3.3 gaps include `extra-request-commitment`, a complete otherwise-valid request with an extra nested commitment member, and `envelope-model-v2-revoked-key`, a v2 bounded envelope carrying a revoked signer-key status (the initial inventory covers all statuses only in a v1 envelope). The author must validate the selected candidate against both live runners and use its exact error/type or accepted bytes; these names are proposals, not preapproved expected results. An accepting row needs its input diff, `.bin` hex diff, byte length, and SHA-256. A rejecting row needs its input diff, exact expected error type/code, and proof that no `.bin` exists. In either case review the complete changed `manifest.json` raw bytes and digest. Council approval must identify each added or changed row, the raw bytes where applicable, and the final manifest digest. Do not mutate an old row solely to obtain a digest change.

## 2. `A2` scope and acceptance

`A2` is a **new paired contract anchor**, not an exception to `A..HEAD` confinement. The backend PR stays held open. Let `D1` be the manifest digest at `A` and `D2` the newly reviewed digest at `A2`. The new anchor is declared only if `A2` descends from `A` and `5cf0e346`, its own first-parent corpus `manifest.sha256` differs from `A2`'s, the entire corpus/file set validates against `D2`, and both real runners and the independent Node checker agree. `D2` must differ from `D1`. The final backend tip must satisfy `anchor-diff` relative to `A2`: its post-`A2` diff contains only `preview-contract-aim-data.lock.json` and, if evidence requires it, `.github/workflows/preview-contract-cross-repo.yml`. Preserve `A` and `A2` as ancestors of the backend merge commit; never amend, rebase, or delete either after AIM pins it. A successful initial-installation classification must not stand in for the new-anchor and reverse-pin evidence on the held-open PR.

The reviewed `A2` commit must itself change the backend lock to **exactly** `{aim_data_sha: B, contract_anchor_sha: A, manifest_sha256: D2}`. `B` must already be reachable from AIM `main`; this lock does not claim the future `B2`. The single post-`A2` lock-only reverse-pin commit must change it to **exactly** `{aim_data_sha: B2, contract_anchor_sha: A2, manifest_sha256: D2}`. `B2` must be the actual AIM merge commit reachable from AIM `main`, and its own lock must be exactly `{backend_sha: A2, manifest_sha256: D2}`. No other post-`A2` contract path may change. Both the held-open PR event (whose base can precede `A`) and the backend merge push event must prove this same sequence from Git objects, not infer it from the live lock alone.

Modify `backend-transition` classification **inside reviewed `A2`**. Retain the initial `A` installation and `B/A/D1` reverse-pin rules. Add a distinct changed-manifest new-anchor branch that reads `A2`'s committed lock and first-parent corpus, verifies the exact `B/A/D2` anchor state and `A` ancestry, then accepts only the one `B2/A2/D2` reverse pin after `peer_lock` and AIM-main reachability checks. The present `old is None` reverse-pin branch at backend `224b85a4` requires the anchor's own lock to be initial `INITIAL_AIM/PLACEHOLDER/D1`; extend that classification for this reviewed `B/A/D2` anchor, rather than weakening the initial-anchor check or treating every changed lock as an anchor. A same-manifest replacement of `A` or `A2` fails `non_anchor_manifest_transition` or `non_anchor_pin_bump` as appropriate; an `A2` that does not descend from `A` fails `reverse_pin_anchor_missing`; an anchor lock other than exact `B/A/D2` fails `reverse_pin_anchor_lock_invalid`; a changed digest without a first-parent corpus transition fails `non_anchor_manifest_transition`; an unmerged `B2` fails `aim_data_sha_not_merged_to_main` before either runner. Keep `aim_lock_missing_or_not_anchor` for a `B2` lock that does not name `A2/D2`. The diagnostic unmerged-AIM mode remains non-required and cannot green the required job.

On AIM, `aim-transition` must accept `B2` only when its previous lock is `A/D1`, its new lock is `A2/D2`, the pinned backend checkout is exactly `A2`, `D2` verifies against the complete fetched corpus, and `A2`'s first-parent corpus manifest differs from `A2`'s. `B2` must be merged before the backend reverse pin can pass. Preserve `same_manifest_pin_bump` for an unchanged digest or unchanged backend SHA and `non_anchor_pin` for a backend commit whose first-parent manifest is unchanged; keep `peer_sha` and `lock_manifest_digest` failures for mismatched checkout or digest. Test both PR and push classifications. Required unit fixtures cover the exact `A` initial lock, `B/A/D1`, committed `A2` lock `B/A/D2`, `B2` AIM lock `A2/D2`, and final `B2/A2/D2`; add negative fixtures for a same-manifest bump, unmerged `B2`, missing `A` ancestry, malformed `A2` own lock, non-anchor corpus transition, wrong AIM peer SHA/digest, and unrelated post-anchor path changes. The positive fixtures must use full history and the exact pinned peer commits.

For every added or changed reviewed row, `A2` must register its ID and exact operation/model/expectation in the backend `ACCEPT` or `REJECT` inventory in `scripts/preview_contract_gate.py`; update `tests/test_preview_contract_cross_repo.py::test_manifest_exact_inventory_and_bytes` and every other exact total/accept/reject assertion to the counts recomputed from the reviewed manifest (initially 81 total, 36 accept, 45 reject). `B2` must register the same IDs in AIM `scripts/preview_contract_gate.py`'s closed `ACCEPT`/`REJECT` inventory and update `tests/test_preview_contract_cross_repo.py`'s exact 36/45 assertions and any other exact inventory counts. Neither side may accept an unknown ID or widen the inventory generally. Both `verify-manifest` commands must accept the exact reviewed IDs and `D2`; both focused suites must pass with **zero skipped tests** and their recomputed counts, and the paired transition and `anchor-diff` checks must retain protected-path confinement. These are gate and test changes only; no production model, serializer, or wire behavior changes are authorized.

Repair the two backend tests inside `A2`, with no production behavior change:

- For the initial-state assertion, read the lock from `A`'s committed tree (`git show A:preview-contract-aim-data.lock.json` or an equivalent immutable object read) and assert exactly `aim_data_sha=6529e1ed4d5983a87a9b1e2faadda32e18d4cf76`, `contract_anchor_sha=d5d2e3915fb5067e04b03dfe97716da380002b6b`, and the initial manifest digest. Separately read the live lock and accept **only** the one permitted follow-up `aim_data_sha=B`, `contract_anchor_sha=A`, same initial digest when exercising the existing reverse pin. After `B2`, add an exact `B2/A2/new digest` fixture; do not use an unconstrained set of SHAs or accept arbitrary future states.
- For `test_anchor_only_installation_fails_backend_transition_at_reverse_pin`, construct an actual anchor-only fixture from `A`'s tree and require `aim_lock_missing_or_not_anchor`. Exercise the reverse-pin checkout fixture separately and assert its own correct result. Do not demand the anchor-only error from a live working-tree lock that already names `B`.

Keep the two deferred DeepSeek Gate 3 `053438` LOWs deferred to the subsequent Gate 3 disposition. `A2` already needs a reviewed gate-script transition change, but the LOW fixtures do not repair this CI failure or enable the paired re-pin. Deferral keeps the security-critical `A2` review surface smaller, at the cost of a later review or reopening if Gate 3 requires the LOWs before close:

1. **LOW1:** explicit shallow-history rejection in `backend-transition`, with a focused shallow-checkout fixture whose visible tip otherwise looks valid.
2. **LOW2:** a post-anchor `app/services/listing_preview_disclosure.py` mutation fixture requiring `anchor-diff` refusal on the held-open PR.

The implementation review must verify the two fixed tests fail against the old broken state and pass against the initial, `B/A/D1`, and final `B2/A2/D2` states as applicable; the new vector is independently reproduced in both repositories; and the pre-existing mutation/protection evidence is retained. Track both deferred LOWs explicitly at Gate 3; do not silently mark them resolved. Any necessary implementation of this section belongs in the paired code PRs after this spec is approved. This document changes no code.

## 3. Replace Gate 2 §5.2 backend workflow

Only the backend workflow may be changed after `A` to repair CI infrastructure. Use a disposable PostgreSQL 16 service as in backend `test-gold-path.yml`. The backend app receives a synchronous `postgresql://` URL, which `app/core/database.py` converts to `postgresql+asyncpg://` for its async engine. `S1294_REQUIRE_POSTGRES=1` is the existing database-test fixture switch that fails instead of skipping when PostgreSQL cannot be reached. The preflight checks an actual connection before the regressions. The focused command also fails if any test in the three named files is skipped, so a changed skip reason cannot silently make the required job green. Do not change the AIM workflow's separate SQLite setting.

The exact replacement for §5.2 is:

```yaml
name: Preview contract cross-repo

on:
  pull_request:
  push:
    branches: [main]

permissions:
  contents: read

jobs:
  preview-contract-cross-repo:
    name: Preview contract cross-repo
    runs-on: ubuntu-latest
    timeout-minutes: 40
    services:
      postgres:
        image: postgres:16
        env:
          POSTGRES_USER: test
          POSTGRES_PASSWORD: test
          POSTGRES_DB: test
        ports:
          - 5432:5432
        options: >-
          --health-cmd "pg_isready -U test -d test"
          --health-interval 5s
          --health-timeout 5s
          --health-retries 10
    env:
      DATABASE_URL: postgresql://test:test@127.0.0.1:5432/test
      SECRET_KEY: preview-contract-ci-only-not-production
      S1294_REQUIRE_POSTGRES: '1'
    steps:
      - name: Checkout backend with anchor history
        uses: actions/checkout@v4
        with:
          fetch-depth: 0
          persist-credentials: false
      - name: Validate lock
        id: lock
        run: python scripts/preview_contract_gate.py lock --kind backend --file preview-contract-aim-data.lock.json --github-output "$GITHUB_OUTPUT"
      - name: Require target-only AIM Data key
        env:
          DEPLOY_KEY: ${{ secrets.PREVIEW_CONTRACT_AIM_DATA_READ_DEPLOY_KEY }}
        run: test -n "$DEPLOY_KEY"
      - name: Checkout pinned AIM Data
        uses: actions/checkout@v4
        with:
          repository: aidotmarket/aim-data
          ref: ${{ steps.lock.outputs.aim_data_sha }}
          path: peer/aim-data
          ssh-key: ${{ secrets.PREVIEW_CONTRACT_AIM_DATA_READ_DEPLOY_KEY }}
          fetch-depth: 0
          persist-credentials: false
      - name: Checkout AIM Data main for merge proof
        uses: actions/checkout@v4
        with:
          repository: aidotmarket/aim-data
          ref: main
          path: peer/aim-data-main
          ssh-key: ${{ secrets.PREVIEW_CONTRACT_AIM_DATA_READ_DEPLOY_KEY }}
          fetch-depth: 0
          persist-credentials: false
      - name: Verify pins, anchor, and manifest
        run: |
          test "$(git -C peer/aim-data rev-parse HEAD)" = "${{ steps.lock.outputs.aim_data_sha }}"
          if [ "$GITHUB_EVENT_NAME" = pull_request ]; then
            test "$(git rev-list --parents -n 1 HEAD | wc -w)" -eq 3
            test "$(git rev-parse HEAD^2)" = "${{ github.event.pull_request.head.sha }}"
          fi
          if ! git -C peer/aim-data-main merge-base --is-ancestor "${{ steps.lock.outputs.aim_data_sha }}" HEAD; then
            echo 'aim_data_sha_not_merged_to_main' >&2
            exit 1
          fi
          python scripts/preview_contract_gate.py verify-manifest --corpus tests/fixtures/preview/cross_repo_contract/v1 --expected "${{ steps.lock.outputs.manifest_sha256 }}"
          python scripts/preview_contract_gate.py backend-transition --event "$GITHUB_EVENT_PATH" --peer peer/aim-data --peer-main peer/aim-data-main
          CONTRACT_ANCHOR_SHA="${{ steps.lock.outputs.contract_anchor_sha }}" python scripts/preview_contract_gate.py anchor-diff
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - uses: actions/setup-node@v4
        with:
          node-version: '22'
      - name: Install isolated repositories
        run: |
          python -m venv /tmp/preview-contract/backend-venv
          /tmp/preview-contract/backend-venv/bin/pip install -r requirements.txt -r requirements-dev.txt
          python -m venv /tmp/preview-contract/aim-venv
          /tmp/preview-contract/aim-venv/bin/pip install --extra-index-url https://download.pytorch.org/whl/cpu -r peer/aim-data/requirements.txt -r peer/aim-data/requirements-dev.txt
          mkdir -p /tmp/preview-contract/data /tmp/preview-contract/uploads /tmp/preview-contract/processed /tmp/preview-contract/results
      - name: Run both implementations
        run: |
          /tmp/preview-contract/backend-venv/bin/python tests/preview_contract_runner.py --repo-root . --corpus tests/fixtures/preview/cross_repo_contract/v1 --output /tmp/preview-contract/results/backend.json
          /tmp/preview-contract/aim-venv/bin/python peer/aim-data/tests/preview_contract_runner.py --repo-root peer/aim-data --corpus tests/fixtures/preview/cross_repo_contract/v1 --output /tmp/preview-contract/results/aim-data.json
          /tmp/preview-contract/backend-venv/bin/python scripts/preview_contract_gate.py coverage --result /tmp/preview-contract/results/backend.json
          /tmp/preview-contract/aim-venv/bin/python peer/aim-data/scripts/preview_contract_gate.py coverage --result /tmp/preview-contract/results/aim-data.json
          /tmp/preview-contract/backend-venv/bin/python scripts/preview_contract_gate.py compare --corpus tests/fixtures/preview/cross_repo_contract/v1 --left /tmp/preview-contract/results/backend.json --right /tmp/preview-contract/results/aim-data.json
          node peer/aim-data/tests/preview_differential_check.cjs tests/fixtures/preview/cross_repo_contract/v1
      - name: Prove disposable PostgreSQL is reachable
        run: |
          /tmp/preview-contract/backend-venv/bin/python -c 'import os; from sqlalchemy import create_engine, text; engine = create_engine(os.environ["DATABASE_URL"]); conn = engine.connect(); conn.execute(text("SELECT 1")); conn.close(); engine.dispose()'
      - name: Focused regressions
        run: |
          /tmp/preview-contract/backend-venv/bin/python -m pytest -q -p no:cacheprovider -rs --junitxml=/tmp/preview-contract/results/backend-focused.xml tests/test_preview_contract_cross_repo.py tests/test_listing_preview_contracts.py tests/test_listing_preview_database.py
          /tmp/preview-contract/backend-venv/bin/python -c 'import sys, xml.etree.ElementTree as ET; root = ET.parse("/tmp/preview-contract/results/backend-focused.xml").getroot(); skipped = root.findall(".//testcase/skipped"); print(f"focused skipped tests: {len(skipped)}"); sys.exit(1 if skipped else 0)'
```

The JUnit check runs after a successful pytest command; pytest itself fails the step on collection errors or test failures. A missing or unreachable service also fails at the explicit connection preflight and, if reached later, through `S1294_REQUIRE_POSTGRES=1`. No skip in these three files counts as a green focused regression run.

## 4. Correct Gate 2 §6.1 credential proof

The AIM Data repository is **public**. The backend-held key's failure to read its holder repository (backend) is meaningful, but the AIM-held key cannot be proved holder-denied by reading public AIM Data. Replace §6.1's blanket “both keys fail holder read” claim and the §9 AC13 evidence row accordingly:

- For each key, prove the target SHA is readable with the isolated key and that the deploy-key ID is attached only to its named target repository, with `read_only:true` in the target deploy-key API read-back. Inspect the holder repository's deploy-key list and require that key ID absent. Public repository read success, including AIM Data, is not evidence that the key has broader authority.
- For each key, make a disposable, nonprotected branch push attempt **using only that key** against its target and require GitHub's `marked as read only` refusal. Record command exit status, refusal text, target slug, key ID, timestamp, and elapsed time since key creation for **every** attempt. If any attempt unexpectedly creates a probe ref, record its SHA and clean it up using a separately authorized write-capable credential such as `GITHUB_ORG_ADMIN_TOKEN` or the designated keyring credential; the read-only key cannot perform cleanup. Record the cleanup command, credential identity without secret value, timestamp, exit status, and absence read-back. Never treat an accepted push as proof of read-only scope.
- One push approximately two minutes after key creation was accepted and its branch was deleted; subsequent probes were refused. Thus repeat the write-refusal probe until the target refuses with `marked as read only`, recording every attempt and elapsed time. A fixed sleep or a single early response is insufficient. Keep the workflow blocked until the refusal and key-attachment/read-only API evidence agree. Do not push to `main` or any protected branch.
- On rotation, repeat the same positive target SHA, attachment/read-only read-back, and repeated target write-refusal checks for the replacement key before removing the old key. The backend-holder read denial may be retained as supplementary evidence where the holder is private; the public AIM direction has no holder-read denial requirement.

This changes only the credential **proof**, not key generation, target-only scope, secret placement, fork fail-closed behavior, protection, or the provider-authorization boundary.

The **exact replacement §9 AC13 row** is: `| AC13 | For each isolated key: positive target exact-SHA fetch; target-only deploy-key ID attachment with API read_only:true read-back and that ID absent from the holder repository's deploy-key list; timestamped disposable target write-probe attempts with elapsed time, exit status, refusal text, and any created probe-ref SHA plus cleanup/absence read-back by a separately authorized write-capable credential (GITHUB_ORG_ADMIN_TOKEN or designated keyring credential, never the read-only key); final marked as read only refusal; fork PR fail-closed job URL; no pull_request_target in either preview-contract workflow. Holder-read denial is optional supplementary evidence only for the private backend holder direction; it is not required for public AIM Data. |` The positive fetch must verify the requested commit SHA exactly, not just succeed against a branch name. A probe accepted before propagation keeps AC13 red until the unexpected ref is cleaned up and a later refusal is observed.

## 5. Bootstrap from the observed state

This is a **post-approval** execution sequence. Every mutating, code, workflow, credential, protection, merge, or other operational step below begins only after this Gate 2 amendment is approved; this proposed spec grants no authority to perform step 2 early. Read-only preservation and review of already obtained evidence may continue during authoring.

1. Retain AIM `B` on protected `main`, its green job, protection read-back, PR #81 failure, and administrator 405 refusal as already obtained evidence. Retain both deploy-key/Infisical/holder-secret installations; reconcile their proof against §4, repeating target write-refusal probes and recording elapsed times if the existing records do not meet it. Do not recreate or broaden a key just because public AIM read succeeds.
2. Keep backend PR #456 open and unmergeable. Apply the §3 workflow-only PostgreSQL correction; rerun the required job and record the exact failure that remains from the protected tests. This workflow edit is permitted after `A`; it does not redefine an anchor or waive red CI.
3. Implement and review `A2` on that same backend PR: fix the two tests, add the §2 new-anchor transition branch and exact fixtures, register each reviewed vector in the backend closed inventory, update all backend exact-count tests, and add and review at least one substantive corpus row under §2.2 before copying it into the committed tree. Verify `D2`, both runners, and the Node checker, then commit `A2` descending from `A` with its exact `B/A/D2` lock. Preserve the existing `B/A/D1` history. Backend remains held while AIM has not pinned `A2`.
4. Open an AIM Data PR from its protected `main` to pin `A2/D2`, register the same rows in AIM's closed inventory, and update all AIM exact-count tests. Its transition must classify `A2` as a genuine changed-manifest anchor. Obtain green required CI with zero skipped focused tests, raw-byte approval evidence, and the required review; merge AIM by its permitted method as `B2`. Read back the exact merged SHA and confirm AIM `main` is green. Do not substitute a branch tip for `B2`.
5. Add one backend post-`A2` reverse-pin follow-up naming `B2`, `A2`, and the exact `A2` digest. Require `backend-transition`, `anchor-diff`, both runners, the Node verifier, both `verify-manifest` commands, and the §3 focused regressions green with zero skipped focused tests on the held-open PR. Check `A` and `A2` ancestry and the post-`A2` path diff. Carry the two deferred LOWs into Gate 3 disposition.
6. Backend protection has **not** yet been applied. Only after its new required job is observed green, perform the existing Max-gated §6.2/§6.3 administrator protection step, read back the exact `Preview contract cross-repo` requirement and all retained checks/provider bindings, and prove a disposable failing backend mutation PR unmergeable by an administrator. No protection mutation is authorized by this authoring task.
7. With protection and Council Gate 3 evidence complete, merge backend **by merge commit** so `A` and `A2` remain ancestors. Confirm both `main` jobs green and record `A`, `B`, `A2`, `B2`, backend merge SHA, manifest digests, job URLs, mutation proof, protection read-backs, and credential proof in the existing runbook closeout. A green runbook index or this amendment alone is not a release receipt.

All other Gate 2 requirements remain unchanged.
