---
# Runbook: Dual-Brand System — vectorAIz / AIM Channel

## Product Taxonomy

ai.market has four products:

| Product | Type | Purpose |
|---------|------|---------|
| **ai.market** | Marketplace | Non-custodial P2P AI model and dataset marketplace |
| **AIM Node** | CLI tool (pip) | Compute plane — sellers host models/pipelines, buyers invoke them |
| **vectorAIz** | Desktop app | Internal AI for enterprises — local data processing behind the firewall, with trojan-horse marketplace features |
| **AIM Channel** | Desktop app | Data plane — ai.market-branded skin of vectorAIz, focused on marketplace data channel use case |

## Critical Rules

1. **vectorAIz and AIM Channel share the same codebase** (vectoraiz monorepo) but are DIFFERENT products with DIFFERENT brands.
2. **vectorAIz is NOT being renamed.** It retains its own name, brand, website (vectoraiz.com), and positioning.
3. **AIM Channel is a brand skin**, not a fork. Brand differences are controlled at runtime via the channel/theme system.
4. **Never modify vectorAIz-specific branding** when doing AIM Channel work. All brand content is conditional.
5. **Brand selection is runtime**, not build-time. Controlled by VITE_BRAND env var or hostname detection (*.ai.market → AIM Channel, everything else → vectorAIz).

## Codebase Architecture

### Brand Config (src/lib/brandConfig.ts)
- Defines BrandConfig type and two brand instances: VECTORAIZ_BRAND, AIM_CHANNEL_BRAND
- getActiveBrand() determines which brand is active based on env var / hostname

### Brand Context (src/contexts/BrandContext.tsx)
- React context providing active brand to all components
- useBrand() hook for accessing brand config

### Brand Detection Order
1. VITE_BRAND env var (explicit: "vectoraiz" or "aim-channel")
2. Hostname detection (*.ai.market → aim-channel)
3. Default: vectoraiz

## What's SHARED (same in both brands)
- All features, functionality, and backend logic
- localStorage keys (vectoraiz_api_key, vectoraiz_api_url, etc.)
- Package names (package.json: vectoraiz-frontend)
- API paths (/api/vectors/, /api/datasets/, etc.)
- Internal imports and component names
- Docker infrastructure

## What's DIFFERENT per brand
- Product name (vectorAIz vs AIM Channel)
- Logo files and favicon
- HTML meta tags (title, description, og:tags, twitter)
- Welcome/onboarding copy
- External links (vectoraiz.com vs ai.market)
- Settings page descriptions
- Sidebar branding
- Login page branding

## Deployment

### vectorAIz
- Deployed via Docker (customer-hosted behind firewall)
- VITE_BRAND not set or set to "vectoraiz"
- Domain: customer-controlled, or dev.vectoraiz.com for dev

### AIM Channel
- Deployed from ai.market infrastructure
- VITE_BRAND=aim-channel (or hostname detection handles it)
- Domain: TBD subdomain of ai.market

## Common Mistakes to Avoid
- DO NOT rename vectoraiz repos, packages, or env vars for AIM Channel work
- DO NOT use find-and-replace on "vectorAIz" — use the brand config system
- DO NOT hardcode brand strings in new components — always use useBrand()
- DO NOT confuse the useChannel hook (feature-level channel detection) with the brand system (product-level branding)

## Council Hall Decision (S425)
Names decided by Council Hall consensus: MP + AG unanimous, Vulcan concurred.
- "AIM Node" kept for compute (static endpoint in P2P network)
- "AIM Channel" chosen for data (dynamic path feeding the marketplace)
- Rejected: AIM Data (generic/trademark), AIM Gateway (asymmetric pairing), AIM Vault (HashiCorp collision), AIM Desktop (form factor), AIM Enclave (environment not function), AIM Bridge (weaker)
---
