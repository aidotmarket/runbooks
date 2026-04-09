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
export PATH="/opt/homebrew/bin:$PATH" && cd ~/Projects/vectoraiz/vectoraiz-monorepo && scripts/release-aim-data.sh rc patch
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

## Repo

- **GitHub:** aidotmarket/vectoraiz (monorepo)
- **Local:** `/Users/max/Projects/vectoraiz/vectoraiz-monorepo`
- **Docker image:** `ghcr.io/aidotmarket/aim-data`
- **Dockerfile:** `Dockerfile.customer` in monorepo root
- **Compose file:** `docker-compose.aim-data.yml`
- **Installers:** `installers/aim-data/install.sh`, `installers/aim-data/install.ps1`

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
