# BQ-SELLER-GUIDED-LISTING-FLOW-S1787: Gate 1, a guided seller listing flow (R3)

**Build Queue entity:** `build:bq-seller-guided-listing-flow-s1787` (P1, owner Vulcan).
**Tickets:** T-2026-000908 (consolidated scope), T-2026-000877 (the walkthrough notes, item by item; the thread is reproduced in the review package). T-2026-000878 (Markdown licence editor) stays separate.
**Authority:** Max, S1756 (2026-09-27 15:13 UTC): "We had a window in the corner that had each step, the way Stripe does it. Can we bring this back. That shows the steps and it is obvious what the next step is." Re-raised S1787 (2026-10-01 00:37 CEST). Max, 01:00 CEST: "Do it in the order that makes sense but do not lose track of it."
**Risk class:** customer-facing seller flow. No change to money, auth, delivery or the licence contract. Council: full panel (GLM, DeepSeek, CC in Gemini seat per `d50cbd80`; codex2 in GLM seat per `e4c8ed6f` until 2026-10-02 00:00 CEST).
**Must land before:** Sergey's switch from legacy AIM Data to Seller Workspace (BQ-AIM-DATA-GATEWAY-REBUILD-S1741 chunk F), because he will not have an operator guiding him.
**Pins:** ai-market-frontend `ac0e0e40072329d96cc5d2dca09b39037989ebdb`, ai-market-backend `83e9b8f9df902b998a574ea52a7fddcb74b79a09`. Production facts read 2026-10-01 01:40 CEST (read-only): `LISTING_LICENSES_ENABLED=true`; table `categories` has 12 top-level rows; `listings.category` holds 18 distinct free-text values, none of them a `categories.slug`.

## 1. Why

Max walked the live Seller Workspace as a real seller (max@kisa.cat) on 2026-09-27 and 28 and got stuck at step boundaries. Some of what he hit was fixed by frontend PR #93 (`c24135e`) the same day; what remains at the pins:

| What happened | Cause at the pins |
| --- | --- |
| After "Licence choice saved" he did not know what to do next | Nothing tracks progress. `WorkspaceOverview.tsx:45-60` `SellerJourney` is a card on the Storage tab only; no stage ever reaches a done state (stage 1 shows "Connected", stage 4's label follows publish capability, not the seller's progress). |
| He had to scroll back to the tab row after each step | No "Next" control at the end of a step. |
| "Prepare with Allai" meant nothing to him | Tabs are named after our assistant, not the task (`WorkspaceOverview.tsx` nav: Storage connections, Choose what to sell, Prepare with Allai, Review listing, Your listings). |
| He nearly published a description of the wrong data | The draft kept the text of an old one-row test file after he chose five new files. `ListingAssistantRequest` (`app/schemas/seller_listing_assistant.py`, `extra='forbid'`) carries only brief, draft, review focus, instruction and history, never the selected files, and nothing warns when the files change after the text was written. Max: "How does my making a change that no customer would know to make fix allai?" |
| Allai invented a category | Category is free text (`normalize_listing_category` accepts any string); Allai is not given a list, although a `categories` table exists. |
| Two licence places, one of them dead | With `LISTING_LICENSES_ENABLED=true` (production), the free-text "Your license" input (`SellerListingEditor.tsx:126`) is overwritten from the licence selection at review (`seller_listing_review.py:49-58`), so what the seller types there never reaches buyers. Allai does not propose it (its `ListingField` is title, description, category, tags). |

Max's two standing rules for every step (T-877, 2026-09-27): **R1** the page always says when a step is not done and what to do; **R2** it never asks the seller to save something they have not changed. #93 already disables "Save selected files" when the selection is unchanged (`WorkspaceData.tsx:295`); R2 here is about moving on without re-saving.

## 2. The design

### 2.1 One step list, one source of truth

Six steps, named for the task:

| # | Step name | Done when |
| --- | --- | --- |
| 1 | Connect your storage | a current connection has status `verified` |
| 2 | Choose your files | a saved listing source exists and `connection_current` is true |
| 3 | Choose a licence | the draft's `license_selection` is complete (flag on); skipped when licences are off |
| 4 | Describe and price | every field this step owns is valid (the licence belongs to step 3): title, description, a category from the list, at least one tag, an admissible price (the same rules as `seller_listing_review.py:60-73` and `seller_listing_approval.py:44-47`), and the description is confirmed for the current files (2.4) |
| 5 | Review | the current draft has an approved review |
| 6 | Publish | the listing is published |

