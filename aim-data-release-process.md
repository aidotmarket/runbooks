# AIM Data Release Process

## What it does

AIM Data is a standalone data processing component extracted from vectorAIz. Gets its own Docker image, install scripts, and download page.

## How it works

AIM Data lives in the vectoraiz monorepo (aidotmarket/vectoraiz) with its own Dockerfile and installer scripts.

```
Dockerfile.customer             -> Docker image
docker-compose.aim-data.yml     -> Compose file for end users
installers/aim-data/
  install.sh                    -> macOS/Linux installer
  install.ps1                   -> Windows installer
```

## Docker image

- **Image:** `ghcr.io/aidotmarket/aim-data`
- **Dockerfile:** `Dockerfile.customer` in vectoraiz monorepo root
- **Multi-arch:** amd64 + arm64

## Running a release

**Status:** GHA workflow NOT yet created (backlog).

Once created, the workflow should:
1. Trigger on `aim-data-v*` tags (namespaced to avoid VZ tag collision)
2. Build multi-arch image from `Dockerfile.customer`
3. Push to `ghcr.io/aidotmarket/aim-data:VERSION`
4. Smoke test
5. Create GitHub Release with install scripts

**Manual build (interim):**
```bash
cd ~/Projects/vectoraiz/vectoraiz-monorepo
docker build -f Dockerfile.customer -t ghcr.io/aidotmarket/aim-data:latest .
docker push ghcr.io/aidotmarket/aim-data:latest
```

## Installer

**Target URLs (via Cloudflare Worker at get.ai.market):**
```bash
curl -fsSL https://get.ai.market/aim-data | bash           # macOS/Linux
irm https://get.ai.market/aim-data/windows | iex            # Windows
```

**Status:** CF Worker routes NOT yet added (backlog).

## Download page

`ai.market/download` includes AIM Data download card.

## Repo

- **GitHub:** aidotmarket/vectoraiz (monorepo)
- **Local:** `/Users/max/Projects/vectoraiz/vectoraiz-monorepo`
- **Docker image:** `ghcr.io/aidotmarket/aim-data`

## Remaining work

- [ ] GHA workflow for Docker multi-arch builds
- [ ] Cloudflare Worker routes for get.ai.market/aim-data
- [ ] release.sh for AIM Data (or extend VZ release.sh)
- [ ] Smoke test in GHA workflow

## When it breaks

| Symptom | Likely cause | Fix |
|---------|-------------|-----|
| Docker build fails | Dockerfile.customer deps | Check build context |
| Installer 404 | CF Worker routes missing | Add routes to worker |
| Download page broken | Frontend links to missing routes | Verify routes first |

## Related

- [aim-node-release-process.md](aim-node-release-process.md)
- [vz-release-process.md](vz-release-process.md)
- [cloudflare-worker.md](cloudflare-worker.md)
