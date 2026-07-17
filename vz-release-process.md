# VZ Release Process

## What it does

Builds and publishes new vectorAIz versions. Creates GitHub releases, triggers GHCR Docker multi-arch builds. Also covers the Railway `vectoraiz-backend` production service deploy (auto-deploys from `aidotmarket/vectoraiz` main).

> **Release ownership (S1255/S1256, Max ruling A, decision event b65ee94d).** This repo's release lane publishes `ghcr.io/aidotmarket/vectoraiz` ONLY. The canonical `ghcr.io/aidotmarket/aim-data` image ships exclusively from the standalone `aidotmarket/aim-data` repo's own release train (see [aim-data-release-process.md](aim-data-release-process.md)); `docker-compose.aim-data.yml` here merely consumes it. Enforced by `ci-release-integrity.yml` (fails on any aim-data reference in workflows) and `tests/test_release_contract.py` (pins vectoraiz-only publishing in `release.yml` and `release.sh`). The corrective fold merged to main at `d8d8127` (S1256, GLM-approved); `release.sh promote` is unblocked. Known LOW gap: CI no longer scans `scripts/` for stray aim-data release scripts — the contract test covers `scripts/release.sh` only.

## How it works

```
scripts/release.sh [patch|minor|major|promote]
  → patch/minor/major: creates RC (release candidate) tag
  → promote: promotes latest RC to stable release
  → GitHub Actions: builds Docker multi-arch images (AMD64 + ARM64)
  → Pushes to ghcr.io/aidotmarket/vectoraiz (vectorAIz only; aim-data ships from its own repo)
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
3. If good, promote: `release.sh promote`

## Railway vectoraiz-backend service deploys (S1255)

The production service `vectoraiz-backend` (Railway project `vectorAIz` a9a69c43-a67b-438c-bce3-759e68c649e7, service 20a276f7-4dde-4f27-b3ba-087d7f17e014, environment `production` 3322a136-267b-4b91-a358-63797e8ab8d5) auto-deploys from `aidotmarket/vectoraiz` main. Health endpoint: `https://vectoraiz-backend-production.up.railway.app/api/health` (NOT `/health` — that 404s). Token and access policy: `infra:railway` in Living State (account-scoped token via `source /Users/max/bin/railway-env.sh`; bare python-urllib is Cloudflare-blocked, use httpx or the CLI).

Diagnosis pattern (verified S1255):
1. List recent deployments via GraphQL `deployments(input:{projectId,serviceId,environmentId})` — get id, status, commit.
2. Build logs via GraphQL `buildLogs(deploymentId:...)` or `railway logs --build <deployment-id> --lines 200` from the linked checkout.
3. A FAILED build stuck ~15-30 min with ZERO build logs is builder-side runner death, not code — especially on a docs-only commit. The prior SUCCESS deployment keeps serving; production is not down.
4. Recovery: trigger a rebuild of the same commit with GraphQL mutation `serviceInstanceDeployV2(serviceId, environmentId, commitSha)` (returns the new deployment id), then poll status and curl `/api/health`. A newer push to main supersedes the retry automatically (old deployment shows REMOVED).

| Symptom | Likely cause | Fix |
|---------|-------------|-----|
| Railway build FAILED, zero build logs, ~15-30 min duration | Railway builder/runner death (transient) | `serviceInstanceDeployV2` rebuild of the same commit; verify SUCCESS + `/api/health` 200 |
| `/health` returns 404 on vectoraiz-backend | Wrong path | Use `/api/health` |
| GHA release run FAILED with build-push step left `in_progress` and no step conclusion | GHA runner death mid-build (same transient class) | Re-run the workflow (post-fold the workflow is vectoraiz-only; safe to re-run) |

## Cloudflare installer proxy

`get.vectoraiz.com` proxies installer scripts:
- `/` routes to stable installer
- `/rc` routes to latest RC installer
- Cache: stable 5min, RC 2min

## When it breaks

| Symptom | Likely cause | Fix |
|---------|-------------|-----|
| `gh` not found | PATH not set | Add `export PATH="/opt/homebrew/bin:$PATH"` |
| RC cut with wrong version (e.g. `v0.0.1-rc.1`) | Local clone missing stable tags: `release.sh` resolves latest stable from local `git tag` only, so a tag-less clone yields current=0.0.0 (S1263 incident: bogus v0.0.1-rc.1 tag+prerelease+run, fully cleaned up) | ALWAYS run `git fetch origin --tags` before `release.sh rc`; verify the "Current stable" line the script prints before it pushes. If it already fired: cancel the tag's workflow run, `gh release delete <tag> --yes`, `git push origin :refs/tags/<tag>`, reset local main to origin |
| Compose bump commit not on remote main after release | KD pre-push guard blocks direct main pushes; `release.sh` swallows the failure (`|| true`) | The tag still drives the release, so the run is fine; push the release script's version-bump commit with `KD_ALLOW_MAIN_PUSH=1 git push origin main` (established release-process commit class, same as prior rc bumps) |
| GHCR build fails | ARM64 QEMU issue | Re-run GitHub Actions workflow |
| Accidental stable release | Used old release.sh | Ensure release.sh creates RC by default (fixed S222) |
| Docker pull fails | Image not built yet | Wait for GHA to complete (45-60 min) |
| `aim-data:latest` unexpectedly changed / customer installs pull an older AIM Data | A vectoraiz promote overwrote the standalone aim-data train's `:latest` | Re-promote the latest stable from `aidotmarket/aim-data` (`scripts/release-aim-data.sh promote`) to restore `:latest`; since the S1256 fold, a vectoraiz promote cannot touch aim-data (release ownership note above) |
| Railway `vectoraiz-backend` build failure email | See "Railway vectoraiz-backend service deploys" section above | Diagnose via GraphQL deployments + build logs; transient runner deaths get a `serviceInstanceDeployV2` rebuild |