A single pure function in the frontend computes each step's state (`done`, `current`, `blocked`, `to do`) and, for anything not done, one plain sentence saying what is missing and what to do (R1). Its inputs are existing endpoints; steps 5 and 6 need their review and publication reads lifted from the Review and Your listings panels to the page, with no new backend endpoint. If Review still refuses (a rule the function did not mirror), Review's own reason is shown and step 4 is marked not done with that reason, so the checklist can never say "done" while Review says no. The tabs, the checklist and the Next buttons all read that one result.

The step names become the tab names. "Prepare with Allai" becomes "Describe and price", with a line inside the step: "Allai, our assistant, can draft this for you from your files." "Your listings" stays as a separate tab after the six steps.

### 2.2 The checklist

Max asked for a panel in the corner visible on every step, like Stripe's onboarding. It shows on every Seller Workspace tab: in the right column on wide screens, and as a collapsible bar at the top on phones (one component, two layouts). Each step shows its state with an icon and text, not colour alone, and clicking a step opens it. The first not-done step is marked "Next" with one primary button. After publishing it shows "Published: view your listing" and a link to start another. The static `SellerJourney` card is deleted.

The existing account-setup bar (`SellerSetupProgressBar.tsx`: name, company, 2FA, Stripe payouts) is unchanged. When account setup is incomplete, the checklist shows it as a line above step 1 with a link to that bar's next step.

### 2.3 Next buttons and saving (R2)

When a step becomes done, its bottom shows "Next: <step name> →". A selection or choice already shown as saved counts as confirmed and needs no save to move on. A save button appears only with unsaved changes; pressing Next with unsaved changes saves them first, and if the save fails, the reason is shown and the seller stays on the step.

### 2.4 Allai drafts from the files, and the page knows which files the text was written for

- **What Allai is given.** The assistant request gains one bounded field, `source_summary`, built by the backend from the saved listing source (never from the browser): `source_version`, object count, total bytes, and up to 200 entries of `{basename, size, extension}`. Basenames only (no bucket, prefix or path), each cut to 120 characters, and the whole field capped at 16 KB; beyond the caps it carries only a count of the remainder. No object is fetched, opened or sampled for this: the summary comes from the stored source record (`app/schemas/seller_listing_source.py`), which already holds each object key and size, and the source record version (CORE S1/P2 unchanged).
- **Disclosure.** Above the draft button the step says: "Allai reads your file names and sizes to write the draft. It never opens your files." File names stay private unless the seller keeps them in the text: any file name in an approved description or title becomes public, and no automatic check removes it. The step says so next to the description: "Anything you keep here, including file names, will be public."
- **Binding drafts to files.** The assistant response echoes `source_version`. Proposals from a response whose `source_version` is not the current saved source are discarded with "Your files changed while Allai was drafting. Ask again." Choosing new files clears pending proposals and the chat history.
- **Stamp.** `ListingDraftContent` gains optional `description_source_version`. It is set only when the seller accepts Allai's **description** proposal bound to the current source version, or presses "This description matches my files". Accepting only a title, category or tags proposal does not set it, and any later manual edit of the description clears it until the seller confirms again.
- **Warning.** If the saved source version differs from `description_source_version` (or the stamp is missing), step 4 is not done and shows "Your files changed after this description was written" with two buttons: "Ask Allai to update it" and "This description matches my files".
- **Where suggestions are.** A fixed hint above the chat, and the assistant's instructions, say the suggestions are in the boxes under each field on the left.

### 2.5 Category list

The single source is the existing `categories` table (12 top-level rows in production: financial-data, alternative-data, consumer-retail, healthcare-life-sciences, geospatial-location, environmental-climate, technology-web, government-public, energy-utilities, transportation-logistics, real-estate-property, ai-machine-learning). It is already the join target for the MCP `/categories` tree and the datasets filter, so listings that use its slugs start appearing there. No new config list.

- A read-only endpoint (or the existing categories read, if one is reachable to sellers) serves slug and name to the editor dropdown; the assistant request carries the same list, and the assistant is instructed to choose one slug from it.
- Draft saves keep accepting any category value, as today, so the current editor keeps working during the staged release; the new editor's dropdown can only send a slug or empty, and an empty category saves (so a licence can be saved before describing).
- Review and publish require a slug for Seller Workspace listings (chunk A2, after the new editor is live), with a message naming step 4 (R1).
- Existing listings and their 18 free-text values are untouched; public search facets keep reading the listing's own value (`listing_search_service.py`). A draft holding an old free-text value keeps it stored until the seller picks from the list; the dropdown shows "Choose a category from the list" with nothing selected, step 4 is not done, and saving other fields does not change the stored value.
- `CATEGORY_TAXONOMY` in `app/knowledge/listing_knowledge.py` stays allAI's knowledge guidance about each domain; it is not a listing vocabulary. The frontend fallback list in `lib/marketplaceCategories.ts` is not used by the editor. Reconciling the public facet labels with the table is a follow-up, recorded on T-2026-000908.

