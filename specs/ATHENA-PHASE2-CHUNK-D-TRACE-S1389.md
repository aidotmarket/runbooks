# ATHENA-PHASE2-CHUNK-D-TRACE-S1389

Status: DRAFT LOCAL COMMIT PREPARATION  
Owner: Athena  
Session: S1389  
Branch: `docs/athena-phase2-chunk-d-s1389`  
Exact base ref: local `main`  
Exact base SHA: `5f968f167661dcac669dd42910037e05a50221ed`  
Phase 1 triage source: `0945124c5abc4fd20173b89135c32fc94460ae34:specs/ATHENA-PHASE1-TRIAGE-S1389.md`

## 1. Purpose and constraints

This trace records Phase 2 Chunk D. It continues from the landed Chunk C cursor,
creates three DRAFT destinations, and leaves every root source unchanged.

Binding limits:

- docs only in the runbooks repository;
- no catalog, topic-router, or README inventory write;
- no ACTIVE promotion;
- no archive or retirement execution;
- K1-K3 and M1-M6 remain Max-gated;
- no push, merge, build, or `kd_session_close`;
- unsupported operational detail remains explicitly `Unknown`.

## 2. Base and source integrity

The branch was created directly from local `main` at
`5f968f167661dcac669dd42910037e05a50221ed`. That local ref was behind
`origin/main`. This trace does not disguise source divergence:

| Source | Blob on exact base | Blob on `origin/main` | Result |
|---|---|---|---|
| `website-copy-standard.md` | `22aec721e64f2e919756d765efcb2aa731344634` | `22aec721e64f2e919756d765efcb2aa731344634` | Identical |
| `max-reporting.md` | `e765cc9b822acf7bec2cf2b262cd702998d582ce` | `e765cc9b822acf7bec2cf2b262cd702998d582ce` | Identical |
| `rtk-token-optimization.md` | `324213b743bd29d32b8096ae63774064410c4d12` | `c41f9611ec7c6d9147b13d93f23751e979f287ee` | Diverged; rewrite is explicitly based on the requested exact local-main source |

No source file is modified. The differing RTK blob is recorded as a future
non-author reconciliation point; this DRAFT does not claim the base source is
newer than `origin/main`.

## 3. Cursor, stops, and eligible selection

Chunk C landed the first three eligible product rows and transferred
`alphafold-publish-scale-up.md` to its protected owner. Chunk D therefore starts
with the one remaining product rewrite, then continues through the unprocessed
rewrite rows in the frozen manifest. Merge-only rows do not enter a rewrite
chunk.

| Cursor order | Source | Triage action | Chunk D decision |
|---:|---|---|---|
| 1 | `website-copy-standard.md` | Rewrite | Eligible; selected |
| 2 | `bq-124-retro-verification.md` | Rewrite | Protected stop: production worker shell, `RAILWAY_TOKEN`, and production-row evidence |
| 3 | `build-queue-lifecycle.md` | Rewrite | Protected stop: token-scoped mutations and production datastore mechanics |
| 4 | `codex-mp.md` | Merge | Skipped; M1 remains Max-gated and this is a rewrite chunk |
| 5 | `constitution-amendment.md` | Rewrite | Unavailable at the exact local-main base; no source invented or imported |
| 6 | `dev-tickets.md` | Rewrite | Protected stop: customer-ticket and production-database verification path |
| 7 | `max-reporting.md` | Rewrite | Eligible; selected |
| 8 | `rtk-token-optimization.md` | Rewrite | Eligible; selected |

The selected destinations are:

| Order | Source | DRAFT destination |
|---:|---|---|
| 1 | `website-copy-standard.md` | `runbooks/website-copy-standard.md` |
| 2 | `max-reporting.md` | `runbooks/max-reporting.md` |
| 3 | `rtk-token-optimization.md` | `runbooks/rtk-token-optimization.md` |

The three protected stops are scope transfers only. Athena made no destination
edit, archive recommendation, retirement decision, or operational claim for
those files.

## 4. Truth-preservation ledger

### 4.1 Website copy

