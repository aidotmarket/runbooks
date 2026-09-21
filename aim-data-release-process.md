---
title: AIM Data Release Process
owner: unassigned
last_verified: '2026-09-21'
aliases: []
error_signatures: []
---

# AIM Data Release Process

## What it does

Builds and publishes new AIM Data versions. Creates GitHub releases, triggers GHCR Docker multi-arch builds, and runs smoke tests.

## How it works

```
scripts/release-aim-data.sh rc [patch|minor|major]
  → Creates RC (release candidate) tag with aim-data- prefix
scripts/release-aim-data.sh promote [vX.Y.Z-rc.N]
  → Promotes RC to stable release
  → GitHub Actions: builds Docker multi-arch images (AMD64 + ARM64)
  → Pushes to ghcr.io/aidotmarket/aim-data
  → Runs smoke test
  → Creates GitHub Release with install scripts
```

## Running a release

**From Vulcan (via run_background):**
```bash
export PATH="/opt/homebrew/bin:$PATH" && cd ~/Projects/ai-market/aim-data && scripts/release-aim-data.sh rc patch
```

**Important:** Always use `run_background` with explicit PATH prefix. CC does NOT have `gh` in PATH — never use CC for releases.

**Main-push guardrail (S1716, 2026-09-17):** the aim-data repo has a pre-push guardrail that refuses automated pushes to `refs/heads/main`. `rc` pushes usually pass because they add no main commit, but `promote` commits the three installer defaults to main and its atomic push is REFUSED with `GUARDRAIL: refusing push to refs/heads/main`. The script has already committed and tagged locally at that point. Complete the release as the deliberate reviewed push the guardrail names, atomically, from the instance running the release:

```bash
KD_ALLOW_MAIN_PUSH=1 git push --atomic origin main aim-data-vX.Y.Z
```

Then confirm the stable workflow started (`gh run list --workflow aim-data-release.yml --limit 1`). Push main and the tag in one atomic push so the release commit and its tag land together or not at all; a tag that lands without its release commit leaves the installer defaults on main pointing at the previous version until someone pushes main by hand.

**Installer URL lags the release by up to 24 hours unless you purge it (S1732, 2026-09-21):** `get.ai.market/aim-data`, `/aim-data/windows` and `/aim-data/docker-compose.yml` are served by the `get-ai-market` Worker from Workers KV (namespace `INSTALLERS`, id `6f25aeeb6a4a4cdcb31ccd45fc460605`, `KV_TTL = 86400` in `cf-get-worker/src/index.js`). The Worker only re-reads GitHub when a key is missing, so after a promote the installer keeps serving the previous stable version until the key expires. v1.25.1 was tagged at 09:45Z and `get.ai.market/aim-data` still said 1.25.0 an hour later, with the key due to expire at 20:10Z. After every `promote`, delete the three keys and re-check:

```bash
JWT=$(cat ~/.config/infisical/sysadmin-token | tr -d '\r\n')
T=$(infisical secrets get CLOUDFLARE_API_TOKEN --projectId bd272d48-c5a1-4b52-9d24-12066ae4403c --env prod --domain https://secrets.ai.market --token "$JWT" --plain --silent | tr -d '\r\n')
ACC=d5346d3e0f8f344c5f4915aaca689adf; NS=6f25aeeb6a4a4cdcb31ccd45fc460605
for k in aim-data/install.sh aim-data/install.ps1 aim-data/docker-compose.yml; do
  curl -sS -X DELETE --oauth2-bearer "$T" "https://api.cloudflare.com/client/v4/accounts/$ACC/storage/kv/namespaces/$NS/values/$k"
done
for p in aim-data aim-data/windows aim-data/docker-compose.yml; do curl -sS "https://get.ai.market/$p" | grep -m1 -oE "1\.[0-9]+\.[0-9]+"; done   # all three must print the new version
```

`npx wrangler kv key list` is NOT a reliable check here: unauthenticated it silently prints `[]` for this namespace. Use the API listing (`.../namespaces/$NS/keys`) if you need to see the keys and their `expiration`. If the Infisical session has lapsed (`infisical` starts an interactive login), run `~/bin/infisical_auth_refresh.sh` first; see `infisical-secrets.md`.

**Promotion window:** stable builds fresh from the tag, not from the RC image. Before `promote`, run `git fetch origin` and then `git log --oneline <rc-commit>..origin/main` (an empty result only counts after that fetch, with local `main` at `origin/main`); anything merged to main since the RC ships in the stable without having been in the RC smoke test. If that list is non-empty, either cut a new RC or record the decision to ship it (S1716: aim-data-v1.24.0 shipped S1717 B/C this way).

## Release types

