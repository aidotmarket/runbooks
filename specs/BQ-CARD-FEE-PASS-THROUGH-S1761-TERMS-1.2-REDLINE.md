# Terms 1.2 redline — S1761

**DRAFT — NEEDS MAX / LEGAL SIGN-OFF. Not legal advice. Not published.** Source: `aidotmarket/ai-market-backend origin/main@66109cdc681066bf05e99d3a43de368daa2d4c26`, `app/legal/terms_v1_1.md`. Each current passage is verbatim at the cited line. Proposed replacements apply only to the recommended **seller-bears** card-sale default. Buyer-bears and positive buyer-share split stay disabled pending separate legal sign-off, permitted-jurisdiction/card rules and publication. Preserve each existing order's accepted Terms version.

## Summary

**Current — `app/legal/terms_v1_1.md:19`:**
> - The buyer pays the transaction costs. That covers Stripe, stablecoin, and escrow fees. Our commission is 5% of the deal and it comes out of the seller's proceeds, not on top of the buyer's price.

**Replace:**
> - For a card sale of a seller listing, the seller pays the actual Stripe card processing fee from sale proceeds, in addition to our 5% commission. The buyer pays only the total shown before payment. Other payment methods have their separately disclosed terms and costs.

**Current — `app/legal/terms_v1_1.md:21`:**
> - Card money is held until the refund window closes, which is 90 days. If a buyer pays by card, the seller gets paid after that period passes, and the payment processor holds the money in the meantime, not us.

**Replace:**
> - For a seller-listing card sale, ai.market controls the captured proceeds in its Stripe platform balance and instructs a separate seller payout after delivery confirmation and the 48-hour post-confirmation hold. We may hold seller proceeds for up to 90 days during refund, dispute, fraud or legal review under Section 5.3. This is a payout hold, not a statement that every buyer has a 90-day refund right.

**Current — `app/legal/terms_v1_1.md:23`:**
> - Disputes are yours to sort out. Buyers and sellers handle disputes directly. We do not mediate. We only act on a court order. We will record that a transaction ended in a dispute, and that can lower a seller's quality score.

**Replace:**
> - Buyers and sellers resolve Data quality and licence disputes between themselves. ai.market may process card refunds and chargebacks, hold or adjust seller proceeds, and respond to payment disputes through Stripe as described below. We may record a dispute and reflect it in a seller's quality score. A court order is not required for those payment actions.

## Acceptance and definitions

**Current — `app/legal/terms_v1_1.md:39`:**
> - ☐ Box 1 — How the market works. I understand ai.market is non-custodial. It never touches, stores, or moves the data. It is not a party to any transaction, it does not mediate deals, and it does not guarantee that any dataset is accurate, lawful, or fit for purpose. The deal and its risks are between the buyer and the seller.

**Replace:**
> - ☐ Box 1 — How the market works. I understand ai.market never possesses, stores, hosts, transmits or moves the Data and is not a party to the buyer–seller Data licence. It does not guarantee any Dataset. For a seller-listing card sale, it controls captured proceeds in its Stripe platform balance and administers card payments, refunds, disputes, holds and seller payouts under these Terms.

**Current — `app/legal/terms_v1_1.md:43`:**
> - ☐ Box 3 — At my own risk, no legal action against ai.market. I understand that disputes are strictly between the buyer and the seller, that ai.market does not mediate them, and that by using the marketplace I give up and waive all legal recourse and all right to bring any claim or legal action against the ai.market Parties, and I waive any right to a jury trial and to bring or join a class action, to the maximum extent permitted by law (Section 13).

**Replace:**
> - ☐ Box 3 — At my own risk, subject to Sections 12 and 13. I understand that buyers and sellers resolve Data quality and licence disputes between themselves, while ai.market may administer card refunds, payment disputes, proceeds holds and seller payouts. I acknowledge the risk allocation and waivers in Section 13 to the extent permitted by law. **Legal must review the existing claim, jury and class waivers before publication; this draft does not validate them.**

**Current — `app/legal/terms_v1_1.md:61`:**
> 2.5 "Non-custodial" means we hold the index, the trust signals, and the billing metadata only. We never store, host, transmit, or take possession of the Data, and we do not hold customer funds.

