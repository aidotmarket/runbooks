# BQ-AGENT-TOOLS-DESCORE-D7-S1600 Gate 1 design specification

**Build Queue entity:** `build:bq-agent-tools-descore-d7-s1600`

**Session:** Vulcan S1599

**Verified code baseline:** `ai-market-backend@2ab324698a465f316246ea6b73259e83a7e2d430`

**Existing product authority:** `BQ-DATA-VERIFICATION-S1590-GATE1.md` sections 2, 5, 14 and acceptance criterion 17. In particular, numeric or composite quality scores are absent from listing pages, published evidence is the complete point-in-time scan-findings artifact, and the listing and API contain no unqualified truth-status string, numeric quality score, or compliance claim.

## 1. Frozen problem

The unauthenticated public agent surface at `POST /api/v1/agent/tools/call` contradicts the existing D7 trust decisions:

- `search_listings` computes and emits a composite `trust_score`, emits `verification_status`, accepts and echoes `trust_score_min`, and orders by `quality_score`.
- `get_listing_detail` emits `quality_score`, composite `trust_score`, `verification_status`, `compliance_status`, and `compliance_details`.
- `evaluate_trust` emits the same composite conclusion, its component score breakdowns, and legacy attestation signals instead of the already-defined published scan-findings projection.
- The same anonymous API family still exposes `compliance_status` as a result field and request filter through `/api/v1/search/listings`, and the legacy anonymous `GET /api/v1/listings/{id}` detail response does not exclude `compliance_status` or `compliance_details`.

These public contracts let buyers or agents treat platform-computed scores, verification labels, or risk tiers as an ai.market quality or compliance conclusion. The problem is public serialization and public score-oracle inputs, not the internal persistence or calculation of those legacy fields.

## 2. Frozen scope

### In scope

1. Remove `trust_score`, `quality_score`, and unqualified `verification_status` from the public agent search/detail/evaluation responses.
2. Remove `compliance_status` and `compliance_details` from the public agent detail response, the anonymous search response and filter contract, and the non-owner legacy listing-detail response.
3. Remove `trust_score_min` from the public agent manifest, argument model, service signature, response echo, and SQL predicate. Remove `quality_score` from public agent search ordering.
4. Preserve the `evaluate_trust` tool name for compatibility, but replace its response with the exact existing S1590 public scan-findings projection described in section 3.
5. Reuse the existing S1590 public projection validation and withdrawal-window behavior; do not create a second scan-artifact serializer.
6. Add only focused contract and service tests for these public shapes and rejected former inputs.

### Out of scope

- Removing, renaming, recalculating, or migrating internal listing columns, scores, trust levels, privacy scores, searchability scores, attestation records, or compliance records.
- Changing authenticated seller/admin response shapes or internal search-service capabilities.
- Changing the S1590 scan, publication, payment, corpus, signing, or privacy design.
- Renaming public tools, adding authentication, changing rate limits, or redesigning MCP transport.
- General cleanup of other historical public surfaces not named in section 1.

## 3. Exact public contract

### 3.1 `search_listings`

The request accepts only the existing query/keyword alias, category, price range, limit, and offset fields. `trust_score_min` is absent from the manifest and argument model; because the model remains `extra="forbid"`, sending it returns the existing invalid-params response.

Each result retains its existing non-D7 fields, including `trust_level`, but contains none of `trust_score`, `quality_score`, or `verification_status`. The response contains no `trust_score_min` echo. Ordering remains title-prefix relevance first, then `published_at DESC NULLS LAST`, then `created_at DESC`; the `quality_score DESC` term is removed without introducing a new ranking system.

### 3.2 `get_listing_detail`

The response retains its existing non-D7 fields but contains none of `trust_score`, `quality_score`, `verification_status`, `compliance_status`, or `compliance_details`. This change does not redefine other legacy metrics or the existing attestation summary.

### 3.3 `evaluate_trust`

The tool name remains `evaluate_trust`, but its manifest description says that it returns published point-in-time scan findings and never a composite trust judgment. Its result has exactly this top-level shape:

```json
{
  "listing_id": "uuid",
  "slug": "listing-slug-or-null",
  "status": "published | withdrawn | not_available",
  "scan_findings": "VerificationPublicProjection-or-null"
}
```

- `published`: `scan_findings` is the exact existing `VerificationArtifactPublic` for the listing's active `PUBLISHED` epoch.
- `withdrawn`: `scan_findings` is the exact existing time-bounded `VerificationWithdrawalPublic` marker. After the existing 30-day window it becomes `not_available`.
- `not_available`: `scan_findings` is null. This covers disabled verification, no active epoch, invalid/mismatched stored public projection, and every non-public lifecycle state.

No legacy score, score breakdown, `verification_status`, compliance claim, or legacy attestation summary appears in this response. The public projection helper used by the listing API is moved or exposed at the service layer and called by both surfaces so validation, feature-flag, identity-binding, and withdrawal-window behavior remain one mechanism.

### 3.4 Other named anonymous API shapes

- `/api/v1/search/listings` GET and POST no longer accept `compliance_status`, describe compliance risk tiers, or serialize `compliance_status` in `SearchResultItem`.
- The non-owner response from `GET /api/v1/listings/{id}` excludes `compliance_status` and `compliance_details` alongside its existing quality/verification exclusions.
- Owner and internal service shapes remain unchanged.

## 4. Acceptance criteria

1. The public tool manifest and generated public argument schema contain no `trust_score_min`; a call that still sends it is rejected as invalid params before database execution.
2. Public agent search SQL has no composite score expression, score predicate, or quality-score ordering, and search responses contain none of `trust_score`, `quality_score`, `verification_status`, or `trust_score_min`.
3. Public agent detail responses contain none of `trust_score`, `quality_score`, `verification_status`, `compliance_status`, or `compliance_details` even when source rows contain populated hostile values.
4. `evaluate_trust` returns the exact active S1590 artifact for a valid published epoch, the exact existing withdrawal marker during its window, and the explicit `not_available`/null shape for disabled, missing, stale, mismatched, invalid, expired-withdrawal, and other non-public states.
5. `evaluate_trust` contains no legacy score, breakdown, unqualified verification label, compliance conclusion, or legacy attestation summary at any nesting depth.
6. Anonymous GET/POST search contracts contain no compliance filter or result field; attempts to send the removed POST field are rejected by schema validation. The legacy non-owner listing detail omits both compliance fields while the owner path is unchanged.
7. Existing rate limiting, audit logging, listing visibility (`published` only for agent tools), query/price filters, pagination bounds, price-check tool, authenticated MCP routes, and S1590 public listing projection tests remain passing.
8. Focused tests cover the request schemas, manifest, SQL/serialization, published/withdrawn/unavailable evaluation states, anonymous search shapes, legacy detail redaction, and unchanged owner behavior.
9. Production verification calls the unauthenticated public manifest and tool endpoint against a published listing and proves the removed fields/inputs are absent or rejected and `evaluate_trust` returns one of the exact honest states. A live published scan artifact is verified only if one already exists; no scan, charge, listing, or customer-data mutation is created for this ticket.

## 5. Implementation boundary and test plan

Expected backend files are limited to the existing public agent service/router, the existing shared S1590 public-projection path, the two named anonymous endpoint serializers, and their focused tests. No schema migration is expected.

Focused validation:

- the existing public MCP test module plus new D7 assertions;
- existing S1590 publication/public-listing tests that cover projection identity and withdrawal behavior;
- focused anonymous search and legacy-listing tests;
- Ruff or repository lint only for changed Python files, `git diff --check`, and the protected-branch checks required by the repository workflow.

Rollback is a normal protected-branch forward revert of the exact merge. It restores only the former public response/filter contract; it makes no data change.

## 6. Known limits and simplicity check

The ticket does not remove every historical internal score or trust label. It removes only the dishonest public fields and score-oracle inputs named above and redirects the existing evaluation tool to the already-reviewed S1590 artifact. Reusing the one public projection is simpler and safer than defining a parallel agent-specific findings schema. Keeping the tool name avoids an unnecessary compatibility break. Council should explicitly say if any response field or touched surface can be removed from this design while still satisfying the frozen D7 acceptance criteria.