| Command | Creates | Example |
|---------|---------|--------|
| `release-aim-data.sh rc patch` | RC tag | aim-data-v0.0.2-rc.1 |
| `release-aim-data.sh rc minor` | RC tag | aim-data-v0.1.0-rc.1 |
| `release-aim-data.sh rc major` | RC tag | aim-data-v1.0.0-rc.1 |
| `release-aim-data.sh promote` | Stable from latest RC | aim-data-v0.0.2 |

## Release version source of truth

`scripts/release-aim-data.sh` is the single update path for the customer-facing release default. During stable promotion, its `update_release_defaults` function rewrites all three consumers together:

- `docker-compose.aim-data.yml`
- `installers/aim-data/install.sh`
- `installers/aim-data/install.ps1`

The version remains embedded in each installer because `get.ai.market` serves each installer as a standalone script; it cannot depend on a separate version file that was not downloaded. RC creation leaves the customer defaults on the latest stable version. Stable promotion updates and commits all three, then atomically pushes `main` and the stable tag so CI sees the new stable tag with the matching defaults.

`.github/workflows/ci-release-integrity.yml` is the independent guard. On relevant pushes to `main`, it resolves the latest stable `aim-data-vX.Y.Z` tag and fails if the compose file, shell installer, or PowerShell installer does not reference that version. Treat any mismatch as a stopped release; do not waive the check as an in-progress release.

## GitHub Actions workflow

File: `.github/workflows/aim-data-release.yml`
Triggers on: push of `aim-data-v*` tags (namespaced to avoid VZ tag collision)

Jobs:
1. **build-push** — Multi-arch Docker build (amd64 + arm64) from `Dockerfile.customer`, pushes to GHCR
2. **smoke-test** — Verifies multi-arch manifest, pulls image, runs container, health check
3. **create-release** — Creates GitHub Release with `install.sh`, `install.ps1`, `docker-compose.aim-data.yml`

After `build-push` publishes the image, the workflow pulls that exact tag and inspects its `version` label. The label must exactly equal the version derived from the Git tag. Stable releases also fail explicitly if the label contains `-rc.`. `Dockerfile.customer` materializes the `VERSION` build argument before applying the label, so an RC runtime layer cannot be reused with stale metadata when the GitHub Actions cache is imported.

Stable promotion does not retag the RC image. The stable tag triggers a fresh workflow build of both `vX.Y.Z` and `latest`; the workflow creates the stable GitHub Release only after the published-label proof and smoke test pass. If the label check fails, stop and fix the build path on `main` before cutting a new version. Do not retag the RC image or publish `latest` manually.

## Testing an RC

The image tag is the bare version, **without** the `aim-data-` prefix that the git
tag carries: the git tag is `aim-data-v1.25.0-rc.1` and the image is
`ghcr.io/aidotmarket/aim-data:v1.25.0-rc.1`. The release script prints the image
line; use that rather than composing one from the tag.

The container listens on **8000**, and health is at **`/api/health`**, not `/health`
(corrected S1720 — the previous example said `-p 8080:8080` and `/health`, both of
which silently fail: the port never binds anything and `/health` returns
`{"detail":"Not Found"}`, which reads like a broken build rather than a wrong probe).

1. Wait for the GHCR build. `gh run view <id>` works, but space the calls out — S1720
   tripped GitHub's secondary rate limit polling a build every ten seconds and got
   403s on the Actions API while `gh api rate_limit` still reported 5000 core
   remaining. The registry is not affected by that limit, so
   `docker manifest inspect ghcr.io/aidotmarket/aim-data:<version>` is a cheaper
   readiness signal and also shows that both `linux/amd64` and `linux/arm64` landed.
2. Pull and run it:
   ```bash
   docker pull ghcr.io/aidotmarket/aim-data:v1.25.0-rc.1
   CID=$(docker run -d -p 18080:8000 ghcr.io/aidotmarket/aim-data:v1.25.0-rc.1)
   curl -s http://127.0.0.1:18080/api/health     # {"status":"ok","version":"v1.25.0-rc.1",...}
   docker rm -f $CID
   ```
   `/api/health` echoes the version it was built as, which is the cheapest proof that
   the image is the code you think it is. Probe one route that only exists in this
   release as well: a `401` says the route is there and authenticating, a `404` says
   the build predates it.

   **The container provisions a real serial against production on startup.** A test
   run auto-provisions and activates an install (`Auto-provisioned serial: VZ-…`),
   so every RC test leaves an activated install behind. Do not loop this.
3. If good, promote: `scripts/release-aim-data.sh promote`

## Installer

**Target URLs (via Cloudflare Worker at get.ai.market):**
```bash
curl -fsSL https://get.ai.market/aim-data | bash           # macOS/Linux
irm https://get.ai.market/aim-data/windows | iex            # Windows
```