**Replace:**
> 2.5 "Non-custodial" describes the Data: ai.market never stores, hosts, transmits or takes possession of the Data. For seller-listing card payments, ai.market controls captured proceeds in its Stripe platform balance and instructs refunds and later seller Transfers. "Non-custodial" does not mean that ai.market lacks control of those payment funds.

**Current — `app/legal/terms_v1_1.md:65`:**
> 2.7 "Refund Period" means 90 days from the date a transaction is paid, during which a Buyer may seek a refund or a card payment may be reversed.

**Replace:**
> 2.7 "Refund Period" refers to any refund or card reversal period that applies under the stated sale terms, applicable law or payment-network rules. It is separate from the ordinary 48-hour seller payout hold and from ai.market's right under Section 5.3 to hold seller proceeds for up to 90 days during a specific review. This definition does not grant an unconditional 90-day buyer refund right.

## Platform and payment terms

**Current — `app/legal/terms_v1_1.md:81`:**
> 4.2 We are non-custodial. We are the index and the billing layer. We are not a party to the licence between a Buyer and a Seller, we do not own or control the Data, we never take possession of it, and we do not hold customer funds.

**Replace:**
> 4.2 We provide the index and billing layer. We are not a party to the Data licence between Buyer and Seller; we do not own or control the Data and never possess it. For seller-listing card sales, the charge is captured on ai.market's Stripe platform account, where ai.market controls the proceeds until a refund or separate seller Transfer under Section 5.

**Current — `app/legal/terms_v1_1.md:87`:**
> 4.5 Communication runs through allAI. Buyer-seller discovery, search, and deal communication on the Platform are carried by allAI, and Buyers and Sellers agree not to arrange an on-platform transaction through direct off-platform contact. This is how the marketplace works and how translation between languages happens. This is separate from disputes: once a transaction has gone wrong, resolving the dispute is the parties' own responsibility (Section 12), and ai.market does not mediate it.

**Replace:**
> 4.5 Buyer–seller discovery, search and deal communication on the Platform run through allAI; Buyers and Sellers agree not to arrange an on-platform transaction through direct off-platform contact. They resolve Data quality and licence disputes directly, subject to ai.market's card-payment, refund and dispute duties in Sections 5 and 12.

**Current — `app/legal/terms_v1_1.md:91`:**
> 5.1 Commission. We charge a 5% Commission on the value of a successful transaction. We charge no listing fees. The Commission is deducted from the Seller's proceeds and is not added to the Buyer's price. The Seller therefore receives 95% of the listing price.

**Replace:**
> 5.1 Commission. We charge a 5% Commission on the listing price of a successful transaction, rounded down to whole cents. We charge no listing fee. For a seller-listing card sale, the Seller's amount before card fees is the listing price less Commission (normally 95%, subject to cent rounding). The payout statement shows the listing price, Commission, actual seller-paid Stripe card fee, any refunds or debt offsets, and the net seller Transfer. Refunds and disputes may reduce proceeds or create a Seller debt.

**Current — `app/legal/terms_v1_1.md:93`:**
> 5.2 Buyer pays transaction costs. The Buyer pays all transaction and processing costs on top of the price, including Stripe fees, stablecoin fees, and escrow fees. These costs are the Buyer's, not the Seller's and not ours.

**Replace:**
> 5.2 Card processing costs. For a seller-listing card sale, the Seller owes the actual Stripe card processing fee; ai.market first pays that fee from its platform Stripe balance and recovers it from Seller proceeds or a Seller receivable. The Buyer pays the displayed card total, with no added seller-sale card Processing fee under the current seller-bears policy. Terms and costs for stablecoin, escrow or other payment products are stated separately. No buyer-bears or split card-fee policy applies unless separately approved and published.

**Current — `app/legal/terms_v1_1.md:95`:**
> 5.3 Card funds held by the Payment Provider until the Refund Period passes (90 days, defined in 2.7). Where a Buyer pays by credit card, the Payment Provider holds or reserves the funds and does not release them to the Seller until the Refund Period has passed. ai.market does not hold these funds; it only instructs the Payment Provider to release them once the Refund Period closes. Release is also subject to chargebacks, reversals, provider rules, sanctions review, and legal holds. This protects against reversals and chargebacks while keeping ai.market non-custodial.

