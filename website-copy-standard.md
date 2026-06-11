# Website Copy Standard

## §A. Header
**Owner surface:** ai.market public website (aidotmarket/ai-market-frontend) and all customer-facing marketing copy.
**Companion:** the write-like-max skill (Max's voice profile). This runbook is the site-copy addendum to it, approved by Max S811.
**Last verified:** 2026-06-11 (S811 content refresh, PR #28 / main ebcf0ae).

## §B. Capability Matrix
Applies to: page copy, headlines, CTAs, meta descriptions, og/twitter tags, structured data text, llms.txt phrasing, email/newsletter copy reused on the site.
Does not apply to: legal pages (Site Terms, Privacy), API reference text.

## §C. Architecture & Interactions
Visible copy and machine-readable metadata are one artifact. Any copy change ships with matching meta tags, JSON-LD, llms.txt, and sitemap updates in the same PR. An agent reading our structured data must get the same story a human gets. llms.txt and listing markdown endpoints are backend-generated (proxied via next.config); page meta and JSON-LD injection live in the frontend.

## §D. Agent Capability Map
Either instance authors and ships copy under this standard. Builders (MP) receive final copy verbatim in the dispatch prompt with the voice rules inlined; connective text a builder writes itself must pass the same rules. Verbatim verification against the diff before merge is mandatory.

## §E. Operate
Voice rules (inherits the full write-like-max banned list):
1. The site speaks as "we", never "I". Short sentences. Plain words.
2. Never use: delve, leverage, robust, comprehensive, seamless, unlock, empower, streamline, journey, game-changer, "Moreover", "Furthermore", "It's worth noting". No em-dashes or semicolons in customer copy.
3. Never signal small (Max directive S811): no "the big players", "the big aggregators", "even small teams like ours". Say "the aggregators". The audience is free to assume we are a billion-dollar company.
4. Every big claim gets its mechanics nearby. "Sell data without giving it away" is allowed because three steps under it show how. Never claim a capability that has not shipped.
5. CTAs are verbs, two or three words: Find Data, Sell Data, Post a Request. One primary action per section. Buyer and seller actions get equal weight on shared pages.
6. Every top-level page answers "what do I get" for its reader inside the first screen. The homepage answers it for both buyer and seller.
7. Discoverability is a budget line, not a feature (Max directive S811): communicate that listing on ai.market is global marketing the seller does not pay for. Buyers discover listings through AI assistants and search engines without visiting ai.market.
8. No copy baked into images. Strings stay in JSX/content constants. English is canonical until internationalization ships, then this standard applies per language.

## §F. Isolate
Copy reads as AI-written or off-voice: check against the write-like-max banned list first, then rules 1-3 above. Claim challenged as inaccurate: check rule 4 and the shipped-capability list before defending the copy.

## §G. Repair
Wrong copy live: fix on a branch, verify verbatim, merge. Meta/structured-data drift from visible copy: treat as a bug, fix both in one PR. Unshipped claim found live: remove the claim same day, no debate.

## §H. Evolve
New standing copy directives from Max get added to §E with a session reference and noted on the active content BQ. The standard is changed by replacement, not accretion.

## §I. Acceptance Criteria
A copy PR passes when: all final copy verified verbatim against the diff; zero banned-list hits; meta/og/twitter/JSON-LD/sitemap updated in the same PR; no unshipped claims; buyer and seller CTAs balanced on shared pages; build and lint pass.

## §J. Lifecycle
Created S811 as part of the website content refresh. Review whenever a content refresh BQ ships or Max issues a new copy directive.

## §K. Conformance
Registered in TOPIC-ROUTER.md under "Website copy / marketing". router_drift_check enforces the link.
