---
title: Listing slug rename (seller-identifying slug)
owner: vulcan
last_verified: '2026-09-23'
aliases:
- slug rename
- branded slug
- neutral slug
error_signatures:
- UPDATE 0 on listings slug rename
- duplicate key value violates unique constraint on listings slug
- Kaggle create/new rejected, title already in use
---

# Listing slug rename

## Purpose

A listing's slug is public. It appears in the listing URL, the JSON-LD, the
sitemap and the names of the metadata cards we mirror to Hugging Face and
Kaggle. A slug that names the seller, such as a company name, breaks the
anonymity rule (CORE P5/S1; `ai-market-backend` runbook
`runbooks/public-seller-anonymity.md`). This page renames such a slug to a
neutral one. The page is a production-data procedure: the exact values for a
given listing are Council-approved before it runs.

First use (S1740):

| Item | Value |
| --- | --- |
| Listing id | `5ab53e16-ca71-4d5b-8d55-794420d3b800` |
| Old slug | `eolymp-problem-dataset-5ab53e16` |
| New slug | `competitive-programming-problems-5ab53e16` |
| Title | "Competitive Programming Problems" (already neutral, unchanged) |
| Old HF mirror | `ai-market/eolymp-problem-dataset-5ab53e16-sample` |
| Old Kaggle mirror | `maxrobbinsaimarket/eolymp-problem-dataset-5ab53e16` |
| Archive title for the old Kaggle mirror | `Archived ai.market listing 5ab53e16` |

## What depends on the slug

