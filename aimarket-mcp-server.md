# aimarket-mcp-server — Public MCP Integration

## What it is

Model Context Protocol (MCP) server that lets any LLM client (Claude, ChatGPT, etc.) search, evaluate, and purchase datasets from ai.market. Published on PyPI and npm.

**Repo:** [aidotmarket/aimarket-mcp-server](https://github.com/aidotmarket/aimarket-mcp-server)
**Local path:** `/Users/max/Projects/aimarket-mcp-server`
**Public:** Yes (open source)

## Tech stack

Python, MCP SDK, httpx (async HTTP client). Packaged via `pyproject.toml`.

## Architecture

```
LLM Client (Claude, etc.)
  └── MCP Protocol
        └── aimarket-mcp-server
              └── httpx → api.ai.market/api/v1/*
```

The MCP server acts as a thin protocol adapter. It translates MCP tool calls into REST API calls to the ai.market backend.

## Tools exposed to LLM clients

| Tool | Purpose | Backend endpoint |
|------|---------|------------------|
| `search_datasets` | Search the marketplace by query | `/api/v1/search` |
| `get_dataset` | Get full listing details | `/api/v1/listings/{id}` |
| `evaluate_dataset` | Quality/relevance assessment | `/api/v1/listings/{id}` + scoring |
| `preview_dataset` | Sample data preview | `/api/v1/listings/{id}/preview` |
| `check_wallet` | Check user's credit balance | `/api/v1/credits/balance` |
| `purchase_dataset` | Buy a listing | `/api/v1/checkout` |
| `list_orders` | View order history | `/api/v1/orders` |
| `get_order_data` | Download purchased data | `/api/v1/deliveries/{id}` |
| `verify_connection` | Test API connectivity | `/health` |

## Key files

| File | Purpose |
|------|--------|
| `src/aimarket_mcp/server.py` | MCP server — tool definitions and dispatch |
| `src/aimarket_mcp/client.py` | HTTP client — API calls to backend |
| `src/aimarket_mcp/config.py` | Configuration — API URL, auth |
| `src/aimarket_mcp/__main__.py` | Entry point |

## Configuration

Users configure via environment variables or MCP client settings:

| Variable | Purpose |
|----------|--------|
| `AIMARKET_API_KEY` | User's MCP API key (generated in dashboard settings) |
| `AIMARKET_API_URL` | Override API URL (default: `https://api.ai.market`) |

## Installation (end users)

```sh
pip install aimarket-mcp
# or
npx aimarket-mcp
```

## Release process

1. Update version in `pyproject.toml`
2. Push to main
3. Create GitHub release with tag
4. PyPI publish (manual or CI)

## Troubleshooting

| Problem | Diagnosis | Fix |
|---------|-----------|-----|
| "Connection refused" | Backend unreachable | Check `AIMARKET_API_URL`, verify `api.ai.market` is up |
| "Invalid API key" | Key not set or revoked | Generate new key in dashboard settings, set `AIMARKET_API_KEY` |
| Tool not found | MCP server version outdated | Update: `pip install --upgrade aimarket-mcp` |
| Search returns empty | Backend search issue | Test directly: `curl https://api.ai.market/api/v1/search?q=test` |
| Purchase fails | Credit balance or Stripe issue | Check wallet balance, verify Stripe configuration |

## Relationship to other repos

- **ai-market-backend:** The API this server calls. Any backend endpoint changes may break MCP tools.
- **MCP API keys:** Managed via `mcp_api_keys.py` endpoint and `mcp_key_service.py` in the backend.
- **koskadeux-mcp:** Separate — that's the internal Koskadeux orchestration MCP server, not the public marketplace one.

---

*Created: S363 (2026-04-01)*
