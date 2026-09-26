---
title: Marketplace identity and contact policy
owner: mars
last_verified: '2026-09-27'
aliases: [seller identity, buyer identity, counterparty identity, seller branding, verified seller brand, anonymity policy, supplier arrangement, sold and licensed by ai.market]
error_signatures: []
---

# Marketplace identity and contact policy

This page is the current rule for what buyers and sellers learn about each other on ai.market. Authority: Max, S1753, 2026-09-27, Event Ledger `78777ec9`. It supersedes Max's anonymity decision `c3af20e0` and the licence-record decision `0b06e6fe` where they conflict with it. CORE P5 and S1 are unchanged: allAI mediates buyer-seller interaction and there is no direct off-platform channel.

## The rule

1. **Seller branding is the seller's choice.** A verified business seller may choose to show its approved business name, logo and credentials on its listings. Nothing is shown unless the seller opts in and ai.market has verified the business and approved what is displayed. Sellers who do not opt in stay anonymous: public surfaces show the `ai.market Seller` constant (see backend `runbooks/public-seller-anonymity.md`).
2. **No personal contact details on a listing.** Personal emails, phone numbers and direct contact links never appear on a listing, in listing metadata, JSON-LD, share cards, agent or MCP responses, even for a verified seller who shows its brand.
3. **All dealing stays in ai.market.** Enquiries, negotiation, payment, delivery, updates and support run through ai.market so the platform stays useful after the introduction.
4. **Buyers browse anonymously.** A seller never learns who is browsing, searching, asking or requesting data. Identities are disclosed only when the transaction or licence requires it.
5. **The licence names both parties.** The signed licence record already identifies both parties (backend `app/resources/licenses/standard-1.0.md` line 3). After purchase, each party's signed record shows the counterparty's legal name and jurisdiction. This replaces the earlier view where the counterparty appeared only as "identified to ai.market under order X".
6. **Supplier arrangements are labelled truthfully.** When ai.market sells data a supplier provides, the listing reads "Data supplied by [company]; sold and licensed by ai.market", naming the supplier only if it agrees. The supplier is never presented as the legal seller; ai.market is the seller and licensor.

## Current state versus the rule

The rule is decided; the product does not implement all of it yet. Until it does, do not describe unbuilt behaviour to customers as live.

| Rule | Shipped behaviour today | Gap |
|---|---|---|
| 1. Seller branding | Every public listing shows `ai.market Seller`; seller profile routes return 404 (S1737/S1740, backend `d78f2d08`) | Opt-in verified brand display (name, logo, credentials) with approval is not built |
| 2. No personal contact | Anonymous chat and buyer-request validators block contact details | Must also cover any new brand fields |
| 3. In-platform dealing | Terms 1.1 section 6 anti-circumvention; allAI carries communication | None for dealing. Terms 1.1 still say disputes are settled directly between the parties (see below) |
| 4. Buyer anonymity | Seller-facing responses and delivery tokens carry no buyer identifier (backend `runbooks/counterparty-anonymity.md`, S1740) | None |
| 5. Licence names both parties | Record stores both identities; each party's view shows only its own and "identified to ai.market under order X" (`runbooks/listing-licenses.md`) | Record views and PDF must show the counterparty's legal name and jurisdiction |
| 6. Supplier labelling | Not supported; the Standard licence names the seller as Licensor | Supplier listing label and an ai.market-as-licensor record are not built |

## Known conflict left open

Max chose to leave Terms 1.1 unchanged for now (`78777ec9`). These clauses conflict with the rule and stay recorded here until a Terms revision is decided: box 1 ("not a party to any transaction, it does not mediate deals"), box 3 and section 12.1-12.2 (disputes are strictly between buyer and seller, resolved directly, no mediation), and section 7.2 ("The licence ... is a contract between you and the Buyer. ai.market is not a party to it"), which does not fit a supplier arrangement where ai.market is the licensor.

## Superseded passages

Read these older documents through this page:

- `specs/ENTITLEMENT-BUYER-ID-ANONYMITY-S1740.md` "a seller never learns the buyer's identity": still true for browsing, delivery tokens and seller nodes; the signed licence record now names the buyer to the seller.
- `specs/BQ-AIM-DATA-GATEWAY-S1741-GATE2.md` anonymity bullet: a verified seller that opts in to branding may be named to buyers.
- `specs/BQ-LISTING-LICENSES-S1735-GATE2-AMENDMENT-1.md` sections 3 and 4 counterparty-reference-only record views.
- `specs/BQ-CONNECTOR-ACTION-PATH-GATE1.md` and `-GATE2.md` "seller view anonymised": still true for order lists; the licence record link shows both parties.
- `listing-slug-rename.md`: still the procedure for sellers who have not opted in to branding.

## When it breaks

- **Personal contact details found on a listing or public surface** (email, phone, direct link, including inside an approved brand field): remove them from the listing through the owner or admin edit path, tell Mars and Vulcan on the peer bus, and record the listing id. This is a breach of rule 2 whether or not the seller opted in to branding.
- **A seller name, logo or company appears publicly for a seller who did not opt in, or before verification and approval**: treat it as a regression of backend `runbooks/public-seller-anonymity.md`; run its verification steps and fix the leaking surface.
- **Any seller-facing response, notification or token carries a buyer identifier outside the signed licence record**: treat it as a regression of backend `runbooks/counterparty-anonymity.md`.
- **A review or spec cites "a seller never learns the buyer" or "the counterparty appears only as identified to ai.market" as a reason to hide the licence counterparty**: point it to rule 5 of this page.
