# Docker Testing (VZ Local)

## What it does

Tests vectorAIz Docker images locally on Titan-1 via OrbStack before promoting to stable.

## Setup

Docker runs via OrbStack on Titan-1. Docker CLI at `~/.orbstack/bin/docker`.

## Testing an RC image

```bash
# Pull the RC
docker pull ghcr.io/aidotmarket/vectoraiz:v1.20.33-rc.1

# Or use docker-compose
cd ~/Projects/vectoraiz/vectoraiz-monorepo
docker compose -f docker-compose.customer.yml up
```

## Local VZ container

The customer test container runs locally. Currently on v1.20.31.

## Key files

| File | Purpose |
|------|--------|
| `Dockerfile.customer` | Customer-facing Docker image |
| `docker-compose.customer.yml` | Customer compose config |
| `docker-compose.yml` | Dev compose |
| `docker-compose.prod.yml` | Production compose |

## VZ imports

Local directory import uses sandboxed `~/vectoraiz-imports` mount.

## When it breaks

| Symptom | Fix |
|---------|-----|
| OrbStack not running | Open OrbStack app |
| Image not found | Wait for GHCR build (45-60 min) |
| MemoryError on ARM64 | onnxruntime remnants — `rm -rf` not `pip uninstall` |
| Semaphore leak | Fixed in recent versions — update image |