**Status:** CF Worker routes — see [cloudflare-worker.md](cloudflare-worker.md) for current state.

## Repos

**Branches are not how work is preserved here.** The remote carries exactly one branch, `main`; everything ships from tags, and finished-with branches are archived as `archive/s<session>/<branch-name>` tags and then deleted from the remote. S1500 archived 32 that way. S1532 archived a further 17 that predated the convention and existed only on Titan-1, then cut the local clone back to `main`. If you are looking for old work, look at the tags, not the branches — and note that `git branch -r --contains <sha>` will not find it, because a tag is not a remote branch.

The AIM Data product split off from the vectoraiz monorepo. Release machinery now lives in the product repo itself — decoupled from the vectoraiz repo (S751). Product code, customer-facing installers, and the published Docker image live in the standalone repo.

- **Repo (product code, installers, compose, INSTALL.md, `release-aim-data.sh`, GHA workflow):** `aidotmarket/aim-data` — the ONE clone is at `/Users/max/Projects/ai-market/aim-data`. Corrected S1532: this used to be listed as two entries, splitting "product repo" from "release script repo", which read as two repositories when it is one, and pointed the first at `/Users/max/aim-data`. That path is NOT a checkout — it is the running customer-install demo directory (compose files and `.env`, no `.git`). The same mistake made the whole repository invisible to the open-items board in S1461, and `aim-data.md` has had it right all along (see its §Two directories) while this page contradicted it. A second clone that sat at `/Users/max/Projects/ai-market/aim-channel`, wearing the retired product name, was removed in S1532 (Max: "Remove aim-channel we only have aim-data"). Do not create another clone and do not point anything at `/Users/max/aim-data` for source.
- **Docker image:** `ghcr.io/aidotmarket/aim-data` (multi-arch amd64 + arm64)
- **Dockerfile:** `Dockerfile.customer` (lives in `aidotmarket/aim-data` and is what the GHA release workflow builds)
- **Compose file:** `docker-compose.aim-data.yml` at the root of `aidotmarket/aim-data`
- **Installers:** `installers/aim-data/install.sh` and `install.ps1` in `aidotmarket/aim-data`. Served at `get.ai.market/aim-data` and `get.ai.market/aim-data/windows` via the `get-ai-market` Cloudflare Worker (source: `aidotmarket/cf-get-worker`).

## When it breaks

| Symptom | Likely cause | Fix |
|---------|-------------|-----|
| `gh` not found | PATH not set | Add `export PATH="/opt/homebrew/bin:$PATH"` |
| GHCR build fails | ARM64 QEMU issue | Re-run GitHub Actions workflow |
| Docker pull fails | Image not built yet | Wait for GHA to complete |
| `get.ai.market/aim-data` still shows the previous version after promote | Workers KV `INSTALLERS` key not expired (24h TTL) | Delete the three `aim-data/*` keys via the Cloudflare API (see Promotion section) and re-check |
| Tag collision with VZ | Wrong script used | AIM Data uses `aim-data-v*` prefix, VZ uses `v*` |

## Release history worth remembering

- **aim-data-v1.25.0 (2026-09-20, S1720, Mars).** Shipped the S1294 Chunk 5B producer:
  AIM Data signs unchanged-root re-attestations, so a seller whose data has not changed
  can confirm a listing is still current instead of recomputing the whole Merkle root.
  Cut as `rc minor` because it adds a capability — the convention here is minor for
  features, patch for fixes, which is what v1.24.0 did for the S1717 chunks.
  RC `aim-data-v1.25.0-rc.1` from `a90cda3`; nothing merged to main between the RC and
  the promotion, so the promotion window was clean. The `promote` push hit the main
  guardrail exactly as documented above and was completed with
  `KD_ALLOW_MAIN_PUSH=1 git push --atomic origin main aim-data-v1.25.0`
  (main `e52471f`, workflow run 35532165037 success).
  Verified after the fact rather than assumed: both architectures in the manifest,
  `latest` moved, `ci-release-integrity` green on `e52471f`, the GitHub Release published
  with all three installer assets, the stable image's `/api/health` reporting `v1.25.0`,
  the new re-attest route answering `401` rather than `404`, and — the one that actually
  matters to a seller — the live installers at `get.ai.market/aim-data` and
  `/aim-data/windows` both serving `v1.25.0`.
  Build times for planning: the RC build took about 35 minutes and the stable about 40,
  in line with the two releases before it. Do not treat twenty minutes of silence as a
  stuck build.

## Related

- [aim-node-release-process.md](aim-node-release-process.md)
- [vz-release-process.md](vz-release-process.md)
- [cloudflare-worker.md](cloudflare-worker.md)
