# VZ Release Process

## What it does

Builds and publishes new vectorAIz versions. Creates GitHub releases, triggers GHCR Docker multi-arch builds.

> **PROMOTE BLOCKED (S1255, pending Max ruling).** Since the S1253 hard-rename chunk (BQ-AIM-DATA-RENAME-UMBRELLA-S684 G2-C2), `scripts/release.sh` publishes every version tag to BOTH `ghcr.io/aidotmarket/vectoraiz` and `ghcr.io/aidotmarket/aim-data`, and a stable promote moves BOTH `:latest` aliases. The standalone `aidotmarket/aim-data` repo is a live second release train that owns `ghcr.io/aidotmarket/aim-data:latest` (v1.22.x line; the customer installer and compose pin it — see [aim-data-release-process.md](aim-data-release-process.md)). Promoting from this repo would overwrite the customer-facing `:latest` with an older-line (v1.20.x) image and downgrade fresh installs. Do NOT run `release.sh promote` until Max rules which repo owns the aim-data image and the corrective fold lands. RC releases are safe (version tags only, no `:latest` movement). Canonical status: `build:bq-aim-data-rename-umbrella-s684` body.ghcr_trains_conflict_s1255.

## How it works

```
scripts/release.sh [patch|minor|major|promote]
  → patch/minor/major: creates RC (release candidate) tag
  → promote: promotes latest RC to stable release
  → GitHub Actions: builds Docker multi-arch images (AMD64 + ARM64)
  → Pushes to ghcr.io/aidotmarket/vectoraiz
  → Since S1253 also pushes the same digest to ghcr.io/aidotmarket/aim-data (see PROMOTE BLOCKED note above)
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

Note the v2 script syntax is `release.sh rc [patch|minor|major]` and `release.sh promote [vX.Y.Z-rc.N]` (verified S1255).

## Testing an RC

1. Wait for GHCR build to complete (check GitHub Actions)
2. Pull and test locally:
   ```bash
   docker pull ghcr.io/aidotmarket/vectoraiz:v1.20.33-rc.1
   ```
3. If good, promote: `release.sh promote` — **currently blocked, see PROMOTE BLOCKED note above**

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
| `aim-data:latest` unexpectedly changed / customer installs pull an older AIM Data | A vectoraiz promote overwrote the standalone aim-data train's `:latest` | Re-promote the latest stable from `aidotmarket/aim-data` (`scripts/release-aim-data.sh promote`) to restore `:latest`, then escalate per the PROMOTE BLOCKED note |
