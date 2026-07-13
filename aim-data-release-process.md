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

### The version customers actually get is a PINNED DEFAULT — verify it after every release

`docker-compose.aim-data.yml` pins the image as `ghcr.io/aidotmarket/aim-data:${AIM_DATA_VERSION:-vX.Y.Z}`.
That literal default is what a fresh customer install pulls. It is **hand-maintained**, and it is the
single thing most likely to be left behind by a release.

`scripts/release-aim-data.sh` does bump it (`update_compose`, called by BOTH `cmd_rc` and `cmd_promote`).
**So the script is safe. Tagging by hand is not.** A tag pushed outside the script builds and publishes the
image, cuts the GitHub Release, and leaves the pinned default pointing at the PREVIOUS version. Nothing fails.
Nothing warns. Every new customer silently installs the old build.

**This has already happened.** Observed live S1207 (2026-07-13):

| Where | Version |
|---|---|
| Latest GitHub release | `aim-data-v1.22.2` |
| GHCR (image exists) | `v1.22.2` |
| Compose on `main` = what customers pull | `v1.22.1` |
| Installer served at get.ai.market | `v1.22.1` |
| Compose in the local product checkout | `v1.21.1` |

Three different versions in three places, and every fresh install for five days got a stale build.

**MANDATORY post-release check.** After any release, run this and confirm the served default matches the tag:

```bash
# what customers actually get, straight from the wire
curl -fsSL https://raw.githubusercontent.com/aidotmarket/aim-data/main/docker-compose.aim-data.yml \
  | grep -oE 'AIM_DATA_VERSION:-[^}]*'
# what the latest release actually is
curl -s https://api.github.com/repos/aidotmarket/aim-data/releases/latest \
  | python3 -c 'import sys,json; print(json.load(sys.stdin)["tag_name"])'
```

They must agree. If they do not, the release did not reach customers — bump the compose default, commit, push.

**Rules:**
- **Always release via `scripts/release-aim-data.sh`.** Never `git tag` an `aim-data-v*` release by hand.
- Never hand-edit the compose pin as a one-off "fix" — it drifts straight back. Fix the release path.
- **Preferred permanent fix (not yet built):** stop hand-maintaining the pin. Have the installer resolve the
  latest published release at install time, so a forgotten bump cannot ship a stale product. Until that exists,
  the check above is the guard.


## Repos

The AIM Data product split off from the vectoraiz monorepo. Release machinery now lives in the product repo itself — decoupled from the vectoraiz repo (S751). Product code, customer-facing installers, and the published Docker image live in the standalone repo.

- **Product repo (customer-facing code, installers, compose, INSTALL.md):** `aidotmarket/aim-data` — local at `/Users/max/aim-data`
- **Release script repo (`release-aim-data.sh`, tag bumping, GHA workflow inputs):** `aidotmarket/aim-data` — local at `/Users/max/Projects/ai-market/aim-data`
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