| Surface | How it uses the slug | What this procedure does |
| --- | --- | --- |
| `listings.slug` | Public URL `https://ai.market/listings/{slug}`, API `/public/listings/{slug}` | Set to the new value in the step 3 transaction. |
| `listings.jsonld` | The old slug appears in `url` and other fields; `sameAs` lists the mirrors | Step 3 rewrites every occurrence of the old slug and drops `sameAs`. The card publishers (`huggingface_service.py`, `kaggle_service.py` → `generate_listing_jsonld`) later write the full document with the new `sameAs`. MCP detail serves the stored column, so it must be correct at commit time. |
| `listings.source_delivery` | `huggingface_url`, `kaggle_url` of the old mirrors | Step 3 removes both keys, so the publishers create new mirrors instead of versioning the old ones. |
| `inquiries.listing_slug` | Denormalized copy shown in inquiry context | Step 3 updates the rows for this listing. |
| `listing_summary_records` / `listing_preview_disclosure_heads` | The `listing_summary_content_update` trigger invalidates an approved summary on any content-column change, including `slug`. The invalidation turns preview heads ineligible. | Step 1 records the state. If an approved summary exists, the seller re-approves it afterwards (the seller's own action in the listing editor). The first use has only an already-invalidated summary and no preview heads, so nothing is lost. |
| Hugging Face mirror | Repo `ai-market/{slug}-sample` | Step 2 makes the old repo private. Step 4's job creates the new repo. Never delete. |
| Kaggle mirror | Dataset `maxrobbinsaimarket/{slug, max 50 chars}`. Kaggle rejects a second dataset with the same title in the account. The backend's collision fallback versions a dataset under the NEW slug, which does not exist yet. | Step 2 retitles the old dataset to the archive title and makes it private, which frees the title. Step 4's job then creates the new dataset cleanly. Never delete. |
| Frontend | The old URL must keep working | Step 5 deploys a permanent redirect old → new (`next.config.ts` `redirects()`) right after the rename. This is the point of no return; see Rollback. |
| Frontend page cache | ISR `revalidate: 3600` (`lib/api.ts` fetchPublicListing) | Wait out the hour or verify through the API; the page self-heals. |
| Sitemap | Built from the database and cached for one hour | Verify after the cache expires. |
| Search | The Qdrant payload has no slug; queries read `l.slug` from Postgres (`listing_search_service.py`) | Verify only. |
| `ai_crawler_events.listing_slug` | Historical analytics | Left unchanged (history). |
| Share links | `listing_share_links` keyed by listing id | Verify the count (0 for the first use). |

## Tools and access

- Database: the prod DSN script `scripts/test-db-dsn.sh` in the ai-market workspace, as in `dataset-card-publishing.md` E-02.
- Card-channel credentials: `HUGGINGFACE_TOKEN`, `KAGGLE_USERNAME` and `KAGGLE_API_TOKEN` from Infisical `ai-market-backend` prod, exported only into the shell that runs the command. Never print or paste them.
- Clients: a throwaway venv with `kaggle` 2.2.4 and `huggingface_hub` 1.32.0 (both verified S1740). Hugging Face uses `HfApi().update_repo_settings(repo_id=..., repo_type="dataset", private=...)`. Kaggle uses `kaggle datasets metadata -p DIR OWNER/SLUG`, then edits `title` and `isPrivate` in the downloaded metadata JSON, then runs `kaggle datasets metadata --update -p DIR OWNER/SLUG`; `dataset_metadata_update` sends title, subtitle, description, isPrivate, licenses and keywords from that file.

## Procedure

1. **Pre-check (read-only) and record.** Record in the release evidence:
   - the listing row: id, slug, title, status, `source_delivery`, the full `jsonld`;
   - the order count and the share-link count;
   - the `inquiries` rows (id, listing_slug);
   - the `listing_summary_records` state and the `listing_preview_disclosure_heads` rows;
   - that `select count(*) from listings where slug = '<new>'` returns 0;
   - the old mirrors' current visibility and title.
2. **Make the old mirrors private, and free the Kaggle title.**
   - Hugging Face: set the old repo private.
   - Kaggle: download the old dataset's metadata, set `title` to the archive title and `isPrivate` to true, and upload the metadata.
   - Verify: logged out, both old URLs return 401 or 404, and the Kaggle metadata shows the archive title.

   This only hides old public copies; it changes nothing on ai.market.
3. **Rename in one transaction**, guarded on the old slug:

   ```sql
   begin;
   set local lock_timeout = '5s';
   update listings
      set slug = '<new>',
          jsonld = (replace(jsonld::text, '<old>', '<new>'))::jsonb - 'sameAs',
          source_delivery = coalesce(source_delivery, '{}'::jsonb) - 'huggingface_url' - 'kaggle_url',
          updated_at = now()
    where id = '<listing-id>' and slug = '<old>';
   -- expect UPDATE 1; anything else: rollback
   update inquiries set listing_slug = '<new>'
    where listing_id = '<listing-id>' and listing_slug = '<old>';
   -- expect UPDATE = the step-1 inquiry count
   commit;
   ```

   Then check that `https://api.ai.market/api/v1/public/listings/<new>` returns 200, that its JSON-LD contains no `<old>` and no `sameAs`, and that the MCP listing detail for the id carries the new `url`.
4. **Republish the cards.** Insert one `huggingface` and one `kaggle` `updated` job for the listing (`dataset-card-publishing.md` E-02). Wait for both to reach `succeeded`. Then read back:
   - `source_delivery`: the new URLs, named from the new slug;
   - `jsonld.sameAs`: only the new mirrors;
   - `jsonld.url`: the new slug.

   A `dead` job does not block step 5: the listing is already consistent without mirrors. Follow `dataset-card-publishing.md` When it breaks, then re-enqueue.
5. **Deploy the frontend redirect.** The branch with the `redirects()` entry old → new (`permanent: true`) merges right after step 3 is verified, so the old URL is broken only for that short gap. Announce on the peer bus before and after (the merge rule). Frontend deploy per the frontend deploy runbook. **From here on the change is one-way**: browsers and crawlers cache a 308.
6. **Verify from outside:**
   - `https://ai.market/listings/<new>` returns 200.
   - `https://ai.market/listings/<old>` returns 308 to the new URL.
   - The API detail for `<new>` returns 200 and contains no seller identity.
   - The new HF and Kaggle cards return 200 and link back to the new URL.
   - The old HF and Kaggle URLs still return 401 or 404 when logged out.
   - A marketplace search for the title returns the new slug.
   - After one hour: the listing page's JSON-LD and the sitemap carry the new slug and no `<old>`.

   Record the evidence in the Event Ledger.

## Rollback

- **Before step 3:** set the old mirrors public again and restore the old Kaggle title from the step-1 record. Nothing else has changed.
- **After step 3, before step 5:**
  - Reverse step 3 with the same guarded statements (swap `<old>` and `<new>`).
  - Restore `jsonld` and `source_delivery` from the step-1 record.
  - Make any new mirror created by step 4 private.
  - Then undo step 2.
- **After step 5:** do not move the slug back, because cached 308s would point old visitors at a slug that no longer exists. Fix forward on the new slug. If a return is required anyway, first revert and deploy the frontend redirect, then keep the new slug working through a reverse redirect before reversing step 3.

Nothing is deleted at any step.

## When it breaks

- `UPDATE 0` on listings: the slug changed since the pre-check, or the id is wrong. Roll back the transaction and re-run step 1.
- Unique violation on `slug`: the new slug already exists. Stop, and choose a different neutral slug with Council.
- Kaggle `create/new` rejected with "already in use": step 2 did not free the title. Check the old dataset's title, fix it, and re-enqueue.
- A card job ends `dead`: follow `dataset-card-publishing.md` When it breaks. The rename stands; re-enqueue after the fix.
