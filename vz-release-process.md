# VZ Release Process

## What it does

Builds and publishes new vectorAIz versions. Creates GitHub releases, triggers GHCR Docker multi-arch builds.

## How it works

```
scripts/release.sh [patch|minor|major|promote]
  → patch/minor/major: creates RC (release candidate) tag
  → promote: promotes latest RC to stable release
  → GitHub Actions: builds Docker multi-arch images (AMD64 + ARM64)
  → Pushes to ghcr.io/aidotmarket/vectoraiz
  → Takes 45-60 min due to QEMU/ARM64 emulation
```

## Running a release

**From Vulcan (via run_background):**
```bash
export PATH="/opt/homebrew/bin:$PATH" && cd ~/Projects/vectoraiz/vectoraiz-monorepo && scripts/release.sh patch
```

**Important:** Always use `run_background` with explicit PATH prefix. CC does NOT have `gh` in PATH — never use CC for releases.

## Release types

| Command | Creates | Example |
|---------|---------|--------|
| `release.sh patch` | RC tag | v1.20.33-rc.1 |
| `release.sh minor` | RC tag | v1.21.0-rc.1 |
| `release.sh major` | RC tag | v2.0.0-rc.1 |
| `release.sh promote` | Stable from latest RC | v1.20.33 (from v1.20.33-rc.1) |

## Testing an RC

1. Wait for GHCR build to complete (check GitHub Actions)
2. Pull and test locally:
   ```bash
   docker pull ghcr.io/aidotmarket/vectoraiz:v1.20.33-rc.1
   ```
3. If good, promote: `release.sh promote`

## Cloudflare installer proxy

`get.vectoraiz.com` proxies installer scripts:
- `/` routes to stable installer
- `/rc` routes to latest RC installer
- Cache: stable 5min, RC 2min

## When it breaks

| Symptom | Likely cause | Fix |
|---------|-------------|-----|
| `gh` not found | PATH not set | Add `export PATH="/opt/homebrew/bin:$PATH"` |
| GHCR build fails | ARM64 QEMU issue | Re-run GitHub Actions workflow |
| Accidental stable release | Used old release.sh | Ensure release.sh creates RC by default (fixed S222) |
| Docker pull fails | Image not built yet | Wait for GHA to complete (45-60 min) |
