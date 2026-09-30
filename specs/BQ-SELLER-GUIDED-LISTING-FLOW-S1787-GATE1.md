# BQ-SELLER-GUIDED-LISTING-FLOW-S1787: Gate 1, a guided seller listing flow

**Build Queue entity:** `build:bq-seller-guided-listing-flow-s1787` (P1, owner Vulcan).
**Tickets:** T-2026-000908 (consolidated scope), T-2026-000877 (the walkthrough notes, item by item). T-2026-000878 (Markdown licence editor) stays separate.
**Authority:** Max, S1756 (2026-09-27 15:13 UTC): "We had a window in the corner that had each step, the way Stripe does it. Can we bring this back. That shows the steps and it is obvious what the next step is." Re-raised S1787 (2026-10-01 00:37 CEST). Max, 01:00 CEST: "Do it in the order that makes sense but do not lose track of it."
**Risk class:** customer-facing seller flow. No change to money, auth, delivery or the licence contract. Council: full panel (GLM, DeepSeek, CC in Gemini seat per `d50cbd80`; codex2 in GLM seat per `e4c8ed6f` until 2026-10-02 00:00 CEST).
**Must land before:** Sergey's switch from legacy AIM Data to Seller Workspace (BQ-AIM-DATA-GATEWAY-REBUILD-S1741 chunk F), because he will not have an operator guiding him.

## 1. Why

Max walked the live Seller Workspace as a real seller (max@kisa.cat) on 2026-09-27 and 28 and got stuck at every step boundary. Evidence, all on production:

| What happened | Cause at ai-market-frontend main |
| --- | --- |
| After "Licence choice saved" he did not know what to do next | Nothing tells the seller the next step. `components/seller-workspace/WorkspaceOverview.tsx` `SellerJourney` is a static four-stage card on the Storage tab only; its states never move past "Connected". |
| He had to scroll back to the tab row after each step | No "Next" control at the end of a step. |
| "Prepare with Allai" meant nothing to him | Tabs are named after our assistant, not the task (`WorkspaceOverview.tsx` nav: Storage connections, Choose what to sell, Prepare with Allai, Review listing, Your listings). |
| He nearly published a description of the wrong data | The draft kept the text of an old one-row test file after he chose five new files. The assistant is given only the seller's brief and current fields (`app/services/seller_listing_assistant.py:13`), never the selected files, and nothing warns when the files change after the text was written. Max: "How does my making a change that no customer would know to make fix allai?" |
| Allai invented a category | Category is free text (`normalize_listing_category` accepts any string); Allai is not given a list. |
| Two licence places, one of them dead | The free-text "Your license" field (`SellerListingEditor.tsx:126`) is overwritten from the licence selection at review (`seller_listing_review.py:49-57`), so what the seller types there never reaches buyers. |

Max's two standing rules for every step (T-877, 2026-09-27): **R1** the page always says when a step is not done and what to do; **R2** it never asks the seller to save something they have not changed.

## 2. The design

### 2.1 One step list, one source of truth

Six steps, named for the task:

| # | Step name | Done when (existing reads only) |
| --- | --- | --- |
| 1 | Connect your storage | a current connection has status `verified` |
| 2 | Choose your files | a saved listing source exists and `connection_current` is true |
| 3 | Choose a licence | the draft's `license_selection` is complete |
| 4 | Describe and price | title, description, category and price are saved in the draft, and the draft was written for the current file selection (2.4) |
| 5 | Review | the current draft has an approved review |
| 6 | Publish | the listing is published |

A single pure function in the frontend computes, from the reads the page already makes, each step's state (`done`, `current`, `blocked`, `to do`) and, for anything not done, one plain sentence saying what is missing and what to do (R1). The tabs, the checklist and the Next buttons all read that one result, so they cannot disagree. No new backend status endpoint.

The step names become the tab names. "Prepare with Allai" becomes "Describe and price", with a line inside the step: "Allai, our assistant, can draft this for you from your files." "Your listings" stays as a separate tab after the six steps.

### 2.2 The checklist

A panel shown on every Seller Workspace tab: in the right column on wide screens, and as a collapsible bar at the top on phones. Each step shows its state with an icon and text (not colour alone), and clicking a step opens it. The first not-done step is marked "Next" with one primary button. It stays visible until the listing is published, then shows "Published: view your listing" and a link to start another. This replaces the static `SellerJourney` card, which is deleted.

The existing account-setup bar (`SellerSetupProgressBar.tsx`: name, company, 2FA, Stripe payouts) is unchanged. When account setup is incomplete, the checklist shows it as a line above step 1 with a link to that bar's next step, so the seller sees one path from sign-up to published.

### 2.3 Next buttons and saving (R2)

