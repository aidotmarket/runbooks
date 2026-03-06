# GCP Auth

## What it does

Manages Google Cloud authentication for Pub/Sub (Gmail pipeline) and any future GCP services.

## Accounts

| Account | Used for |
|---------|----------|
| `max@ai.market` | Production GCP project (`aimarket-prod`) |
| `maxdrobbins@gmail.com` | Personal GCP (no access to aimarket-prod) |

## Auth refresh

GCP tokens expire periodically. When they do:

```bash
gcloud auth login --account=max@ai.market
gcloud config set project aimarket-prod
```

This requires interactive browser login — Vulcan cannot do it headlessly.

## Verify setup

```bash
gcloud auth list                    # Check active account
gcloud config get-value project     # Should be: aimarket-prod
gcloud pubsub topics list           # Should show gmail-push
gcloud pubsub subscriptions list    # Should show gmail-push-sub
```

## When it breaks

| Symptom | Fix |
|---------|-----|
| "Reauthentication failed" | Run `gcloud auth login --account=max@ai.market` in terminal |
| "does not have permission" | Wrong account active — `gcloud config set account max@ai.market` |
| Wrong project | `gcloud config set project aimarket-prod` |
