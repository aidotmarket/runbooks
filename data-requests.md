# data-requests — Buyer-initiated Data Request Surface

## What it is

The data-request feature lets a buyer post a "I'm looking for X kind of data" listing and receive responses from sellers. Lifecycle: a buyer drafts a request, publishes it to the public board, sellers reply with proposals, the buyer picks a winning response and the flow proceeds to payment + fulfillment via the standard listing/order pipeline.

**Customer-facing entry point:** `ai.market/requests/new` (create) and `ai.market/requests` (browse the public board).

## Repos and code map

| Layer | Repo | Path |
|---|---|---|
| Backend endpoints | aidotmarket/ai-market-backend | `app/api/v1/endpoints/requests.py` |
| Backend service | aidotmarket/ai-market-backend | `app/services/data_request_service.py` |
| Backend schema | aidotmarket/ai-market-backend | `app/schemas/data_request.py` |
| Backend model | aidotmarket/ai-market-backend | `app/models/data_request.py` |
| Frontend create page | aidotmarket/ai-market-frontend | `app/requests/new/page.tsx` |
| Frontend browse page | aidotmarket/ai-market-frontend | `app/requests/page.tsx` |
| Frontend detail page | aidotmarket/ai-market-frontend | `app/requests/[slug]/page.tsx` |
| Frontend dashboard view | aidotmarket/ai-market-frontend | `app/dashboard/requests/page.tsx` |
| Frontend API client | aidotmarket/ai-market-frontend | `api/data-requests.ts` |
| Frontend types | aidotmarket/ai-market-frontend | `types/index.ts` (DataRequest*, CreateDataRequestPayload) |

## Backend API surface (under `/api/v1/data-requests`)

| Method | Path | Purpose |
|---|---|---|
| POST | `/data-requests` | Create draft request (auth required) |
| GET | `/data-requests` | List + filter (auth-aware visibility) |
| GET | `/data-requests/{slug_or_id}` | Detail |
| PATCH | `/data-requests/{request_id}` | Edit draft |
| POST | `/data-requests/{request_id}/publish` | Move from draft → open |
| DELETE | `/data-requests/{request_id}` | Close / cancel |
| POST | `/data-requests/{request_id}/responses` | Seller responds with a proposal |
| GET | `/data-requests/{request_id}/responses` | List responses (visibility scoped) |
| PATCH | `/data-requests/{request_id}/responses/{response_id}` | Edit response |
| POST | `/data-requests/{request_id}/messages` | Message thread between buyer + responder |

## Lifecycle states

`draft` → `open` → `responses_received` → `fulfilled` | `closed` | `expired`

A draft is private to the buyer. Once published it's visible on the public board. As responses come in the state advances. Final terminal states are `fulfilled` (a response was accepted and the order pipeline took over), `closed` (buyer cancelled), or `expired` (TTL elapsed).

## The contract — fields that MUST match between frontend and backend

This is where bugs live. Every field below is a known drift hotspot. When changing any of these on the backend, the frontend MUST be updated in the same release window.

| Field | Backend (Pydantic) | Frontend (TypeScript) | Notes |
|---|---|---|---|
| `description` | `str`, `min_length=20`, `max_length=10000` | `string` (required) | Front-end SHOULD validate min length client-side to avoid round-trip 422s |
| `urgency` | `str`, pattern `^(low\|normal\|high\|urgent)$`, default `"normal"` | `DataRequestUrgency = 'low' \| 'normal' \| 'high' \| 'urgent'` | Was previously typed `'medium'` on frontend; corrected S574. Default value MUST match backend pattern. |
| `categories` | `Optional[List[str]]` | `string[] \| undefined` | Frontend splits comma-separated input. |
| `format_preferences` | `Optional[List[str]]` | `string[] \| undefined` | Was previously typed `string` on frontend; corrected S574. Frontend splits comma-separated input. |
| `price_range_min` | `Optional[Decimal]`, `>= 0` | `number \| undefined` | Backend rejects max < min |
| `price_range_max` | `Optional[Decimal]`, `>= 0` | `number \| undefined` | Backend cross-validates against min |
| `currency` | `str`, default `"USD"`, `max_length=3` | `string \| undefined` | |
| `regulatory_requirements` | `Optional[List[str]]` | `string[] \| undefined` | |
| `provenance_requirements` | `Optional[str]` | `string \| undefined` | |