When a step becomes done, its bottom shows "Next: <step name> →". A selection or choice already shown as saved counts as confirmed. A save button is shown only when there are unsaved changes, and continuing to the next step with unsaved changes saves them first or asks once. This removes the case Max hit, where an unchanged file selection had to be saved again before anything moved.

### 2.4 Allai drafts from the files, and the page notices when the files change

- **What Allai is given:** alongside the brief and fields, the assistant request carries a metadata-only summary of the saved listing source: object count, total size, and each object's name, size and format from its file extension, as the file list already labels them (capped at 200 entries, with a count of the rest). This is metadata the seller already chose to list. No object content is read or sent (CORE S1/P2 unchanged).
- **Draft stamping:** when drafted fields are saved, the draft content records `drafted_for_source_version`, the listing source `version` it was written for. It is a new optional field on `ListingDraftContent` (`app/schemas/seller_listing_draft.py`, which forbids unknown fields, so the schema and the frontend draft type both change); the draft is stored as JSON, so no migration.
- **Warning:** if the saved source version differs from `drafted_for_source_version`, step 4 shows "Your files changed after this description was written" with one button, "Ask Allai to update it". Step 4 is not done until the seller redrafts or confirms "Keep this description".
- **Stale chat:** a new draft request clears the previous assistant reply from the panel.
- **Where suggestions are:** the assistant's instructions and a fixed hint above the chat say the suggestions are in the boxes under each field on the left.

### 2.5 Category list

The backend owns one listing category list, served to the editor as a dropdown and passed to Allai with the instruction to pick from it. It is seeded from the marketplace categories the site already shows (`lib/marketplaceCategories.ts`). The draft save and publish reject a value not on the list with a message naming the step (R1). Existing published listings keep their value. Open question for review: whether the list lives in backend config or a small table; the proposal is config, since no one edits it at runtime.

### 2.6 Licence: one place, readable without leaving the page

- The dead free-text "Your license" field is removed from the editor, and Allai stops drafting it, while `LISTING_LICENSES_ENABLED` is true. The editor's preview shows the real licence selection.
- "Read licence" opens the full licence, matching the AI-training choice, in a dialog over the page. The Marketplace Listing Covenant opens the same way. Opening each counts as read; closing returns to the same spot; an "Open in new tab" link stays inside for printing. The dialog is accessible (focus trap, Esc closes, labelled). The buyer licence acceptance uses the same dialog.

### 2.7 Smaller fixes from the same walkthrough (T-877 S1759 items)

Title, tags and category inputs grow to fit or wrap; "Use suggestion" reliably applies a title (reproduce first); Review shows "Files included (n)" beside the confirmations; the Publish button and "Refresh publication status" get spacing; the listing page uses one date rule for "Published"; the licence cards appear once; the approved listing preview sizes to its content instead of a fixed-height box; a seller viewing their own listing sees "This is your listing" instead of the buy form. Individual (non-business) buyer acceptance is T-2026-000884 and stays with that ticket. The #93 deferred nits (a)-(g) are folded in where they touch the same components.

## 3. Out of scope

Money, payouts, checkout, delivery, gateway, the licence text and its hashing, buyer Terms. T-2026-000878 (custom licence formatting). The account-setup bar's own steps.

## 4. Build plan

- **Chunk A (backend, one PR):** assistant request carries the source summary; optional `drafted_for_source_version` added to `ListingDraftContent`; category list config, served read-only, enforced at draft save and publish; stop drafting the free-text licence when licences are enabled.
- **Chunk B (frontend, one PR):** step function, checklist, task-named tabs, Next buttons and save behaviour (R2), stale-draft warning, stale-chat clear, category dropdown, licence dialog, removal of the dead field and the static journey card.
- **Chunk C (frontend, one PR):** the 2.7 listing-page and review fixes.

MP builds each chunk; review follows Option C sizing, with chunk A and any chunk touching the approval or publish check to the full panel. Deploy A before B.

## 5. Acceptance

1. A new synthetic seller, with no operator guidance, goes from a verified connection to a published listing using only the checklist and Next buttons. Record the walk (Playwright, production-like data, no real money).
2. At every point in that walk the checklist names exactly one next step, and every disabled control says why (R1).
3. No step asks to save an unchanged selection (R2).
4. Changing the file selection after drafting shows the warning; publishing is not offered until the seller redrafts or keeps the description.
5. Allai's draft names the selected files' formats and count; its category is from the list.
6. Max repeats the walk as max@kisa.cat and signs it off before Sergey's switch.

## 5a. Rollback

Each chunk is a revert of one PR. The draft field and category config are additive; old drafts without `drafted_for_source_version` show the warning once, which the seller clears by redrafting or keeping the description.