**Replace:**
> 5.3 Card proceeds and seller payout. For a seller-listing card sale, ai.market controls captured proceeds in its Stripe platform balance. After delivery is confirmed by the Buyer or automatically under the sale process, the ordinary seller payout hold lasts 48 hours from confirmation. Subject to the payout checks, ai.market then instructs a separate Stripe Transfer of the net amount due to the Seller. ai.market may hold Seller proceeds for up to 90 days during a refund, chargeback, dispute, fraud, sanctions or legal review, and may refuse a payout while the matter is unresolved. This is a contractual review right, not an automatic 90-day payout schedule or a guarantee that funds will be released on a fixed date. The Seller remains responsible for amounts owed under Sections 5.2 and 5.4.

**Current — `app/legal/terms_v1_1.md:97`:**
> 5.4 Payment methods and provider terms. Payments may be made by card (via Stripe), by stablecoin, or through escrow. You agree to the terms of the applicable Payment Provider. Payment Providers may perform identity and business verification, sanctions screening, reserves, reversals, refunds, chargebacks, wallet or address checks, and tax reporting.

**Replace:**
> 5.4 Payment methods, refunds and Seller debt. Payments may be made by card through Stripe or by separately offered stablecoin or escrow methods, subject to their applicable terms. Providers may verify identity and business status, screen sanctions, reserve or reverse funds, handle refunds and chargebacks, and report tax information. Stripe generally does not return the original processing fee when a card sale is refunded; the Seller remains liable for that retained fee, actual dispute or chargeback fees, and the amount lost on an adverse dispute. The Seller also owes any refund principal or fee that cannot be recovered from that sale's unpaid proceeds. ai.market may apply the sale's available proceeds first, then offset open debt against later payouts **to the same Seller**, suspend new listings while debt remains open, and seek payment or collection. Offsets never exceed the debt then owed. Suspension and collection do not guarantee recovery; an unpaid balance remains due unless expressly settled or written off through separate authorized accounting. Refunds to Buyers may be made through Stripe without a court order, subject to the sale terms and applicable law.

## Disputes

**Current — `app/legal/terms_v1_1.md:191`:**
> 12.1 Any dispute about a Dataset, its quality, its licence, payment, or a transaction is strictly between the Buyer and the Seller. They must first try in good faith to resolve it directly between themselves.

**Replace:**
> 12.1 Buyers and Sellers should first try in good faith to resolve Data quality, delivery and licence disputes directly. Card-payment refunds, chargebacks and payment-network disputes may also be handled by Stripe and ai.market under Sections 5.3 and 5.4.

**Current — `app/legal/terms_v1_1.md:193`:**
> 12.2 We do not mediate. ai.market does not mediate, arbitrate, or take sides in these disputes. We will act only where required to by a valid court order or legal process, and our involvement is limited to complying with that order.

**Replace:**
> 12.2 ai.market does not arbitrate the merits of the Data licence. It may investigate and respond to card-payment disputes, process or contest refunds and chargebacks through Stripe, hold or adjust proceeds, apply Seller debt offsets, and comply with law or legal process. These payment actions do not require a court order.

**Current — `app/legal/terms_v1_1.md:195`:**
> 12.3 Dispute record. We may record that a transaction resulted in a dispute. That record may be shown on the Platform and may affect a Seller's or a party's quality score. This keeps the marketplace honest for everyone.

**Replace:**
> 12.3 We may record a Data or payment dispute, its status and outcome; it may be shown on the Platform and affect a Seller's or other party's quality score, subject to applicable law and our review process.

**Publication gate:** Max and Legal must approve the complete Terms 1.2 wording, Seller debt/offset and collection authority, checkbox/waiver wording, checkout copy and acceptance flow. Publish and record acceptance before the seller-bears flag is enabled. Buyer-bears and split require a separate legal review of surcharging, geography/card eligibility, caps, disclosure and fee refunds.
