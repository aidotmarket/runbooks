# AIM Node Release Process

## What it does

Builds and publishes new AIM Node versions. Creates GitHub releases, triggers GHCR Docker multi-arch builds, and runs smoke tests.

## How it works

```
scripts/release.sh rc [patch|minor|major]
  -> Creates RC (release candidate) tag
scripts/release.sh promote [vX.Y.Z-rc.N]
  -> Promotes RC to stable release
  -> GitHub Actions: builds Docker multi-arch images (AMD64 + ARM64)
  -> Pushes to ghcr.io/aidotmarket/aim-node
  -> Runs smoke test (manifest verify + health check)
  -> Creates GitHub Release with install scripts
```

## Running a release

**From Vulcan (via run_background):**
```bash
export PATH="/opt/homebrew/bin:$PATH" && cd ~/Projects/ai-market/aim-node && scripts/release.sh rc patch
```

**Important:** Always use `run_background` with explicit PATH prefix. CC does NOT have `gh` in PATH -- never use CC for releases.

## Release types

| Command | Creates | Example |
|---------|---------|--------|
| `release.sh rc patch` | RC tag | v0.0.2-rc.1 |
| `release.sh rc minor` | RC tag | v0.1.0-rc.1 |
| `release.sh rc major` | RC tag | v1.0.0-rc.1 |
| `release.sh promote` | Stable from latest RC | v0.0.2 |

## GitHub Actions workflow

File: `.github/workflows/docker-build.yml`
Triggers on: push of `v*` tags

Jobs:
1. **build-push** -- Multi-arch Docker build (amd64 + arm64), pushes to GHCR
2. **smoke-test** -- Logs into GHCR, verifies multi-arch manifest, pulls image, runs container, hits `/api/mgmt/health`
3. **create-release** -- Creates GitHub Release with `install.sh`, `install.ps1`, `docker-compose.aim-node.yml`

## Testing an RC

1. Wait for GHCR build to complete (check GitHub Actions)
2. Pull and test locally:
   ```bash
   docker pull ghcr.io/aidotmarket/aim-node:v0.0.2-rc.1
   docker run -p 8080:8080 ghcr.io/aidotmarket/aim-node:v0.0.2-rc.1
   curl http://localhost:8080/api/mgmt/health
   ```
3. If good, promote: `scripts/release.sh promote`

## Installer

`get.ai.market/aim-node` proxies the installer script from GitHub:
```bash
curl -fsSL https://get.ai.market/aim-node | bash
```

## Repo

- **GitHub:** aidotmarket/aim-node
- **Local:** `/Users/max/Projects/ai-market/aim-node`
- **Docker image:** `ghcr.io/aidotmarket/aim-node`

## When it breaks

| Symptom | Likely cause | Fix |
|---------|-------------|-----|
| `gh` not found | PATH not set | Add `export PATH="/opt/homebrew/bin:$PATH"` |
| GHCR build fails | ARM64 QEMU issue | Re-run GitHub Actions workflow |
| Smoke-test GHCR login denied | Escaped dollar signs in workflow YAML | Ensure expressions are NOT backslash-escaped |
| Docker pull fails | Image not built yet | Wait for GHA to complete |

## Related

- [aim-node.md](aim-node.md)
- [vz-release-process.md](vz-release-process.md)
- [cloudflare-worker.md](cloudflare-worker.md)
