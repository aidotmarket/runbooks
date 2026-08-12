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

## Release types

| Command | Creates | Example |
|---------|---------|--------|
| `release-aim-data.sh rc patch` | RC tag | aim-data-v0.0.2-rc.1 |
| `release-aim-data.sh rc minor` | RC tag | aim-data-v0.1.0-rc.1 |
| `release-aim-data.sh rc major` | RC tag | aim-data-v1.0.0-rc.1 |
| `release-aim-data.sh promote` | Stable from latest RC | aim-data-v0.0.2 |

## GitHub Actions workflow

File: `.github/workflows/aim-data-release.yml`
Triggers on: push of `aim-data-v*` tags (namespaced to avoid VZ tag collision)

Jobs:
1. **build-push** — Multi-arch Docker build (amd64 + arm64) from `Dockerfile.customer`, pushes to GHCR
2. **smoke-test** — Verifies multi-arch manifest, pulls image, runs container, health check
3. **create-release** — Creates GitHub Release with `install.sh`, `install.ps1`, `docker-compose.aim-data.yml`

## Testing an RC

1. Wait for GHCR build to complete (check GitHub Actions)
2. Pull and test locally:
   ```bash
   docker pull ghcr.io/aidotmarket/aim-data:aim-data-v0.0.2-rc.1
   docker run -p 8080:8080 ghcr.io/aidotmarket/aim-data:aim-data-v0.0.2-rc.1
   ```
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
| Tag collision with VZ | Wrong script used | AIM Data uses `aim-data-v*` prefix, VZ uses `v*` |

## Related

- [aim-node-release-process.md](aim-node-release-process.md)
- [vz-release-process.md](vz-release-process.md)
- [cloudflare-worker.md](cloudflare-worker.md)
