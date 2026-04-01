# ai-market-frontend — Marketplace Web App

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
| `/dashboard/orders` | `app/dashboard/orders/page.tsx` | Buyer: order history |
| `/dashboard/inquiries` | `app/dashboard/inquiries/page.tsx` | allAI mediated inquiries |
| `/dashboard/requests` | `app/dashboard/requests/page.tsx` | Data requests |
| `/dashboard/settings` | `app/dashboard/settings/page.tsx` | Account settings, Stripe connect |
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

Backend URL configured via `NEXT_PUBLIC_API_URL` in `.env`. Points to `api.ai.market` (Railway internal URL in production). API rewrites configured in `next.config.ts` for AI discovery endpoints.

## Configuration

| Variable | Purpose |
|----------|--------|
| `NEXT_PUBLIC_API_URL` | Backend API base URL |
| `API_URL` | Server-side API URL (same) |

## SEO

Sitemap at `/sitemap.xml` (generated). `robots.txt` in `public/` directory includes backend listings sitemap. Google Search Console configured.

## Troubleshooting

| Problem | Diagnosis | Fix |
|---------|-----------|-----|
| White screen / 500 | Check Railway deploy logs | Fix build error, push to main |
| API calls failing | Check `NEXT_PUBLIC_API_URL` | Verify env var in Railway |
| Listings not showing | Backend search endpoint issue | Check backend `/api/v1/search` |
| OAuth not working | Google client ID mismatch | Check `GOOGLE_CLIENT_ID` in both frontend env and backend |
| Styles broken after deploy | Tailwind purge issue | Check Tailwind config, redeploy |

---

*Created: S363 (2026-04-01)*