## Known issues + history

### Resolved S574 — multi-bug data-request form failure (white-screen on submit)

**Symptom:** Customer (max@kisa.cat) submitted the create form at `ai.market/requests/new` and saw "Application error: a client-side exception has occurred while loading ai.market".

**Five connected bugs:**
1. Form defaulted `urgency: 'medium'`, but backend pattern only accepts `low|normal|high|urgent`. Every default-urgency submission was 422'd at the backend.
2. Frontend's catch block toasted the FastAPI Pydantic 422 `detail` field directly. That field is `Array<{type, loc, msg}>`. Passing an array of objects as a React text child throws "Objects are not valid as a React child" — the white-screen exception.
3. `format_preferences` was sent as a raw string. Backend declared `Optional[List[str]]`. Latent bug; would 422 the moment a user filled the field.
4. The `DataRequestUrgency` type itself listed `'medium'` instead of `'normal'` — the deeper root cause that explains why bug 1 existed.
5. Three other pages (`app/dashboard/requests/page.tsx`, `app/requests/[slug]/page.tsx`, `app/requests/page.tsx`) had `URGENCY_BADGE: Record<DataRequestUrgency, string>` maps with `medium:` keys.

**Fix:** ai-market-frontend PR #1 (commits c8442ff, b125dd6, 9d480e0; merged via a271a1e). Aligned types with backend, fixed default value, made error handler defensive across string/array/object detail shapes, renamed map keys.

**Tracked under:** `BQ-FRONTEND-TYPES-FROM-BACKEND-OPENAPI-S574` (the architectural follow-on to prevent the next round of type-drift bugs).

## Diagnostic procedures

### Customer reports "form submission produced an error page"

1. Get the timestamp of the submission attempt.
2. Tail backend logs filtered for the `/data-requests` POST:
   ```sh
   cd /Users/max/Projects/ai-market/ai-market-backend
   railway logs --service ai-market-backend 2>&1 | grep -E "POST /api/v1/data-requests" | tail -10
   ```
3. If the POST returned `422 Unprocessable Entity`: it's a validation failure. Look for the request body in the logs (will not show by default) or reproduce in `/docs` interactive Swagger UI to see the exact validation error.
4. If the POST returned `200`: the failure is downstream — the response was successful but the frontend choked on something. Open browser console on the failing page; look for the actual JS error.
5. If no POST is in the logs: the failure is frontend-side before submission. Check browser console for the JS error.

### Reproducing a 422 against current production

```sh
# Get an auth token (replace with a real session token)
TOKEN="<bearer-token>"

curl -X POST 'https://api.ai.market/api/v1/data-requests' \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"description":"test description that is at least twenty characters long","urgency":"normal"}'
```

The response body on a 422 is a Pydantic auto-shape: `{"detail": [{"type":..., "loc":["body","field"], "msg":"...", ...}]}`. Frontend now handles all three observed detail shapes (string, array, object) without crashing.

## Cross-references

- `ai-market-backend.md` — broader backend service runbook
- `ai-market-frontend.md` — broader frontend service runbook
- BQ-FRONTEND-TYPES-FROM-BACKEND-OPENAPI-S574 — type-generation BQ to prevent future drift
- BQ-BACKEND-422-RESPONSE-SHAPE-UNIFICATION-S573 — backend 422 contract cleanup

---

*Created: S574 (2026-05-06) — initial runbook capturing the resolved form-submission incident chain plus the contract surface between backend and frontend.*
