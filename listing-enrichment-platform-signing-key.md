---
title: Listing Enrichment Platform Signing Key (verified previews)
owner: unassigned
last_verified: '2026-09-18'
aliases: [platform signing key, preview signing key, LISTING_ENRICHMENT_SIGNING, transparency keys 503]
error_signatures: ["transparency/keys HTTP 503 Preview unavailable", "signing_configuration_unavailable", "signing_key_unavailable", "signing_key_invalid", "signing_environment_not_allowed"]
---

# Listing Enrichment Platform Signing Key

## What it does

The backend signs verified-preview artefacts (transparency log checkpoints, preview platform envelopes, approval decisions under BQ-LISTING-ENRICHMENT-SELLER-TOOLS-S1294) with one Ed25519 key. The public half is served at `GET /api/v1/public/transparency/keys` so browsers verify the platform envelope before trusting any seller key. Without this key T-backend fails closed: the keys route returns 503 and every sample approval is refused. The key was first provisioned on 2026-09-18 (S1716, Max decision Event Ledger 040cc446).

## Where the pieces live

| Setting | Where | Value shape |
|---|---|---|
| `LISTING_ENRICHMENT_SIGNING_KEY_ID` | Infisical prod `/` (synced to Railway) | key id: 1-255 chars matching `^[A-Za-z0-9._:-]+$`; MUST also be a key in `LISTING_ENRICHMENT_SIGNING_PUBLIC_KEYS`; current `aim-preview-platform-2026-09` |
| `LISTING_ENRICHMENT_SIGNING_PUBLIC_KEYS` | Infisical prod `/` (synced to Railway) | JSON object `{"<key_id>": "<public key>"}` where each value is the raw 32-byte Ed25519 public key in UNPADDED base64url (43 chars, no `=`), every key id valid per the pattern, and no two ids carrying the same key bytes; may hold several keys during rotation |
| `LISTING_ENRICHMENT_INFISICAL_SIGNING_KEY_NAME` | Infisical prod `/` (synced) | `LISTING_ENRICHMENT_SIGNING_PRIVATE_KEY_PEM` |
| `LISTING_ENRICHMENT_INFISICAL_SECRET_PATH` | Infisical prod `/` (synced) | `/listing-enrichment-signing` |
| `LISTING_ENRICHMENT_SIGNING_PRIVATE_KEY_PEM` | Infisical prod `/listing-enrichment-signing` only | PKCS8 PEM of the Ed25519 private key. This folder is outside the Infisical→Railway sync on purpose: the backend fetches the key from Infisical at signing time (`app/services/transparency_log_service.py`, `InfisicalEd25519Signer`) using the existing `INFISICAL_TOKEN` / `INFISICAL_PROJECT_ID`; the private key must never appear as a Railway variable |

Generated private keys also exist on Titan-1 at `~/.config/aim-signing/<key_id>.pem` (mode 600) as the operator copy; delete after a rotation is confirmed.

## Provisioning or rotating (headless, sysadmin token)

Runbook rule: `infisical-secrets.md` (raw v3 API with `~/.config/infisical/sysadmin-token`; never the bare CLI from a non-interactive shell).

1. Generate a new key on Titan-1:
   ```bash
   umask 077; cd ~/.config/aim-signing
   ~/Projects/ai-market/ai-market-backend/.venv/bin/python - <<'PY'
   from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
   from cryptography.hazmat.primitives import serialization
   import base64
   KEY_ID = "aim-preview-platform-YYYY-MM"
   k = Ed25519PrivateKey.generate()
   open(f"{KEY_ID}.pem","wb").write(k.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()))
   raw = k.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
   open(f"{KEY_ID}.pub","w").write(base64.urlsafe_b64encode(raw).rstrip(b"=").decode())
   PY
   ```
2. Preflight first: `GET /api/v3/secrets/raw?workspaceId=<project>&environment=prod&secretPath=<path>&viewSecretValue=false` and match each secret by EXACT name (`secretKey` equality, not a substring). Then create only secrets that are confirmed absent with `POST /api/v3/secrets/raw/<NAME>` and update existing ones with `PATCH /api/v3/secrets/raw/<NAME>` (same workspaceId, environment, secretPath, type `shared`; build request bodies in memory, never in shell history). All rotation writes are updates unless the preflight proves absence. Private key: name `LISTING_ENRICHMENT_SIGNING_PRIVATE_KEY_PEM`, `secretPath` `/listing-enrichment-signing`. For rotation, first add the NEW public key to `LISTING_ENRICHMENT_SIGNING_PUBLIC_KEYS` (keep the old one), let the sync land and the service redeploy, then switch `LISTING_ENRICHMENT_SIGNING_KEY_ID` and replace the private secret. Remove the old public key only after every checkpoint signed with it has been superseded (see the T contract, signer_keys rotation rules).
3. Write (POST if absent, PATCH if present, per the same preflight) the four `/`-path settings with `secretPath` `/`. The Infisical→Railway sync (`railway-backend-prod`, auto-sync ON) pushes them; Railway redeploys the backend automatically on variable change (observed ~2 minutes).
4. Verify:
   ```bash
   curl -s https://api.ai.market/api/v1/public/transparency/keys   # 200, profile aim-preview-platform-keys-v1, your key id present
   ```
   and confirm the private key did NOT sync: list Railway variables and check no `*PRIVATE_KEY*` name exists.

## When it breaks

- Keys route 503 `Preview unavailable`: `LISTING_ENRICHMENT_SIGNING_KEY_ID` unset or not present in `LISTING_ENRICHMENT_SIGNING_PUBLIC_KEYS`; a key id failing the pattern or length; a public key that is padded, non-canonical base64url, or not exactly 32 raw bytes; or two ids carrying identical key bytes.
- `signing_configuration_unavailable`: one of `LISTING_ENRICHMENT_INFISICAL_SIGNING_KEY_NAME`, `INFISICAL_TOKEN`, `INFISICAL_PROJECT_ID` or `LISTING_ENRICHMENT_SIGNING_KEY_ID` empty at signing time; check all four, the code tests them together.
- `signing_environment_not_allowed`: `LISTING_ENRICHMENT_INFISICAL_ENVIRONMENT` not in `INFISICAL_ALLOWED_ENVS`.
- `signing_key_unavailable` / `signing_key_invalid`: Infisical fetch failed, secret missing at the configured path, or the PEM is not Ed25519.

## History

- 2026-09-18 (S1716): first key `aim-preview-platform-2026-09` provisioned; keys route went from 503 to 200 on Railway deployment 0b8612ee.
