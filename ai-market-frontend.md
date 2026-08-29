---
title: ai-market-frontend — Marketplace Web App
owner: unassigned
last_verified: '2026-08-25'
aliases: []
error_signatures: []
---

# ai-market-frontend — Marketplace Web App

> Content refresh S811 (PR #28): dual-audience homepage and buyer landing. AIM Federate is retired, with no current public surface, route, redirect, or asset; reintroduction requires explicit Max decision. Copy is governed by [website-copy-standard.md](website-copy-standard.md).

## What it is

Next.js frontend for ai.market — the customer-facing marketplace where buyers search/purchase datasets and sellers list/manage their offerings.

**Repo:** [aidotmarket/ai-market-frontend](https://github.com/aidotmarket/ai-market-frontend)
**Live:** `ai.market`
**Local path:** `/Users/max/Projects/ai-market/ai-market-frontend`
**Hosting:** Railway (Nixpacks build)

## Tech stack

Next.js (App Router), React, TypeScript, Tailwind CSS, Zustand (state), Axios, React Query.

## Deployment

Railway auto-deploys from `main`. Build via Nixpacks (`nixpacks.toml` in repo root). DNS: `ai.market` → Railway service.

**Verify deploy:**
```sh
curl -s -o /dev/null -w "%{http_code}" https://ai.market
```

## Pages (App Router)

| Route | File | Purpose |
|-------|------|--------|
| `/` | `app/page.tsx` | Homepage / landing |
| `/login` | `app/login/page.tsx` | Login with OAuth buttons |
| `/auth/verify` | `app/auth/verify/page.tsx` | Magic link verification |
| `/forgot-password` | `app/forgot-password/page.tsx` | Password reset |
| `/listings` | `app/listings/page.tsx` | Browse all listings |
| `/listings/[slug]` | `app/listings/[slug]/page.tsx` | Single listing detail |
| `/dashboard` | `app/dashboard/page.tsx` | User dashboard (catch-all) |
| `/dashboard/listings` | `app/dashboard/listings/page.tsx` | Seller: manage listings |
| `/dashboard/sales` | `app/dashboard/sales/page.tsx` | Seller (active only): read-only sales list on `GET /seller/orders`; nav entry hidden until capabilities resolve `active`; buyers redirected to `/dashboard/inquiries` (S1589, BQ-SELLER-SALES-SURFACE-S1581) |
| `/dashboard/orders` | `app/dashboard/orders/page.tsx` | Buyer: purchase history — heading and nav renamed "Purchases" for both roles (S1589); URL unchanged; the bare "Orders" nav label is retired |
| `/dashboard/orders/[id]` | `app/dashboard/orders/[id]/page.tsx` | Order detail, served to buyer-of-record OR seller-of-record (backend 403 otherwise). Every action, fetch and download frame is gated on the viewer's relationship to THIS order (`user.id` vs `order.buyer_id`/`seller_id`), never global account role; the `?tx=` transaction renders only when its `order_id` matches the route order (S1590, T-2026-000688, Q2 rule from BQ-SELLER-SALES-SURFACE-S1581) |
| `/dashboard/inquiries` | `app/dashboard/inquiries/page.tsx` | allAI mediated inquiries |
| `/dashboard/requests` | `app/dashboard/requests/page.tsx` | Data requests |
| `/dashboard/settings` | `app/dashboard/settings/page.tsx` | Account settings, Stripe connect |
| `/find-data` | `app/find-data/page.tsx` | Buyer landing (refreshed S811) |
| `/sell-data` | `app/sell-data/page.tsx` | Seller landing (refreshed S811) |
| `/protocol` | `app/protocol/page.tsx` | Protocol mechanics + security |
| `/aim-data` `/aim-node` | `app/aim-data/` `app/aim-node/` | Product pages |
| `/download` | `app/download/` | Install paths (incl. retired /download/aim-channel route) |
| `/requests` `/search` `/blog` `/partner` | respective `app/` dirs | Requests, search, blog (Keystatic), partner |
| `/aim-federate` `/run-federated-learning` (retired) | No route, redirect, or asset | No current public surface; reintroduction requires explicit Max decision |
| `/dashboard/stripe-return` | `app/dashboard/stripe-return/page.tsx` | Stripe onboarding callback |
| `/checkout/success` | `app/checkout/success/page.tsx` | Post-purchase confirmation |
| `/checkout/cancel` | `app/checkout/cancel/page.tsx` | Checkout cancelled |
| `/download` | `app/download/page.tsx` | Secure file download |
| `/legal/privacy` | `app/legal/privacy/page.tsx` | Privacy policy |
| `/legal/site-terms` | `app/legal/site-terms/page.tsx` | Terms of service |

## Key directories

| Path | Purpose |
|------|--------|
| `app/` | Next.js App Router — pages and layouts |
| `components/` | Shared React components |
| `components/allai/` | allAI chat/inquiry widgets |
| `components/search/` | Search UI components |
| `components/publish-wizard/` | Seller listing creation flow |
| `api/` | API client functions (Axios) |
| `hooks/` | Custom React hooks |
| `lib/` | Utilities, helpers |
| `store/` | Zustand state stores |
| `types/` | TypeScript type definitions |
| `public/` | Static assets (images, robots.txt, sitemap) |

## API connection

Backend URL configured via `NEXT_PUBLIC_API_URL` (authoritative source is the **Railway `ai-market-frontend` service variable** — Next.js inlines `NEXT_PUBLIC_*` at build; the committed `.env` is gitignored and does NOT drive the Railway build).

**MUST be `https://api.ai.market`, never the raw Railway host (`…up.railway.app`).** The refresh cookie is `SameSite=Lax`, so the API must be the same site as `ai.market` or the browser withholds the cookie and every reload logs the user out. Full reasoning + verification: [browser-session-auth.md](browser-session-auth.md). API rewrites configured in `next.config.ts` for AI discovery endpoints.

## Configuration

| Variable | Purpose |
|----------|--------|
| `NEXT_PUBLIC_API_URL` | Backend API base URL — MUST be `https://api.ai.market` (same-site as the web app; see browser-session-auth.md). Set on the Railway frontend service. |
| `API_URL` | Server-side API URL (same) |

## SEO

Sitemap at `/sitemap.xml` (generated). `robots.txt` in `public/` directory includes backend listings sitemap. Google Search Console configured.

## Authenticated inquiry rejection result

`components/InquiryWidget.tsx` must leave an authenticated failed submission with a persistent visible result beside the form. Preserve the backend `detail` only when it is a string; structured FastAPI validation details must use the fixed fallback instead of becoming React children. The alert uses `role="alert"`, the typed question remains available for revision, the submit button is restored in `finally`, and the persistent state clears only when the customer starts the next submission. The existing toast may remain, but a timed toast alone is not sufficient evidence because it can disappear before a slow backend response is rendered.

Verify both the exact mediation 422 string and an array-valued validation 422 in `components/InquiryWidget.test.tsx`, then run `tsc --noEmit`. Final production proof must use the authenticated `mediation-contact-leak-probe` charter through the E2E harness; it must complete both the plain and disguised attempts and visibly show the held result for each.

**T-2026-000698 proof (2026-08-24):** frontend candidate `648a232537086ec29013859eb57ad78fbdfb031b`, merge `cc7fc0d069ac83fa331d6ad339de0e65a73a2b88`, Railway deployment `4ea6a792-b13f-4715-bdd9-5a6ef702dc05`, and production E2E run `run-20260824T183519Z-9f8666bb` (passed with no findings).

## Marketplace search reset

The **Clear all** control in `components/search/MarketplaceSearchExperience.tsx` clears the complete URL-driven search state, including `q`, `type`, category, price, format, and sort. It must navigate to the current marketplace pathname with no query string; preserving `q` leaves a customer trapped in the same zero-result state.

Verify this at phone size through the sanctioned `kdbrowser` GUI runner with real Chrome: open `https://ai.market/listings?q=financial+markets` at 390×844, confirm the zero-result state, activate **Clear all**, then require the URL to become `https://ai.market/listings`, the search input to be empty, and a non-zero catalog result count to be visible.

**T-2026-000708 proof (2026-08-25):** frontend candidate `81797ab2afd2e0ae2eac95265eba8a5ec3920fc7`, merge `ac3a15a7646a6dcd6b41ed45335ac9d44c00ed96`, Railway deployment `78fc9b57-d1a6-495a-98bb-a0d281d7c480` (`SUCCESS` at the exact merge SHA), and an isolated `kdbrowser` real-Chrome acceptance at 390×844 that observed 0 results before the action and the restored unfiltered catalog at `/listings` after it.

## When it breaks

| Problem | Diagnosis | Fix |
|---------|-----------|-----|
| White screen / 500 | Check Railway deploy logs | Fix build error, push to main |
| API calls failing | Check `NEXT_PUBLIC_API_URL` | Verify env var in Railway |
| Listings not showing | Backend search endpoint issue | Check backend `/api/v1/search` |
| **Clear all** leaves the same search or zero-result state visible | The handler preserved one or more URL search parameters instead of removing the full query string | Inspect `MarketplaceSearchExperience.tsx`; require navigation to the current pathname without query parameters, then repeat the phone-sized `kdbrowser` Chrome acceptance above |
| OAuth not working | Google client ID mismatch | Check `GOOGLE_CLIENT_ID` in both frontend env and backend |
| Styles broken after deploy | Tailwind purge issue | Check Tailwind config, redeploy |
| Authenticated inquiry stays on **Submitting...** or the rejection disappears | Correlate the browser transcript with the backend `message_audit` timestamp; inspect the persistent authenticated alert path | Run `mediation-contact-leak-probe`; fix the backend post-audit latency or the frontend persistent-result path according to the evidence, then require both attempts to pass |

---

*Created: S363 (2026-04-01)*