### 2.6 Licence: one place, readable without leaving the page

- With licences on (production), the free-text "Your license" input is removed from the editor, and the editor's preview shows the real licence selection. With licences off, the input stays as it is today.
- "Read licence" opens the full licence, matching the AI-training choice, in a dialog over the page; the Marketplace Listing Covenant opens the same way. Opening each counts as read; closing returns to the same spot; an "Open in new tab" link stays inside for printing. The dialog traps focus, closes on Esc and is labelled. The buyer licence acceptance uses the same dialog.

### 2.7 Smaller fixes from the same walkthrough (T-877 items from S1759)

Title, tags and category inputs grow to fit or wrap; an accepted and saved title is what Review shows (Max saw the old title in Review after accepting and saving; reproduce first); Review shows "Files included (n)" beside the confirmations; the Publish button and "Refresh publication status" get spacing; the listing page uses one date rule for "Published"; the licence cards appear once; the approved listing preview sizes to its content instead of a fixed-height box, both in the seller's Review and on the buyer listing page; a seller viewing their own listing sees "This is your listing" instead of the buy form. Individual (non-business) buyer acceptance is T-2026-000884 and stays there. The #93 deferred nits (a)-(g) (quoted in the review package) are fixed where they touch the same components.

## 3. Out of scope

Money, payouts, checkout, delivery, gateway, the licence text and its hashing, buyer Terms. T-2026-000878 (custom licence formatting). The account-setup bar's own steps. Migrating the 18 legacy category values.

## 4. Build plan and release order

- **Chunk A (backend):** `source_summary` in the assistant request and `source_version` echo; optional `description_source_version` on `ListingDraftContent`; categories read for sellers. No category rule changes in A. Chunk A is safe with today's frontend: nothing sends the new fields, and a free-text category still saves.
- **Chunk B (frontend):** step function, checklist, task-named tabs, Next buttons and save behaviour, source binding and warning, category dropdown, licence dialog, removal of the dead input (flag on) and the static journey card.
- **Chunk A2 (backend, one line of rules):** review and publish require a category slug for Seller Workspace drafts. Deployed only after B is live, so no seller on the old editor is blocked.
- **Chunk C (frontend):** the 2.7 fixes.

MP builds each chunk. A and A2 go to the full panel (they touch the assistant request and the admission rules); B and C per Option C unless they touch approval or publish.

## 5. Acceptance

1. A new synthetic seller, with no operator guidance, goes from a verified connection to a published listing using only the checklist and Next buttons (Playwright, production-like data, no real money).
2. At every point in that walk the checklist names exactly one next step, and every disabled control says why (R1).
3. No step asks to save an unchanged selection (R2).
4. Stale-draft sequences. (a) Draft and accept a description for files A; choose files B: pending proposals and chat clear, step 4 shows the warning, reload keeps it, publish is not offered; asking Allai for B and accepting the new description clears it. (b) A response for A arriving after the switch to B is discarded with its message. (c) With files B chosen, accepting only a title suggestion leaves the warning in place after save and reload. (d) Editing the description by hand after confirming brings the warning back until confirmed again.
5. Step 4 and Review agree: empty tags, an invalid price, and a non-slug category each mark step 4 not done with the right message, and Review refuses the same drafts with the same reason.
6. Metadata only: a test captures the outbound assistant request for a source that includes a synthetic sensitive name (`jane.doe@example.com-patients.csv`). The request holds only the fields in 2.4 within the caps; storage calls during drafting are listing calls only, with no object GET; 250 objects produce 200 entries plus a remainder count.
7. Categories: the dropdown shows the 12 table rows; a licence saves with an empty category; after A2, review refuses a draft without a slug with the step-4 message, a legacy draft keeps its stored value until changed, and a newly published listing appears under its node in the MCP `/categories` tree.
8. Licence: with the flag on, the free-text licence input is absent and the preview shows the selected licence; the dialog opens, traps focus, closes on Esc and returns focus to the button.
9. Staged release: with A deployed and the old frontend, a draft with a free-text category still saves and a listing still publishes; after B and A2, the rules in 7 hold.
10. Max repeats the walk as max@kisa.cat and signs it off before Sergey's switch.

## 5a. Rollback

- **B, A2, C:** revert the PR.
- **A:** `description_source_version` is persisted in draft JSON, and the pre-A schema forbids unknown fields, so a plain revert of A would make stamped drafts unreadable. A is therefore rolled back by a forward change: revert B first (nothing new writes the field), then ship a backend release that keeps the field in the schema but ignores it. Drill: stamp a draft on the test environment, perform this rollback, and read and save that draft.