| Source material | Destination treatment |
|---|---|
| Scope and exclusions | §§A-C |
| Visible and machine-readable copy alignment | §§B-C, E-03, F-03, G-03 |
| Voice, banned language, and company-scale rule | §E source-preservation note, F-01, G-01 |
| Mechanics-backed shipped claims | E-01, F-02, G-02 |
| Calls to action and buyer/seller balance | E-02, F-04, G-04 |
| Discoverability and text-not-image directives | §§E, H |
| Same-change verification and lifecycle | §§E, J |

The source does not provide current site conformance, deployment credentials,
an escalation contact, a public schema guarantee, or BREAKING/REVIEW/SAFE
classification rules. Those facts remain `Unknown`.

### 4.2 Max reporting

| Source material | Destination treatment |
|---|---|
| CORE §3 canonicality and opening-prompt subordination | §§A, C, H |
| One summary and two carve-outs | §§C, E, H |
| Summary structure, exclusions, timestamp, and marker | E-01, F-02/F-05, G-02/G-05 |
| Hard-stop and blocking-question behavior | E-02/E-03, acceptance scenarios |
| CORE amendment and marker-test synchronization | E-04, F-03, G-03, H |
| Waiver-store discharge path | F-04, G-04 |
| Change classifications and adjudication | §H |

The rewrite shortens repetition but retains the source's operator decisions,
failure routes, invariants, and acceptance coverage. It does not claim a newer
boot-contract run, waiver mutation, or constitutional amendment.

### 4.3 RTK token optimization

| Source material | Destination treatment |
|---|---|
| Purpose, claimed savings, and four compression strategies | §§A-B |
| CC, AG, MP, and Vulcan integration boundaries | §§C-D |
| Telemetry, tee, and exclusion configuration | §§C, E, H |
| Gain, discover, version, and hook-status commands | E-01/E-02 |
| Upgrade and uninstall forms | E-03 |
| Three inherited troubleshooting paths | §§F-G |
| Historical version and S388 decision | §§A-B |

The source does not identify a runtime owner, escalation contact, credential
scope, current installed version, current savings, compatibility contract, or
change classifications. Those facts remain `Unknown`; historical values are
never promoted into current defaults.

## 5. Ten-field DRAFT frontmatter

Each destination contains all ten catalog fields:

1. `runbook_id`
2. `domain`
3. `status`
4. `authoritative_for`
5. `aliases`
6. `error_signatures`
7. `supersedes`
8. `superseded_by`
9. `owner`
10. `last_verified_at`

All statuses are `DRAFT`. No generated catalog surface is touched.

## 6. Word-count deltas

Counts use `wc -w` against the unchanged exact-base source and DRAFT destination:

| Source → destination | Before | After | Delta | Percent |
|---|---:|---:|---:|---:|
| `website-copy-standard.md` → `runbooks/website-copy-standard.md` | 612 | 2,158 | +1,546 | +252.61% |
| `max-reporting.md` → `runbooks/max-reporting.md` | 3,159 | 2,314 | -845 | -26.75% |
| `rtk-token-optimization.md` → `runbooks/rtk-token-optimization.md` | 573 | 2,200 | +1,627 | +283.94% |

Expansion supplies the required structured forms and explicit unknowns.
Contraction in Max reporting removes repetition from an already structured
source without adding or broadening authority.

## 7. Validation record

The local-main wrapper remains broken under T-2026-000476. Validation therefore
executes all 21 current strict checks directly from the catalog-aware checker at
`968fa2076c320e27c09104e818f1f9d480f40e55`, with catalog-only frontmatter
fields stripped before the A-K checks.

Required final evidence:

- 21 strict checks per file, 63 direct invocations, zero findings;
- `git diff --check` clean;
- exactly the three DRAFT destinations and this trace changed;
- root sources unchanged;
- catalog, router, and README inventory unchanged;
- author and committer `athena <athena@ai.market>`.

## 8. Remaining gates

- Protected owners must triage the three stopped files.
- A later owner must reconcile the RTK source divergence before promotion.
- A non-author review is required before any future ACTIVE promotion.
- Catalog generation and frontmatter ownership remain outside Athena's chunk.
- Mars or Vulcan performs any remote relay after verifying the bundle.
