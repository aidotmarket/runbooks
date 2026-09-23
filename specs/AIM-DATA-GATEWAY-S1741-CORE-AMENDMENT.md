# CORE amendment: AIM Data becomes the self-hosted gateway (S1741)

**Proposed version:** 9.21. **Base:** CORE v9.20, `docs/core/CORE.md` in ai-market-backend at `75c8be5031669bc807e567c1cfdae17c93bd17e7`. The file is byte-identical to Living State `infra:constitution` (sha256 `2916cb9dcaf162942763faac3db8b1e5e260ce9476da7d0b81b8184238939868`, the boot kernel's `source_constitution_sha256`).
**Authority:** Max S1741, Event Ledger `904bacc0` and `308570bd`. Max approves the direction here and must still approve this exact wording after the Council vote (`constitution-amendment.md` E-02). **Gate:** unanimous GLM, DeepSeek and Gemini (CORE §5). MP reviews without a vote (CORE §4: MP "Available for explicit review dispatch, but not a gate voter").
**Companion design:** [BQ-AIM-DATA-GATEWAY-S1741-GATE1.md](BQ-AIM-DATA-GATEWAY-S1741-GATE1.md). This amendment and that Gate 1 are voted in the same round and neither passes without the other.

**R2 changes to the proposed text** (R1 on `062577e8`: DeepSeek found the amendment clean; Gemini F4 NIT):
- Line 54 now reads "vectorAIz (dataset manifests)" (Gemini F4).
- The "IS" bullet says the gateway sends nothing identifying until the seller chooses to (design D9, two-phase).
- The "IS NOT" bullet says the gateway reads only what the customer mounts into it (design D6: no cloud SDK in v1).

**R3 changes to the proposed text** (R2 on `833c2dba`: GLM NIT 4, DeepSeek F5):
- Lines 64–65 (vectorAIz) are added, because they still said vectorAIz uploads "the same way AIM Data does" and called it "the AIM Data conduit".
- The "IS" bullet no longer says "single-use": each permission is for one file of one order, and the design allows bounded resume.

**What changes in substance:**
- AIM Data stops being a management GUI, a developer CLI/SDK/MCP surface and a host for allAI agents. It becomes a gateway with three functions.
- "Outbound connections only" becomes "outbound only to ai.market's control plane, plus the one delivery endpoint the customer chooses to expose" (Max `308570bd`).
- The "encrypted relay" wording is removed: `data-delivery-p2p.md` already forbids relays.
- The AIM Data "allAI key" line is removed, because allAI runs on ai.market over the metadata the gateway sends.
- The product repository becomes `aidotmarket/aim-data-gateway`.
- Programmatic and agent access is stated as ai.market's own surface.

**Unchanged:** P1 (marketplace → engine → conduits; two co-equal customer-facing data products), P2, S1, the public-sample exception, vectorAIz, and every safety rule. The boot kernel's P7 and P8 are regenerated from the amended text by the normal kernel projection, and the result stays within the kernel character budget.

Each change below gives the exact old text (CORE v9.20 line numbers) and the exact new text. Nothing else in CORE changes except the version header, which gains a v9.21 line citing this amendment, the vote and Max's approval.

## CORE v9.20 line 48

**Old:**

```text
- **MUST integrate with:** allAI (mediation, search, agent-facing discovery, listing generation), AIM Data (receives metadata + listing manifests; serves both the non-dev GUI and developer/programmatic buy/sell/request surfaces), vectorAIz (receives Qdrant-format dataset uploads and their listing manifests)
```

**New:**

```text
- **MUST integrate with:** allAI (mediation, search, agent-facing discovery, listing generation), AIM Data (pairs sellers' self-hosted gateways, receives their listing metadata and delivery receipts, and issues their signed download permissions), vectorAIz (receives Qdrant-format dataset uploads and their listing manifests)
```

## CORE v9.20 line 54

**Old:**

```text
- **MUST integrate with:** ai.market (mediation, listing generation, agent-facing answers), AIM Data and vectorAIz (the customer-side data products where allAI's work happens on real data sources, including programmatic developer access), Koskadeux (dev memory)
```

**New:**

```text
- **MUST integrate with:** ai.market (mediation, listing generation, agent-facing answers), AIM Data (allAI classifies and enriches the structural metadata a seller's gateway sends; it never receives the data itself), vectorAIz (dataset manifests), Koskadeux (dev memory)
```

## CORE v9.20 line 56-61

**Old:**

```text
### AIM Data — The Conduit
- **IS:** **A conduit, not a worker.** The conduit through which **allAI's metadata generation, classification, and listing work reaches the customer's data sources**, serving two audiences from one product. For non-technical users: a customer-hosted desktop GUI (Docker app running locally at the customer site) surfacing data-source profiling, PII management, metadata review and approval, listing publication, monitoring, and a request inbox. For developers operating at scale: a programmatic surface — pip-installable Python package + CLI + MCP server + SDK — giving programmatic access to all four marketplace functions (buy, sell, develop/integrate, request) and to allAI's listing/metadata work, plus peer-to-peer data transfer between buyer and seller nodes; the MCP server makes the marketplace and allAI accessible to AI agents. When in connected / approved mode, hosts ai.market agents that run on the customer's data sources to validate quality scores and assist metadata generation. Agents only run with explicit customer approval per data source.
- **IS NOT:** A cloud service or model host. Runs on the customer's / participant's own infrastructure; outbound connections only — works behind any firewall. Never phones home with customer data. **Not the worker — the worker is allAI.**
- **Data plane:** Non-custodial. The programmatic surface forwards opaque frames over an encrypted relay (ChaCha20-Poly1305, per-session ephemeral keys); ai.market handles the control plane and metering metadata only — never data plane content.
- **MUST integrate with:** ai.market (metadata publishing via Trust Channel, agent dispatch in connected mode, session negotiation, metering, billing, relay routing), allAI (the engine of customer value; programmatic listing generation, classification, mediation)
- **allAI key:** Metered allAI access, billed to customer. Only available in connected mode (ai.market proxied key).
```

**New:**

```text
### AIM Data — The Gateway
- **IS:** The self-hosted gateway for sellers who keep their data on their own infrastructure, shipped as a hardened Docker sandbox under an open-source licence so the customer's security team can inspect every line that runs inside their perimeter. It does three things only: it describes the seller's data where it sits to ai.market with structural metadata only (never data values, and nothing identifying until the seller chooses to send it), plus a public sample only when the seller explicitly chooses one; it serves purchased files directly to the buyer through a single delivery endpoint that the seller's own IT exposes, admitting only download permissions signed by ai.market, each for one file of one order; and it reports each delivery to ai.market for billing and payout. Everything else a seller does (listing, allAI metadata review, pricing, licences, earnings, requests) happens on the ai.market website, the same for every seller.
- **IS NOT:** A cloud service, a worker, a management application, or a second place to manage listings. It never gives ai.market access into the customer's systems: it reads only what the customer mounts into it, makes outbound connections only to ai.market's control plane, and accepts inbound connections only on the delivery endpoint the customer chooses to expose. It runs without host privileges and never updates itself. Never sends customer data to ai.market other than the seller-chosen public sample. **Not the worker — the worker is allAI.**
- **Data plane:** Non-custodial and peer to peer. The buyer downloads over TLS directly from the seller's delivery endpoint; ai.market issues the permission and records the delivery receipt, and never carries, relays, caches or stores the bytes.
- **MUST integrate with:** ai.market (pairing, a signed control channel, metadata intake, download permissions, delivery receipts, billing), allAI (through ai.market, on the metadata the gateway sends)
```

## CORE v9.20 line 64-65

**Old:**

```text
- **IS:** Our second customer-facing data product, co-equal with AIM Data. It turns corporate data into a Qdrant (vector database) format and can upload that data to the marketplace the same way AIM Data does. A distinct product with its own brand and repo (`aidotmarket/vectoraiz`).
- **IS NOT:** Branded under ai.market. It is our product, but it ships under its own brand, not as part of the AIM Data conduit. Not a worker — the worker is allAI.
```

**New:**

```text
- **IS:** Our second customer-facing data product, co-equal with AIM Data. It turns corporate data into a Qdrant (vector database) format and can upload that data to the marketplace. A distinct product with its own brand and repo (`aidotmarket/vectoraiz`).
- **IS NOT:** Branded under ai.market. It is our product, but it ships under its own brand, not as part of AIM Data. Not a worker — the worker is allAI.
```

## CORE v9.20 line 357

**Old:**

```text
- **Two customer-facing data products.** Customers reach ai.market through two co-equal data products: **AIM Data** (repo `aidotmarket/aim-data`) — one conduit with two surfaces, a non-dev customer-hosted desktop GUI and a developer surface (CLI, SDK, MCP server) for programmatic access to the marketplace and to allAI; and **vectorAIz** (repo `aidotmarket/vectoraiz`) — which turns corporate data into a Qdrant (vector) format and uploads it to the marketplace the same way AIM Data does. vectorAIz is our product but is not branded under ai.market, and standalone it has no allAI access. The former AIM-Node developer conduit is retired (S1001); its features are subsumed into AIM Data.
```

**New:**

```text
- **Two customer-facing data products.** Customers reach ai.market through two co-equal data products: **AIM Data** (repo `aidotmarket/aim-data-gateway`; the earlier `aidotmarket/aim-data` is frozen for features and retired once its installs migrate) — the open-source, self-hosted gateway for sellers who keep their data on their own infrastructure, with all seller management on the ai.market website; and **vectorAIz** (repo `aidotmarket/vectoraiz`) — which turns corporate data into a Qdrant (vector) format and uploads it to the marketplace. vectorAIz is our product but is not branded under ai.market, and standalone it has no allAI access. The former AIM-Node developer conduit is retired (S1001). Programmatic and agent access to the marketplace is served by ai.market itself.
```
