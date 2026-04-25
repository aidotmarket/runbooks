# BQ-RUNBOOK-DECENTRALIZATION Gate 1 Design Spec

## §0 Header

| Field | Value |
|---|---|
| BQ code | `BQ-RUNBOOK-DECENTRALIZATION` |
| Status | Gate 1 R3 design spec |
| Target repo | `aidotmarket/runbooks` |
| Local repo | `/Users/max/Projects/runbooks` |
| R1 baseline commit | `ebf589c826e39fa86a47dc20f998b58076f861e8` |
| R1 baseline line count | 1,096 |
| R2 parent commit | `ebf589c826e39fa86a47dc20f998b58076f861e8` |
| R2 authoring date | 2026-04-25 |
| R2 final line count | 1,197 |
| R3 parent commit | `b43dc51` |
| R3 authoring date | 2026-04-25 |
| R3 final line count | 1,243 |
| Branch | `main` |
| Authoring session | S505 R3 |
| Decision input | `decision:runbook-architecture-decentralization` v1 |
| Living State input | `build:bq-runbook-decentralization` v3 |
| MP audit input | [/tmp/runbook-audit-mp-2026-04-25.md](/tmp/runbook-audit-mp-2026-04-25.md:1) |
| AG audit input | [/Users/max/.gemini/tmp/runbooks/runbook-audit-ag-2026-04-25.md](/Users/max/.gemini/tmp/runbooks/runbook-audit-ag-2026-04-25.md:1) |
| Parent standard | [specs/BQ-RUNBOOK-STANDARD.md](/Users/max/Projects/runbooks/specs/BQ-RUNBOOK-STANDARD.md:1) |
| Template | [templates/runbook.template.md](/Users/max/Projects/runbooks/templates/runbook.template.md:1) |
| Sibling BQ | `BQ-RUNBOOK-IMPACT-GATE`; owns per-service PR-time impact gate internals |

### §0.1 Prior-Art Inputs

1. MP audit reviewed 33 root operational files plus support files and found every listed operational runbook non-conformant against the current standard at [/tmp/runbook-audit-mp-2026-04-25.md:7](/tmp/runbook-audit-mp-2026-04-25.md:7) and [/tmp/runbook-audit-mp-2026-04-25.md:11](/tmp/runbook-audit-mp-2026-04-25.md:11).
2. MP audit found the current README contradicts itself by claiming universal conformance while the adoption table says no systems are conformant at [/tmp/runbook-audit-mp-2026-04-25.md:12](/tmp/runbook-audit-mp-2026-04-25.md:12). The current repo README shows that claim at [README.md](/Users/max/Projects/runbooks/README.md:3).
3. MP audit recommended cluster-based retrofits and a PR-time runbook-impact gate at [/tmp/runbook-audit-mp-2026-04-25.md:19](/tmp/runbook-audit-mp-2026-04-25.md:19) through [/tmp/runbook-audit-mp-2026-04-25.md:21](/tmp/runbook-audit-mp-2026-04-25.md:21).
4. AG audit identified the centralized corpus as an information-architecture problem at [/Users/max/.gemini/tmp/runbooks/runbook-audit-ag-2026-04-25.md:7](/Users/max/.gemini/tmp/runbooks/runbook-audit-ag-2026-04-25.md:7) through [/Users/max/.gemini/tmp/runbooks/runbook-audit-ag-2026-04-25.md:15](/Users/max/.gemini/tmp/runbooks/runbook-audit-ag-2026-04-25.md:15).
5. AG audit recommended docs-as-code colocation with service repos, while keeping the centralized repo as tooling plus generated index, at [/Users/max/.gemini/tmp/runbooks/runbook-audit-ag-2026-04-25.md:36](/Users/max/.gemini/tmp/runbooks/runbook-audit-ag-2026-04-25.md:36) through [/Users/max/.gemini/tmp/runbooks/runbook-audit-ag-2026-04-25.md:40](/Users/max/.gemini/tmp/runbooks/runbook-audit-ag-2026-04-25.md:40).
6. Max selected Option B in `decision:runbook-architecture-decentralization` v1: runbooks move to service repos; this repo becomes meta-tooling; CI enforcement runs per service repo.
7. `build:bq-runbook-decentralization` v3 provides the controlling AC1-AC9, five candidate chunks, and six carved Gate 1 questions.

### §0.2 Service Repo Existence Verification

| Repo | Requested local path | Git HEAD observed | `/docs` observed | Notes |
|---|---|---:|---:|---|
| ai-market-backend | `/Users/max/Projects/ai-market/ai-market-backend` | `410d0d5` | yes, 35 root markdown files | Existing docs tree is broad; runbook files may live under `docs/` or `docs/runbooks/` until normalized. |
| ai-market-frontend | `/Users/max/Projects/ai-market/ai-market-frontend` | `5ab731b` | no | Chunk 4 must create `/docs`. |
| koskadeux-mcp | `/Users/max/koskadeux-mcp` | `c6a334b` | yes, 10 root markdown files | Also has `runbooks/` references in specs; target is `/docs` for this BQ unless Council explicitly exempts one path. |
| aim-node | `/Users/max/Projects/ai-market/aim-node` | `4427706` | yes, 1 root markdown file | Existing `docs/DEVELOPMENT.md`; runbooks must be added. |
| vectoraiz | `/Users/max/Projects/ai-market/vectoraiz` | not present | no | Requested path does not exist locally. Existing candidate is `/Users/max/Projects/vectoraiz/vectoraiz-monorepo` at `dcfd13b` with `/docs`. |
| runbooks meta-repo | `/Users/max/Projects/runbooks` | `b43dc51` | n/a | Remains standard, linter, harness, generated index, central cross-cutting runbooks, and dated evidence. |

### §0.3 Gate 1 Output

This document is a design contract, not a migration PR. It specifies where docs move, how the generated index works, how chunk deletes become safe, and what evidence must be produced in Gate 2 and Gate 3. It does not move or delete the existing operational runbooks.

## §1 Problem & Context

The current runbook corpus grew as a flat central collection under `/Users/max/Projects/runbooks`. The MP audit found 33 operational root files and zero conformance to the current standard. The AG audit described the same shape as a "bag of documents" problem: discovery is weak, lifecycle is unclear, and copied cross-cutting procedures drift.

The technical problem is not only document formatting. The current architecture lets service code and its operational documentation evolve in different repositories, with different review flows and no reliable same-PR forcing function. That mismatch produced concrete drift:

1. `morning-briefing.md` describes the automatic briefing path as CRM Steward timer driven, but backend code now owns the scheduled path; MP classifies this as wrong at [/tmp/runbook-audit-mp-2026-04-25.md:13](/tmp/runbook-audit-mp-2026-04-25.md:13).
2. Gmail OAuth, briefing, CRM, Celery, and Google auth material is repeated across multiple runbooks, creating contradictory first actions and stale SQL examples, as mapped at [/tmp/runbook-audit-mp-2026-04-25.md:77](/tmp/runbook-audit-mp-2026-04-25.md:77) through [/tmp/runbook-audit-mp-2026-04-25.md:85](/tmp/runbook-audit-mp-2026-04-25.md:85).
3. The README claims all runbooks conform while the adoption table says none do, visible in [README.md](/Users/max/Projects/runbooks/README.md:3) through [README.md](/Users/max/Projects/runbooks/README.md:10).
4. Existing standards tooling is central-repo oriented even though the standard itself is location-orthogonal; `runbook-lint` and `runbook-harness` must work against service repo paths as first-class targets.

Option B promises the following:

1. Service-specific runbooks live with their service code under each service repo's `/docs` directory.
2. The `aidotmarket/runbooks` repo stops being the universal home for service runbooks and becomes the meta-repo for the standard, linter, harness, shared GitHub Action, generated index, and approved cross-cutting SSOT docs.
3. A generated cross-repo index restores discoverability after decentralization.
4. Per-service CI runs lint and harness on the runbooks in that service repo.
5. Cross-cutting topics may remain central only where central ownership is the real SSOT.

### §1.1 Why This Is a Gate 1 BQ

This migration changes repository boundaries, doc ownership, CI wiring, CODEOWNERS requirements, and the meaning of the runbooks repo README. A direct file-move PR would create broken references and ambiguous ownership. Gate 1 must define sequencing, safety checks, and acceptance evidence before any Chunk 3 or Chunk 4 delete happens.

### §1.2 Relationship to BQ-RUNBOOK-STANDARD

The runbook standard remains unchanged. Its required template begins with YAML frontmatter and sections `§A` through `§K` in [templates/runbook.template.md](/Users/max/Projects/runbooks/templates/runbook.template.md:1) through [templates/runbook.template.md](/Users/max/Projects/runbooks/templates/runbook.template.md:120). This BQ changes runbook location and discovery. It does not change content rules, lint semantics, harness semantics, section ordering, scenario count, or conformance thresholds.

### §1.3 Relationship to BQ-RUNBOOK-IMPACT-GATE

`BQ-RUNBOOK-IMPACT-GATE` owns the detailed implementation of per-service PR-time enforcement: path manifests, diff matching, waiver syntax, and CI fail behavior. This BQ depends on that sibling work but does not design its internals. This BQ must, however, define the interfaces that impact-gate consumes: per-service runbook locations, index schema, conformance metadata, and CODEOWNERS expectations.

### §1.4 R2 Mandate Resolution Table

| Mandate | R2 resolution | Spec citation |
|---|---|---|
| M1 | Refresh workflow concurrency, idempotence, rebase/retry, and all-repo scan rules. | §7.1 lines 717-724; §7.5 lines 820-840 |
| M2 | Chunk 1 bootstrap allows fixture-only tests plus `docs_status: NO_MANIFEST` rows, or one seeded service manifest before real-row assertions. | §5.1.6 lines 271-281; §7.2 lines 728-777 |
| M3 | Chunk 4 migration order is topological, with Koskadeux and release ownership decisions before deletes. | §5.4.5 lines 491-504 |
| M4 | §11 inventory now declares non-exhaustive Gate 1 status, requires fresh scans per migration PR, and adds per-source evidence rows including the missing backend/Koskadeux references. | §11 lines 1057-1185 |
| M5 | Shared GitHub Action is versioned from the runbooks meta-repo; service repos pin tags or SHAs and follow an upgrade procedure. | §7.7 lines 852-863; §10.4 lines 1028-1032 |
| M6 | GitHub API discovery auth, permissions, private-repo semantics, ETag caching, and fail-closed behavior are specified. | §5.1.5 lines 264-268; §5.1.6 lines 271-281; §7.2 lines 728-777 |
| M7 | Multi-repo conformance lint is an acceptance criterion and feeds index aggregation with fail-closed repo status. | §5.5.6 lines 573-581; §6.5 lines 651-662 |
| M8 | vectoraiz decision row names the canonical GitHub repo, local path, `/docs` owner, and mapping from `aidotmarket/vectoraiz`. | §10.1 lines 996-1007 |
| M9 | `runbook-index.json` is canonical; README and `INDEX.md` are generated from it with hash checks. | §4.4 lines 190-198; §5.5.6 line 581; §7.4 lines 809-817 |
| M10 | `rtk-token-optimization.md` and `vulcan-configuration.md` are classified as central candidates in Chunk 2/4 catalog. | §4.5 lines 200-211; §5.2.2 lines 304-315; §5.4.2 lines 457-475; §10.2 lines 1009-1020 |
| M11 | §11 explicitly states the Gate 1 inventory is non-exhaustive and mandates fresh scans before each migration PR. | §11 lines 1057-1059 |
| M12 | Waiver-drift mitigation adds a quarterly Council audit of waiver count, nonconformant runbooks, and lint bypasses. | §6.11 lines 711-713; §8.6 lines 917-919 |

### §1.5 R3 Mandate Resolution Table

| Mandate | R3 resolution | Spec citation |
|---|---|---|
| R3-M1 | Chunk 4 now names an ordered migration sequence by repo, with dependency rationale for backend template reuse, Koskadeux Council/dispatch ownership, AIM/vectoraiz release split, and frontend cross-reference blockers. | §5.4.5 lines 511-517 |
| R3-M2 | §11.3 now includes explicit deletion-inventory rows for the seven named missing source files, including current scan commands, hit counts across backend/Koskadeux/runbooks, live-vs-historical classification, and target or retirement decision. | §11.3 lines 1139-1146; §11.3 line 1168 |
| R3-M3 | Quarterly waiver audit now names Vulcan, MP, AG, and Council responsibilities; defines CI/index/grep inputs; records drift indicators and indexer schema follow-up; and specifies Living State plus follow-up-BQ outputs. | §6.11 lines 728-745; §8.6 lines 951-958 |

## §2 Goals

The measurable outcomes are the AC1-AC9 set from `build:bq-runbook-decentralization` plus three index-specific outcomes added by this Gate 1 spec.

| Goal | Source AC | Outcome | Evidence |
|---|---|---|---|
| G1 | AC1 | Every operational root runbook is moved, retained as cross-cutting, retired, or explicitly classified. | `runbooks-manifest.yml` plus generated index diff. |
| G2 | AC2 | [README.md](/Users/max/Projects/runbooks/README.md:1) stops claiming universal conformance and becomes the meta-repo entry point. | README diff and generated section marker. |
| G3 | AC3 | Each service repo has `/docs` with at least one conformant runbook or a documented exception for missing local repo. | Per-repo file existence, lint result, harness result. |
| G4 | AC4 | Cross-repo index auto-generates from service `/docs/*.md` and central cross-cutting runbooks. | `runbook-index refresh --check` passes. |
| G5 | AC5 | Lint and harness operate on service-repo runbook paths. | Integration tests using at least three service repo fixture paths. |
| G6 | AC6 | Inbound links in code, comments, specs, prompts, and Living State are updated when targets move. | Reference inventory matrix with zero stale references for moved files. |
| G7 | AC7 | Dated evidence under `ops/` can remain central and is excluded from runbook conformance migration. | README policy and index exclusion test. |
| G8 | AC8 | Vulcan lookup/dispatch patterns point to generated index and new paths. | Resource registry or prompt reference diff. |
| G9 | AC9 | `BQ-CRM-RUNBOOK-STANDARD` target changes to backend `/docs/crm-system.md`. | Living State/body or spec reference update in CRM chunk. |
| G10 | New | Index supports auto-discovery and static service config fallback. | Unit tests covering GitHub API failure fallback. |
| G11 | New | Index reports conformance status, not only file presence. | Schema test plus sample README/INDEX output. |
| G12 | New | Index refresh cadence is automated daily and on service PR merge. | GitHub Action workflow evidence. |

## §3 Non-Goals

1. This BQ does not revise `BQ-RUNBOOK-STANDARD` content requirements, required sections, linter checks, harness score thresholds, or template grammar.
2. This BQ does not retrofit any individual operational runbook to `§A` through `§K`; it designs where retrofits land and how migration becomes safe.
3. This BQ does not move, rewrite, or delete files in this Gate 1 commit.
4. This BQ does not touch dated operational evidence files such as [ops/briefing-verification-2026-04-25.md](/Users/max/Projects/runbooks/ops/briefing-verification-2026-04-25.md:1) except to define that evidence can stay central.
5. This BQ does not implement the PR-time impact gate internals; that belongs to `BQ-RUNBOOK-IMPACT-GATE`.
6. This BQ does not require every markdown file in a service repo `/docs` directory to be a conformant runbook. Only files marked as `runbook: true` by frontmatter or manifest entry participate.
7. This BQ does not decide whether the standard eventually needs a lite tier. AG raised that risk at [/Users/max/.gemini/tmp/runbooks/runbook-audit-ag-2026-04-25.md:68](/Users/max/.gemini/tmp/runbooks/runbook-audit-ag-2026-04-25.md:68), but this migration proceeds with the current standard.
8. This BQ does not make `/Users/max/Projects/ai-market/vectoraiz` exist. It records the missing requested path and recommends Council adopt `/Users/max/Projects/vectoraiz/vectoraiz-monorepo` if that is the current repo.
9. This BQ does not change historical specs that cite old paths unless the cited target file is actually moved by Chunk 3 or Chunk 4.

## §4 Design Overview

Option B has three layers:

```text
aidotmarket/runbooks (meta-repo)
  specs/
    BQ-RUNBOOK-STANDARD.md
    bq-runbook-decentralization-gate1.md
  templates/
  schemas/
  runbook_tools/
    lint
    harness
    index
  .github/actions/runbook-ci/
  README.md            generated entry table
  INDEX.md             generated full cross-repo index
  gcp-auth.md          central cross-cutting SSOT, until renamed/retrofitted
  infisical-secrets.md central cross-cutting SSOT, until renamed/retrofitted
  gmail-oauth-watch.md central cross-cutting SSOT, new target
  koskadeux-operations.md central cross-cutting SSOT under the §10.2 decision
  ops/                 dated evidence only

service repo
  docs/
    <service-runbook>.md
    <subsystem-runbook>.md
    runbook-manifest.yml
  .github/workflows/runbook-ci.yml
  CODEOWNERS
```

### §4.1 Ownership Model

1. Service-specific runbook ownership follows the service repository that owns the code and deployable surface.
2. Cross-cutting runbook ownership remains central when the procedure is not owned by a single service repo or when copying it into services would create drift.
3. `owner_agent` in frontmatter remains authoritative for operational ownership; CODEOWNERS determines Git review ownership.
4. The generated index is the discoverability layer; it is not the ownership layer.

### §4.2 Directory Model

The primary target is each repo's `/docs` directory, with these allowed forms:

1. `/docs/<runbook>.md` for service or subsystem runbooks.
2. `/docs/runbooks/<runbook>.md` for repos that already use a runbook subdirectory, but the generated index must normalize this as a service repo doc path.
3. `/docs/runbook-manifest.yml` for path mapping, owner metadata, and conformance override fields.
4. `/docs/README.md` may link runbooks but is not itself required to be a conformant runbook.

### §4.3 Classification Model

Every root operational markdown file in the current runbooks repo gets one of four terminal classes:

| Class | Meaning | Example |
|---|---|---|
| `service-move` | Target is a service repo `/docs` file. | `ai-market-backend.md` to backend `/docs/backend-platform.md`. |
| `service-merge` | Content merges into a new or existing service repo runbook, then source deletes. | `crm-architecture.md`, `crm-pipeline.md`, `crm-target-state.md` into backend `/docs/crm-system.md`. |
| `central-cross-cutting` | Stays in runbooks meta-repo because it is cross-service SSOT. | `gcp-auth.md`, `infisical-secrets.md`, future `gmail-oauth-watch.md`. |
| `retire-or-evidence` | Stops being a standing runbook; moves to `ops/` or is deleted with recorded rationale. | `bq-124-retro-verification.md`. |

### §4.4 Generated Index

The canonical generated artifact is `runbook-index.json`. The refresh command reads service repo manifests and runbook frontmatter, writes `runbook-index.json` first, then derives the human outputs from that JSON. README and `INDEX.md` are therefore generated views, not separate sources of truth.

Outputs:

1. `runbook-index.json`: canonical machine-readable artifact for Vulcan lookup and future dashboards.
2. `README.md`: concise dashboard table generated from the canonical JSON.
3. `INDEX.md`: full detail generated from the canonical JSON, with one row per indexed runbook, stale-reference warnings, conformance status, and source repo path.

### §4.5 Central Retained Topics

This Gate 1 recommends retaining these central cross-cutting topics:

| Topic | Central target | Rationale |
|---|---|---|
| GCP auth | `gcp-auth.md` or `gcp-auth.md` retrofit target | Shared OAuth/GCP setup is not owned by one service. |
| Infisical | `infisical.md` eventual target, replacing `infisical-secrets.md` per existing standard chunk intent | Secret lifecycle and emergency recovery span service repos. |
| Gmail OAuth/watch | `gmail-oauth-watch.md` | Gmail watch and OAuth token handling are shared infrastructure; service runbooks reference it. |
| Koskadeux operations | `koskadeux-operations.md` under the §10.2 decision | Council/dispatch/session operation is cross-agent infrastructure; however, code-local subprocedures may still live in `koskadeux-mcp/docs` if Gate 2 records a narrower owner. |
| RTK token optimization | `rtk-token-optimization.md` or central policy appendix | Token-optimization policy affects dispatch/runtime behavior across agents and should not be copied into one service unless code ownership proves otherwise. |
| Vulcan configuration | `vulcan-configuration.md` or central policy appendix | Vulcan lookup/context policy is cross-cutting unless Council decides it belongs inside Koskadeux model-configuration docs. |

### §4.6 CRM Scope Adjustment

Under Option B, `BQ-CRM-RUNBOOK-STANDARD` no longer targets `aidotmarket/runbooks/crm-system.md` or `crm-target-state.md`. Its target is:

```text
/Users/max/Projects/ai-market/ai-market-backend/docs/crm-system.md
```

This target is required by AC9 and must be written into the CRM BQ body or follow-on spec before CRM migration starts.

## §5 Per-Chunk Design

## §5.1 Chunk 1: Foundation - Cross-Repo Index Tooling

### §5.1.1 Scope

Chunk 1 builds the meta-repo foundation before any mass migration:

1. Add index discovery config in the runbooks repo.
2. Add `runbook-index` CLI or `runbook_tools index` subcommand.
3. Generate `INDEX.md`, `runbook-index.json`, and a README dashboard block.
4. Add tests covering service repo discovery, conformance metadata extraction, static config fallback, and exclusion of dated evidence.
5. Add GitHub Action workflow for scheduled refresh and repository dispatch refresh.

### §5.1.2 Files

| Current location | Planned location | Action |
|---|---|---|
| [runbook_tools](/Users/max/Projects/runbooks/runbook_tools/__init__.py:1) | `runbook_tools/index/` | Add index package. |
| [README.md](/Users/max/Projects/runbooks/README.md:1) | same | Replace false universal-conformance claim with generated dashboard. |
| none | `INDEX.md` | Add generated full index. |
| none | `runbook-index.json` | Add generated machine-readable artifact. |
| none | `.github/workflows/runbook-index.yml` | Add scheduled + dispatch refresh. |
| none | `runbook-index.repos.yml` | Static service repo config fallback. |
| none | `tests/test_runbook_index.py` | Unit and integration tests. |

### §5.1.3 LOC Delta Estimate

| Area | Estimate |
|---|---:|
| Index package | +350 to +500 |
| CLI wiring | +50 to +90 |
| Tests | +300 to +450 |
| README/INDEX generated output | +80 to +180 |
| Workflow/config | +60 to +100 |
| Total | +840 to +1,320 |

### §5.1.4 Risk

Risk is medium. Bad index generation can hide runbooks and worsen fragmentation. The safety constraint is that the generated index must fail closed: a configured repo that cannot be scanned is listed with `discovery_status: ERROR`, not silently omitted.

### §5.1.5 Dependencies

1. Current linter and harness package in `runbook_tools`.
2. GitHub token or local clone access for service repos. `GITHUB_TOKEN` is sufficient only for the runbooks repo itself; private cross-repo discovery requires a fine-grained PAT or GitHub App installation with `contents: read` on every configured private repo.
3. `BQ-RUNBOOK-IMPACT-GATE` for later PR-time enforcement, not for Chunk 1 index generation.
4. Service repo list from §10.1, including the vectoraiz canonical path.

### §5.1.6 Test/Verification Strategy

1. Unit test schema validation for index rows.
2. Unit test frontmatter extraction from conformant runbook fixture.
3. Unit test manifest override when frontmatter is missing.
4. Unit test evidence exclusion: `ops/*.md` is not treated as operational runbook.
5. Integration test scans at least three local service repos and produces rows.
6. `runbook-index refresh --check` fails if generated files are stale.
7. Bootstrap rule: before one real service manifest exists, integration tests may use fixtures and configured repo rows with `docs_status: NO_MANIFEST`; once a service repo is manually seeded, recommended first seed is `ai-market-backend/docs/runbook-manifest.yml`, real-row discovery assertions become mandatory for that repo.
8. Discovery failure tests cover 403, 404, and rate-limit responses; each emits `discovery_status: ERROR` and a nonzero `--check` result instead of silently omitting the repo.
9. `git diff --check` passes.

### §5.1.7 Migration Safety

Chunk 1 does not move or delete runbooks. Its safety obligation is reversibility: generated blocks are bounded by markers and can be regenerated from source manifests.

### §5.1.8 Acceptance Notes

Chunk 1 must land before Chunk 3 or Chunk 4. A migration PR that deletes central files without a working generated index is not acceptable.

## §5.2 Chunk 2: Cross-Cutting Topics Decision

### §5.2.1 Scope

Chunk 2 produces the authoritative classification manifest for all existing root runbooks:

1. `service-move`
2. `service-merge`
3. `central-cross-cutting`
4. `retire-or-evidence`

It also updates README policy text explaining what belongs in the runbooks meta-repo after decentralization.

### §5.2.2 Files

| Current location | Planned location | Action |
|---|---|---|
| root `*.md` operational runbooks | `runbook-migration-manifest.yml` | Add one row per file. |
| [README.md](/Users/max/Projects/runbooks/README.md:1) | same | Add central-vs-service policy. |
| [gcp-auth.md](/Users/max/Projects/runbooks/gcp-auth.md:1) | central | Retain as cross-cutting SSOT until retrofit. |
| [infisical-secrets.md](/Users/max/Projects/runbooks/infisical-secrets.md:1) | central, future `infisical.md` | Retain central and track rename/retrofit. |
| [gmail-drop-pipeline.md](/Users/max/Projects/runbooks/gmail-drop-pipeline.md:1) | split: backend CRM references plus central `gmail-oauth-watch.md` | Decide shared content boundary. |
| [agent-dispatch.md](/Users/max/Projects/runbooks/agent-dispatch.md:1) and Council files | central `koskadeux-operations.md` or `koskadeux-mcp/docs` | Apply §10.2 central-candidate decision and record any Gate 2 override explicitly. |
| [rtk-token-optimization.md](/Users/max/Projects/runbooks/rtk-token-optimization.md:1) | central policy candidate | Classify as central unless reference scan proves it is only Koskadeux-local procedure. |
| [vulcan-configuration.md](/Users/max/Projects/runbooks/vulcan-configuration.md:1) | central policy candidate | Classify as central unless Council folds it into Koskadeux model-configuration docs. |

### §5.2.3 LOC Delta Estimate

| Area | Estimate |
|---|---:|
| Manifest | +120 to +220 |
| README policy | +80 to +140 |
| Classification rationale appendix | +150 to +250 |
| Tests for manifest schema | +80 to +140 |
| Total | +430 to +750 |

### §5.2.4 Risk

Risk is medium. Misclassifying a cross-cutting topic as service-specific can create copied procedures and drift. Misclassifying a service-specific topic as central preserves the current architecture defect.

### §5.2.5 Dependencies

1. MP redundancy map at [/tmp/runbook-audit-mp-2026-04-25.md:73](/tmp/runbook-audit-mp-2026-04-25.md:73).
2. AG decentralization rationale at [/Users/max/.gemini/tmp/runbooks/runbook-audit-ag-2026-04-25.md:36](/Users/max/.gemini/tmp/runbooks/runbook-audit-ag-2026-04-25.md:36).
3. §10.2 central keep-list decision.

### §5.2.6 Test/Verification Strategy

1. Manifest schema test: every root operational markdown file appears exactly once.
2. Manifest target path test: service targets are under configured repo `/docs`.
3. Manifest policy test: `ops/` evidence is excluded unless explicitly classified.
4. README generated table includes central retained docs and service docs separately.

### §5.2.7 Migration Safety

Chunk 2 does not delete central files. It only records the intended fate and blocks future migrations from inventing target paths ad hoc.

### §5.2.8 Acceptance Notes

Acceptance requires an explicit manifest row for each file listed in the MP audit compliance table at [/tmp/runbook-audit-mp-2026-04-25.md:29](/tmp/runbook-audit-mp-2026-04-25.md:29) through [/tmp/runbook-audit-mp-2026-04-25.md:63](/tmp/runbook-audit-mp-2026-04-25.md:63).

## §5.3 Chunk 3: First Service Migration - ai-market-backend

### §5.3.1 Scope

Chunk 3 migrates the highest-risk backend/CRM/Gmail/Celery cluster first. It is intentionally large because MP identified CRM/briefing/Gmail as the highest-risk drift area and backend has the broadest runbook surface.

Recommended backend targets:

1. `/Users/max/Projects/ai-market/ai-market-backend/docs/backend-platform.md`
2. `/Users/max/Projects/ai-market/ai-market-backend/docs/crm-system.md`
3. `/Users/max/Projects/ai-market/ai-market-backend/docs/celery-infrastructure.md`
4. `/Users/max/Projects/ai-market/ai-market-backend/docs/seo-discovery.md`
5. `/Users/max/Projects/ai-market/ai-market-backend/docs/marketplace-mcp-public.md`
6. `/Users/max/Projects/ai-market/ai-market-backend/docs/marketing-ops.md` if marketing remains backend-owned
7. Central `/Users/max/Projects/runbooks/gmail-oauth-watch.md` for shared Gmail OAuth/watch SSOT, referenced by backend docs

### §5.3.2 Files

| Current location | Planned location | Action |
|---|---|---|
| [ai-market-backend.md](/Users/max/Projects/runbooks/ai-market-backend.md:1) | backend `/docs/backend-platform.md` | Move/retrofit; remove subsystem duplication. |
| [crm-architecture.md](/Users/max/Projects/runbooks/crm-architecture.md:1) | backend `/docs/crm-system.md` | Merge, then delete source after references update. |
| [crm-pipeline.md](/Users/max/Projects/runbooks/crm-pipeline.md:1) | backend `/docs/crm-system.md` | Merge, then delete source after references update. |
| [crm-target-state.md](/Users/max/Projects/runbooks/crm-target-state.md:1) | backend `/docs/crm-system.md` | Merge target-state facts into conformant runbook. |
| [morning-briefing.md](/Users/max/Projects/runbooks/morning-briefing.md:1) | backend `/docs/crm-system.md` plus central `gmail-oauth-watch.md` refs | Merge correct scheduled path; delete source. |
| [gmail-drop-pipeline.md](/Users/max/Projects/runbooks/gmail-drop-pipeline.md:1) | central `gmail-oauth-watch.md` plus backend CRM refs | Split shared OAuth/watch from service behavior. |
| [email-drafting.md](/Users/max/Projects/runbooks/email-drafting.md:1) | backend `/docs/crm-system.md` or `/docs/email-system.md` | Merge if CRM/outreach-owned. |
| [celery-infrastructure-deployment.md](/Users/max/Projects/runbooks/celery-infrastructure-deployment.md:1) | backend `/docs/celery-infrastructure.md` | Move/retrofit. |
| [bq-124-retro-verification.md](/Users/max/Projects/runbooks/bq-124-retro-verification.md:1) | backend `/docs/celery-infrastructure.md` appendix or central `ops/` evidence | Retire as standing runbook. |
| [seo-infrastructure.md](/Users/max/Projects/runbooks/seo-infrastructure.md:1) | backend `/docs/seo-discovery.md` | Merge or cross-link. |
| [seo-seller-validation.md](/Users/max/Projects/runbooks/seo-seller-validation.md:1) | backend `/docs/seo-discovery.md` or frontend docs if UI-owned | Decide in Chunk 3 preflight. |
| [aimarket-mcp-server.md](/Users/max/Projects/runbooks/aimarket-mcp-server.md:1) | backend `/docs/marketplace-mcp-public.md` | Move if public marketplace MCP is backend-owned. |
| [allai-agents.md](/Users/max/Projects/runbooks/allai-agents.md:1) | backend `/docs/backend-platform.md` or CRM/system docs | Merge only current operational content. |
| [marketing-tab.md](/Users/max/Projects/runbooks/marketing-tab.md:1) | backend `/docs/marketing-ops.md` or frontend docs | Decide by code ownership. |
| [ops-ai-market.md](/Users/max/Projects/runbooks/ops-ai-market.md:1) | backend docs or retained central policy | Audit ownership before move. |
| [meet-records-pipeline.md](/Users/max/Projects/runbooks/meet-records-pipeline.md:1) | backend `/docs/meet-records-pipeline.md` or central GCP refs | Move service behavior; centralize shared auth. |

### §5.3.3 LOC Delta Estimate

| Area | Existing LOC | Target LOC Estimate |
|---|---:|---:|
| Backend platform cluster | 178 + selected allAI/platform content | 220 to 320 |
| CRM system cluster | 210 + 90 + 469 + briefing/email parts | 450 to 700 |
| Gmail OAuth/watch central split | 97 + 161 shared portions | 180 to 280 |
| Celery infrastructure | 399 + selected BQ-124 content | 260 to 420 |
| SEO/discovery | 2 source files | 180 to 320 |
| Marketplace MCP/public backend | 1 to 2 source files | 140 to 240 |
| Net effect in runbooks repo | significant deletion after merge | remove 8 to 14 root files, add/retain 1 central shared file |

### §5.3.4 Risk

Risk is high. This chunk deletes central source files after migration, changes CRM target location, and touches the cluster already known to contain stale production-impacting claims.

Primary risks:

1. A stale reference continues pointing to a deleted central file.
2. CRM runbook content silently drops procedural steps from legacy files.
3. Shared Gmail OAuth instructions are copied into backend docs instead of referenced from central SSOT.
4. `BQ-CRM-RUNBOOK-STANDARD` remains pointed at the old central path.

### §5.3.5 Dependencies

1. Chunk 1 generated index is merged and passing.
2. Chunk 2 migration manifest classifies every backend-related source.
3. `BQ-BRIEFING-PIPELINE-REMEDIATION` docs target remains backend `/docs`.
4. `BQ-RUNBOOK-IMPACT-GATE` interface is available or at least has a temporary manifest shape.
5. CODEOWNERS in backend can assign review for `/docs/*.md`.

### §5.3.6 Test/Verification Strategy

1. `runbook-lint` passes for every new conformant backend runbook.
2. `runbook-harness` passes for each conformant backend runbook with score >= 0.80 when scenario set exists.
3. Procedural coverage matrix maps every legacy operate/isolate/repair section to a new scenario or explicit removal rationale.
4. Inbound reference scan returns no references to deleted files except historical specs explicitly marked as frozen.
5. Generated index lists all backend targets and no longer lists deleted central files.
6. Backend CODEOWNERS covers new docs.
7. CRM BQ body or spec references backend `/docs/crm-system.md`.

### §5.3.7 Migration Safety

Chunk 3 may delete files from the runbooks repo only after all of these pass:

1. Source file content has a trace matrix row: `Legacy Section | Target Runbook Section | Preserve/Merge/Delete Rationale`.
2. Word-count delta is recorded for each source file and target section; >15 percent shrink requires explicit rationale.
3. Inbound references in current service repos, specs, prompts, and Living State are updated in the same migration PR or explicitly classified as frozen historical references.
4. `git grep` or `rg` proves no live reference points to a deleted path.
5. The generated index on the migration branch points users to the new path.
6. The source deletion commit includes a short tombstone in the PR description listing the target path.

### §5.3.8 Acceptance Notes

Chunk 3 acceptance should be split into backend sub-ACs so review can fail one migrated runbook without reopening the whole architecture. However, central deletes for CRM/briefing/Gmail must be reviewed together because their content boundaries overlap.

## §5.4 Chunk 4: Per-Cluster Migrations - Frontend, Koskadeux, AIM Node, vectoraiz

### §5.4.1 Scope

Chunk 4 migrates the remaining service-owned runbooks after backend migration patterns are proven:

1. ai-market-frontend service docs.
2. koskadeux-mcp service docs and/or central cross-cutting operations decision.
3. aim-node service docs.
4. vectoraiz service docs, once repo path is confirmed.
5. AIM/VZ release/distribution docs split by owning repo.

### §5.4.2 Files

| Current location | Planned location | Action |
|---|---|---|
| [ai-market-frontend.md](/Users/max/Projects/runbooks/ai-market-frontend.md:1) | frontend `/docs/frontend-marketplace.md` | Create frontend `/docs`, move/retrofit. |
| [agent-dispatch.md](/Users/max/Projects/runbooks/agent-dispatch.md:1) | central `koskadeux-operations.md` or `koskadeux-mcp/docs/koskadeux-operations.md` | Council decision; do not duplicate. |
| [council-gate-process.md](/Users/max/Projects/runbooks/council-gate-process.md:1) | same as Koskadeux operations target | Merge. |
| [council-hall-deliberation.md](/Users/max/Projects/runbooks/council-hall-deliberation.md:1) | same as Koskadeux operations target | Merge. |
| [session-lifecycle.md](/Users/max/Projects/runbooks/session-lifecycle.md:1) | same as Koskadeux operations target | Merge. |
| [mcp-gateway.md](/Users/max/Projects/runbooks/mcp-gateway.md:1) | `koskadeux-mcp/docs/koskadeux-mcp-internal.md` or central | Decide by code ownership and cross-cutting scope. |
| [rtk-token-optimization.md](/Users/max/Projects/runbooks/rtk-token-optimization.md:1) | central policy appendix or `koskadeux-mcp/docs` | Decide whether it is procedure or policy. |
| [vulcan-configuration.md](/Users/max/Projects/runbooks/vulcan-configuration.md:1) | central policy or `koskadeux-mcp/docs` | Current self-reference must be updated if moved. |
| [aim-node.md](/Users/max/Projects/runbooks/aim-node.md:1) | aim-node `/docs/aim-node-system.md` | Move/retrofit, preserving Standard G4 isolation constraints. |
| [aim-node-release-process.md](/Users/max/Projects/runbooks/aim-node-release-process.md:1) | aim-node `/docs/aim-node-release.md` or release cluster | Merge. |
| [aim-data-release-process.md](/Users/max/Projects/runbooks/aim-data-release-process.md:1) | aim-node or vectoraiz release docs | Decide based on actual repo ownership. |
| [vz-release-process.md](/Users/max/Projects/runbooks/vz-release-process.md:1) | vectoraiz `/docs/releasing.md` or aim-node release cluster | Move after vectoraiz path confirmed. |
| [docker-testing.md](/Users/max/Projects/runbooks/docker-testing.md:1) | aim-node or vectoraiz release docs | Merge into release test procedure. |
| [cloudflare-worker.md](/Users/max/Projects/runbooks/cloudflare-worker.md:1) | backend, aim-node, vectoraiz, or central split | Split DMS/infra vs release proxy concerns. |
| [dual-brand-vectoraiz-aim-channel.md](/Users/max/Projects/runbooks/dual-brand-vectoraiz-aim-channel.md:1) | vectoraiz `/docs/dual-brand-channel.md` | Move after repo path confirmed. |

### §5.4.3 LOC Delta Estimate

| Cluster | Existing LOC Estimate | Target LOC Estimate |
|---|---:|---:|
| Frontend | 91 | 120 to 220 |
| Koskadeux/Council/session | 152 + 114 + 173 + 78 + 60 + selected policy docs | 450 to 750 |
| AIM Node system/release | 250 + 2 release/checklist files | 350 to 600 |
| vectoraiz/AIM release | VZ/Docker/dual-brand/cloudflare parts | 300 to 550 |
| Net effect in runbooks repo | remove or centralize 10 to 15 root files | central retained files shrink to cross-cutting only |

### §5.4.4 Risk

Risk is high for Koskadeux and medium for frontend/AIM/vectoraiz. Koskadeux docs include agent dispatch and Council process references that affect development throughput. vectoraiz risk is currently path uncertainty: the requested service repo path is absent, while another local vectoraiz monorepo exists.

### §5.4.5 Dependencies

1. Chunk 1 and Chunk 2 complete.
2. Chunk 3 validates the delete safety pattern.
3. §10.2 central keep-list decision is applied or explicitly narrowed in Gate 2.
4. §10.1 vectoraiz canonical repo path is used.
5. Frontend `/docs` directory is created.
6. Dependency graph is documented before any Chunk 4 delete, with edges for central-vs-service ownership, release ownership, and live-reference blockers.

Concrete migration order:

1. `ai-market-backend` stays first via Chunk 3, before Chunk 4, because it proves the trace-matrix, reference-scan, generated-index, CODEOWNERS, and delete-safety pattern for the largest service-owned cluster. It also clears active CRM/Celery references such as `/Users/max/Projects/runbooks/crm-architecture.md`, `/Users/max/Projects/runbooks/crm-pipeline.md`, `/Users/max/Projects/runbooks/crm-target-state.md`, and backend-local `docs/runbooks/celery-infrastructure-deployment.md` references before remaining service deletes copy the pattern.
2. `koskadeux-mcp` is the first Chunk 4 repo because it has the highest cross-reference surface and owns the Council/dispatch/Vulcan ambiguity. Decide the central-vs-service split before deleting `agent-dispatch.md`, Council docs, `session-lifecycle.md`, `mcp-gateway.md`, `rtk-token-optimization.md`, or `vulcan-configuration.md`; live Koskadeux specs already cite `aidotmarket/runbooks/agent-dispatch.md`, `aidotmarket/runbooks/vulcan-configuration.md`, and `aidotmarket/runbooks/model-configuration.md`.
3. `aim-node` follows Koskadeux after the AIM/vectoraiz release ownership split is documented. Its migration must preserve the Standard G4 isolation constraints around `aidotmarket/runbooks/aim-node.md` and decide whether `aim-node-release-process.md` plus `aim-data-release-process.md` are AIM-owned or shared release docs.
4. `vectoraiz` follows `aim-node` because its local canonical path is unresolved and its release docs depend on the same split: `vz-release-process.md`, `docker-testing.md`, `cloudflare-worker.md`, and `dual-brand-vectoraiz-aim-channel.md` cannot be deleted until the vectoraiz repo path and release owner are confirmed. If the AIM/vectoraiz release split makes vectoraiz the sole release owner, vectoraiz may absorb the release docs immediately after the `aim-node` ownership note lands.
5. `ai-market-frontend` runs last by default because current scans show many live references to `ai-market-frontend` as a repo/service name in backend and Koskadeux specs, docs, tests, and tooling. It may move in parallel with `vectoraiz` only if the preflight scan proves zero live cross-references to the source file `ai-market-frontend.md` itself and classifies the remaining repo-name hits as non-blocking service inventory references.

### §5.4.6 Test/Verification Strategy

1. `runbook-lint` and harness on each new conformant service runbook.
2. Generated index includes frontend, koskadeux, aim-node, and vectoraiz rows.
3. Integration test scans at least three service repos; by Chunk 4 it must scan all available local service repos.
4. Reference scan proves no live references to deleted central files.
5. Service-specific CODEOWNERS entries exist.
6. For koskadeux, dispatch prompts and model-configuration specs are reviewed for old `aidotmarket/runbooks/*` paths.

### §5.4.7 Migration Safety

Chunk 4 deletes central files only after the same conditions as Chunk 3. Additional safety for Koskadeux:

1. Agent dispatch prompts must be updated in the same PR if they refer to old central paths.
2. Living State pointers to central runbooks must be updated or explicitly marked historical.
3. The generated index must be reachable from the boot/lookup path before central deletion.
4. If a central Koskadeux operations SSOT remains, service-local docs must link to it instead of copying Council-wide procedure.

### §5.4.8 Acceptance Notes

Chunk 4 can be broken into repo-specific PRs after Gate 2, but sequencing must keep reference updates and source deletes together for each moved target.

## §5.5 Chunk 5: Cleanup and Final Meta-Repo State

### §5.5.1 Scope

Chunk 5 completes decentralization:

1. Retire or move `bq-124-retro-verification.md` as non-standing evidence.
2. Remove root service-specific runbooks from runbooks repo after targets are indexed.
3. Polish README as meta-repo entry point.
4. Ensure generated index is stable on `origin/main`.
5. Document central retained policy and dated evidence policy.
6. Update any remaining references in specs that are not frozen historical citations.

### §5.5.2 Files

| Current location | Planned location | Action |
|---|---|---|
| [bq-124-retro-verification.md](/Users/max/Projects/runbooks/bq-124-retro-verification.md:1) | `ops/` evidence or backend Celery appendix | Retire from standing runbook list. |
| root service-specific `*.md` | service repo `/docs` | Delete after migrated. |
| [README.md](/Users/max/Projects/runbooks/README.md:1) | same | Final meta-repo dashboard. |
| `INDEX.md` | same | Final generated full index. |
| `runbook-index.json` | same | Machine-readable lookup artifact. |
| runbook tooling | same | Ensure all paths work outside repo root. |

### §5.5.3 LOC Delta Estimate

| Area | Estimate |
|---|---:|
| Root runbook deletions | -2,500 to -4,500 |
| README final policy | +80 to +160 |
| INDEX generated rows | +150 to +300 |
| Cleanup tests | +100 to +180 |
| Net | large negative in root prose, small positive in tooling/index |

### §5.5.4 Risk

Risk is medium. Most dangerous migration work already happened in Chunks 3 and 4, but final cleanup can still break discoverability if generated index is stale.

### §5.5.5 Dependencies

1. Chunks 1 through 4 merged.
2. No stale live references to deleted central files.
3. Daily and repository-dispatch refresh proven on `origin/main`.
4. Runbooks repo README no longer advertises itself as universal service-runbook SSOT.

### §5.5.6 Test/Verification Strategy

1. `runbook-index refresh --check` passes on clean `main`.
2. `rg` for old central runbook paths returns only approved historical references.
3. `runbook-lint --repos runbook-index.repos.yml` iterates every configured manifest, emits per-repo lint output, and writes a rollup consumed by index refresh.
4. Multi-repo lint fails closed: any required repo with discovery failure, manifest parse failure, or lint invocation failure is represented in the rollup and blocks `--check`.
5. `runbook-lint` can run against service repo paths from the runbooks repo CLI.
6. `runbook-harness` can run against service repo paths from the runbooks repo CLI.
7. README and INDEX generated block hashes match `runbook-index.json`.

### §5.5.7 Migration Safety

Cleanup may delete remaining central service-runbook files only if the manifest row is terminal and the generated index row points to the replacement or retirement rationale.

### §5.5.8 Acceptance Notes

The final acceptance state is not "runbooks repo has no markdown other than tooling." The final state is "runbooks repo has no service-specific operational runbook that belongs with service code, while central cross-cutting SSOT docs and dated evidence are explicitly retained."

## §6 Acceptance Criteria

### §6.1 AC1 - Full Classification of Existing Operational Runbooks

Evidence requirements:

1. `runbook-migration-manifest.yml` exists.
2. Every root operational markdown file from MP audit table appears exactly once.
3. Each row has `classification`, `source_path`, `target_repo`, `target_path`, `owner_agent`, `migration_chunk`, and `delete_policy`.
4. Rows classified `central-cross-cutting` include rationale.
5. Rows classified `retire-or-evidence` include whether the target is `ops/`, service appendix, or deletion.

Chunk evidence:

| Chunk | Required proof |
|---|---|
| 1 | Index can read manifest shape. |
| 2 | Manifest complete. |
| 3 | Backend rows updated to migrated/deleted states. |
| 4 | Remaining service rows updated to migrated/deleted states. |
| 5 | No unclassified root operational files remain. |

### §6.2 AC2 - README Becomes Meta-Repo Entry Point

Evidence requirements:

1. [README.md](/Users/max/Projects/runbooks/README.md:3) no longer says every runbook conforms.
2. README has a generated dashboard block with service repo, runbook path, conformance status, and last refresh.
3. README explains that the repo owns standard, lint, harness, index, central cross-cutting SSOT docs, and dated evidence.
4. README links to `INDEX.md`.

### §6.3 AC3 - Service Repos Host `/docs`

Evidence requirements:

1. Backend `/docs` exists and has conformant migrated runbooks.
2. Frontend `/docs` is created and has at least one conformant runbook.
3. Koskadeux `/docs` has conformant runbook coverage or a Council-approved central exception.
4. AIM Node `/docs` has conformant runbook coverage.
5. vectoraiz canonical repo path is corrected; its `/docs` has conformant runbook coverage.
6. Missing `/Users/max/Projects/ai-market/vectoraiz` is not silently ignored; §10.1 maps vectoraiz to `/Users/max/Projects/vectoraiz/vectoraiz-monorepo`.

### §6.4 AC4 - Cross-Repo Index Auto-Generates

Evidence requirements:

1. `runbook-index refresh` discovers all configured repos.
2. `runbook-index refresh --check` fails on stale generated output.
3. The index includes title, owner_agent, last_refreshed, conformance status, source repo, and source path.
4. Discovery failures appear as `ERROR` rows.
5. Daily cron and repository-dispatch refresh triggers exist.

Additional index ACs:

1. Auto-discovery works via GitHub API when available.
2. Static config fallback works against local clones or configured repo URLs.
3. Conformance status is not inferred from filename; it reads linter metadata or manifest override.
4. Refresh cadence appears in generated output.
5. At least one test fixture covers a non-conformant legacy doc and a conformant runbook.

### §6.5 AC5 - Lint and Harness Work Against Service Repos

Evidence requirements:

1. `runbook-lint /absolute/service/repo/docs/foo.md` works.
2. `runbook-harness --runbook /absolute/service/repo/docs/foo.md` works.
3. CLI path resolution does not assume current working directory is `/Users/max/Projects/runbooks`.
4. Tests cover absolute paths and repo-relative paths.
5. Shared GitHub Action consumes runbooks meta-repo tooling without duplicating scripts.
6. `runbook-lint --repos runbook-index.repos.yml` runs against all configured service manifests and central retained runbooks.
7. Per-repo lint output includes repo id, manifest path, file count, pass/fail count, error details, and discovery status.
8. Aggregated lint output feeds `runbook-index.json`; any required repo with missing output is `discovery_status: ERROR` and blocks generated-output checks.

### §6.6 AC6 - Inbound Links Updated

Evidence requirements:

1. Reference inventory exists and is updated in every migration chunk.
2. For each deleted central file, live references are zero.
3. Historical/frozen spec references are listed separately and do not block deletion.
4. Living State references are updated in the same chunk when they point to active operational docs.
5. Vulcan agent prompts and resource registry references are updated before deletion.

### §6.7 AC7 - Dated Evidence Policy

Evidence requirements:

1. README states `ops/` dated evidence can remain central.
2. Index excludes `ops/` from operational runbook conformance by default.
3. Retired evidence has owner/date/status metadata if preserved.
4. `bq-124-retro-verification.md` receives an explicit retirement or evidence target.

### §6.8 AC8 - Vulcan Lookup and Dispatch Patterns Updated

Evidence requirements:

1. Stable index URL/path is included in the appropriate lookup surface.
2. Agent prompts that currently name `aidotmarket/runbooks/<file>.md` are updated when files move.
3. Resource registry or equivalent points to `INDEX.md` or `runbook-index.json`.
4. A smoke test asks for a known runbook and resolves the service repo path.

### §6.9 AC9 - CRM Runbook Target Adjusted

Evidence requirements:

1. `BQ-CRM-RUNBOOK-STANDARD` body/spec target is backend `/docs/crm-system.md`.
2. Backend `/docs/crm-system.md` is indexed.
3. Deleted CRM central files have trace matrix coverage.
4. CRM references in backend specs are updated where active.

### §6.10 AC Counts Per Chunk

| Chunk | Core ACs | Index-specific ACs | Delete-safety ACs | Total evidence groups |
|---|---:|---:|---:|---:|
| Chunk 1 | AC2, AC4, AC5 partial | 5 | 0 | 8 |
| Chunk 2 | AC1, AC7 | 1 | 1 | 4 |
| Chunk 3 | AC1, AC3, AC5, AC6, AC8, AC9 | 2 | 6 | 14 |
| Chunk 4 | AC1, AC3, AC5, AC6, AC8 | 2 | 6 | 13 |
| Chunk 5 | AC1, AC2, AC4, AC6, AC7, AC8 | 5 | 3 | 14 |

### §6.11 Waiver Drift Audit

`BQ-RUNBOOK-STANDARD` must add a quarterly Council audit of waiver usage.

Ownership:

1. Vulcan initiates the audit at quarter close and opens the read-only `council_request` dispatch.
2. MP and AG execute the audit as read-only reviewers. MP owns conformance/index evidence; AG owns process, bypass, and operational-risk evidence.
3. Council ratifies the findings and decides whether follow-up BQ work is required.

Inputs:

1. Waiver count comes from CI logs, `runbook-index.json` rows with `waiver: true`, and PR titles or descriptions containing `[waiver]`.
2. Bypass evidence comes from searches across the runbooks meta-repo and configured service repos for runbook files that are outside the conformance gate, lint job, harness job, or manifest.
3. Drift indicators include quarter-over-quarter waiver count deltas, repeated waivers on the same runbook, nonconformant runbooks that persist across quarters, and service PRs that modify operational docs without runbook CI evidence.
4. Chunk 1 should add or schedule an indexer enhancement if `runbook-index.json` cannot yet record waiver state, waiver owner, waiver expiry, and last-audit quarter.

Output:

1. Each cycle writes a Living State decision entity named `decision:runbook-quarterly-audit-YYYY-QN`.
2. The decision records waiver count delta, bypass cases, repeated nonconformance, recommendations, and Council ratification status.
3. If drift requires action, Council files a follow-up BQ such as `BQ-RUNBOOK-DRIFT-REMEDIATION-YYYY-QN`.

Dead-man'''s switch (AG-N1 R3 nit):

1. The runbook-index meta-repo CI runs a scheduled job (cron or GitHub Actions schedule) on day Q+5 of each quarter (i.e. April 5, July 5, October 5, January 5) that asserts the existence of `decision:runbook-quarterly-audit-PRIOR-QN` in Living State.
2. If the prior-quarter audit decision entity is missing, the scheduled job fails CI loudly and emits a warning to the runbooks meta-repo issue tracker tagged `audit-overdue`. This makes silent-skip detectable instead of relying on someone noticing absence.
3. Vulcan SHOULD also dispatch the audit on Q+1 of each quarter as primary trigger, with the dead-man'''s switch as backstop.

## §7 Cross-Repo Index Design

### §7.1 Recommendation Summary

Use both static configuration and GitHub API discovery:

1. Static config in runbooks repo is authoritative for repo list and local fallback.
2. GitHub API discovery reads `/docs` contents and latest commits for configured repos.
3. A scheduled GitHub Action refreshes daily.
4. Service repo PR merges trigger `repository_dispatch` back to runbooks repo where available.
5. `runbook-index.json` is the canonical output. README dashboard and `INDEX.md` are generated views with hashes checked against the JSON.
6. Every refresh scans every configured repo; partial refresh is forbidden because it creates stale mixed snapshots and partial-update races.

### §7.2 Discovery Mechanism

`runbook-index.repos.yml`:

```yaml
repos:
  - id: ai-market-backend
    github: aidotmarket/ai-market-backend
    local_path: /Users/max/Projects/ai-market/ai-market-backend
    docs_globs:
      - docs/*.md
      - docs/runbooks/*.md
    required: true
  - id: ai-market-frontend
    github: aidotmarket/ai-market-frontend
    local_path: /Users/max/Projects/ai-market/ai-market-frontend
    docs_globs:
      - docs/*.md
    required: true
  - id: koskadeux-mcp
    github: aidotmarket/koskadeux-mcp
    local_path: /Users/max/koskadeux-mcp
    docs_globs:
      - docs/*.md
    required: true
  - id: aim-node
    github: aidotmarket/aim-node
    local_path: /Users/max/Projects/ai-market/aim-node
    docs_globs:
      - docs/*.md
    required: true
  - id: vectoraiz
    github: aidotmarket/vectoraiz
    local_path: /Users/max/Projects/vectoraiz/vectoraiz-monorepo
    docs_globs:
      - docs/*.md
    required: true
    path_decision: "Canonical local path replaces missing /Users/max/Projects/ai-market/vectoraiz per §10.1."
```

Discovery order:

1. If running in CI with GitHub token, query configured GitHub repos and branch `main`.
2. If GitHub query fails, use local clone paths when present.
3. If both fail for a required repo, emit an error row and nonzero exit in `--check`.
4. If repo exists but `/docs` is absent, emit `docs_status: MISSING` and fail AC3 until fixed.
5. Parse only files with `runbook: true` in frontmatter or files listed in `docs/runbook-manifest.yml` as `type: runbook`.
6. For GitHub API discovery, use conditional requests with ETag caching when a prior ETag exists.
7. Auth semantics: `GITHUB_TOKEN` only covers the current repository unless repository settings grant broader access; private service repos require a fine-grained PAT or GitHub App installation with `contents: read` for each configured repo.
8. A 403, 404, or rate-limit response for a required repo is fail-closed: the repo remains in `runbook-index.json` with `discovery_status: ERROR`, `docs_status: DISCOVERY_FAILED`, and a diagnostic reason.

### §7.3 Index Schema

Each row in `runbook-index.json`:

```yaml
id: crm-system
title: CRM System
owner_agent: CRM Steward
escalation_contact: Max
source_repo: aidotmarket/ai-market-backend
source_branch: main
source_path: docs/crm-system.md
source_commit: <sha>
local_path: /Users/max/Projects/ai-market/ai-market-backend/docs/crm-system.md
classification: service-runbook
system_name: crm
conformance_status: CONFORMANT|NON_CONFORMANT|LEGACY|RETIRED|ERROR
linter_version: <version or null>
last_lint_run: <date or null>
last_harness_date: <date or null>
last_harness_score: <float or null>
last_refreshed: <timestamp>
refresh_source: github-api|local-clone|manifest-only
staleness: current|stale|unknown
replacement_for:
  - aidotmarket/runbooks/crm-architecture.md
  - aidotmarket/runbooks/crm-pipeline.md
inbound_reference_status: clean|warnings|unknown
```

### §7.4 Output Target

Use `runbook-index.json` as canonical:

1. `runbook-index.json` is written first and is the only lookup artifact agents should consume.
2. `README.md` table is generated from `runbook-index.json` for the stable human entry point.
3. `INDEX.md` is generated from `runbook-index.json` for full detail.
4. `runbook-index refresh --check` verifies README and INDEX generated-block hashes match the canonical JSON.

Do not build a dashboard endpoint in this BQ. The JSON artifact is the future dashboard contract.

### §7.5 Refresh Trigger

Required triggers:

1. Daily cron on runbooks repo, recommended 06:10 UTC.
2. Manual `workflow_dispatch`.
3. `repository_dispatch` event from each service repo after PR merge when docs or manifest changes.
4. Workflow-level concurrency:

```yaml
concurrency:
  group: runbook-index-refresh
  cancel-in-progress: false
```

Fallback:

1. If service repos cannot emit repository_dispatch immediately, daily cron is sufficient for initial migration.
2. Generated output must show `last_refreshed` so stale index state is visible.
3. Refresh is idempotent: running it twice without source changes produces no diff.
4. Before committing generated output, the workflow pulls/rebases on `origin/main`; non-fast-forward push failures trigger a bounded retry that reruns the full all-repo scan before the next commit attempt.

### §7.6 Conformance Status Reporting

Conformance source precedence:

1. Runbook frontmatter `conformance.status` if present and schema-valid.
2. `docs/runbook-manifest.yml` row.
3. Latest local linter result generated during refresh.
4. `LEGACY` if file is indexed but not conformant and intentionally included.
5. `ERROR` if parse or discovery fails.

### §7.7 Shared GitHub Action Interface

The runbooks meta-repo publishes a reusable action:

```yaml
uses: aidotmarket/runbooks/.github/actions/runbook-ci@vX.Y.Z
with:
  runbook_globs: "docs/*.md docs/runbooks/*.md"
  manifest_path: "docs/runbook-manifest.yml"
  mode: "lint-and-harness"
```

Service repos consume the action pinned to a versioned tag such as `@v1.2.0` or to a full commit SHA. They do not pin `@main` in protected workflows and do not duplicate linter or harness scripts. Upgrade procedure: runbooks meta-repo publishes a release tag, service repos update the pinned ref in a docs/CI PR, CI runs lint and harness against the service manifest, and the generated index records the action version that produced conformance metadata.

## §8 Migration Sequencing

### §8.1 Required Order

1. Chunk 1: Foundation/index tooling.
2. Chunk 2: Cross-cutting classification manifest.
3. Chunk 3: Backend/CRM/Gmail/Celery first service migration.
4. Chunk 4: Frontend, Koskadeux, AIM Node, vectoraiz migrations.
5. Chunk 5: Cleanup and final meta-repo state.

Chunk 1 must land before Chunks 3 and 4. Chunk 5 must be last.

### §8.2 Gate 2 Breakdown

Gate 2 should convert this design into implementation specs:

1. Gate 2A: Index tooling implementation plan.
2. Gate 2B: Classification manifest and central retained topics.
3. Gate 2C: Backend migration plan with trace matrices.
4. Gate 2D: Remaining services migration plan.
5. Gate 2E: Cleanup and origin-main verification plan.

### §8.3 Chunk 3 Preflight

Before backend migration:

1. Confirm backend `docs/` target files and CODEOWNERS.
2. Run inbound reference scan.
3. Update `BQ-CRM-RUNBOOK-STANDARD` target path.
4. Decide Gmail split boundary.
5. Produce trace matrix for CRM/briefing/Gmail files.
6. Run generated index against branch before deletion.

### §8.4 Chunk 4 Preflight

Before remaining migrations:

1. Create frontend `/docs`.
2. Resolve vectoraiz canonical repo path.
3. Apply §10.2 Koskadeux operations target or record an explicit Gate 2 override.
4. Audit Koskadeux specs that hardcode `aidotmarket/runbooks/model-configuration.md`.
5. Confirm aim-node standard G4 constraints do not forbid reading migrated AIM Node content during standard falsifiability flows.

### §8.5 Rollback

1. Chunk 1 rollback removes generated index tooling and restores README from git.
2. Chunk 2 rollback removes the manifest; no content deleted.
3. Chunk 3 rollback restores deleted central files from the prior commit and removes index replacement rows.
4. Chunk 4 rollback restores deleted central files for the affected service only.
5. Chunk 5 rollback restores any mistakenly deleted central files and reruns index refresh.

### §8.6 Waiver Abuse Mitigation

After decentralization lands, Council reviews waiver usage quarterly under `BQ-RUNBOOK-STANDARD`. Vulcan opens the audit dispatch; MP and AG execute read-only checks against CI logs, `runbook-index.json`, PR metadata, runbooks meta-repo contents, and configured service repos; Council ratifies the result.

The expected output is a `decision:runbook-quarterly-audit-YYYY-QN` Living State entity with:

1. Current waiver count and quarter-over-quarter delta.
2. Runbooks still outside conformance and whether each has an owner, expiry, and impact-gate waiver.
3. Bypass cases where operational runbook files exist outside manifest, lint, harness, or PR-time impact-gate coverage.
4. Recommendation: no drift observed, re-tighten waiver syntax/expiry/ownership, add or strengthen tests, or file `BQ-RUNBOOK-DRIFT-REMEDIATION-YYYY-QN`.

## §9 Test Plan

### §9.1 Chunk 1 Tests

1. `test_index_schema_accepts_required_fields`
2. `test_index_schema_rejects_missing_source_repo`
3. `test_discovery_reads_static_config`
4. `test_discovery_uses_local_clone_when_github_unavailable`
5. `test_discovery_reports_missing_docs_dir`
6. `test_frontmatter_runbook_true_includes_file`
7. `test_manifest_type_runbook_includes_file`
8. `test_ops_evidence_excluded_by_default`
9. `test_readme_generated_block_check_fails_when_stale`
10. `test_index_json_matches_index_md_rows`
11. Integration: scan at least backend, koskadeux, and aim-node local repos and produce rows.

### §9.2 Chunk 2 Tests

1. `test_migration_manifest_covers_all_root_runbooks`
2. `test_migration_manifest_has_unique_source_paths`
3. `test_migration_manifest_service_targets_under_docs`
4. `test_migration_manifest_central_rows_have_rationale`
5. `test_migration_manifest_retired_rows_have_disposition`
6. README policy grep for central retained topics.

### §9.3 Chunk 3 Tests

1. Lint all backend migrated runbooks.
2. Harness all backend conformant runbooks with scenario sets.
3. CRM trace matrix completeness test.
4. Reference scan for `crm-architecture.md`, `crm-pipeline.md`, `crm-target-state.md`, `morning-briefing.md`, and `gmail-drop-pipeline.md`.
5. Index includes backend `/docs/crm-system.md`.
6. Index includes central `gmail-oauth-watch.md`.
7. CODEOWNERS covers backend docs.
8. `BQ-CRM-RUNBOOK-STANDARD` target path check.

### §9.4 Chunk 4 Tests

1. Frontend `/docs` existence and lint.
2. Koskadeux target docs lint/harness.
3. AIM Node target docs lint/harness.
4. vectoraiz target docs lint/harness after path confirmation.
5. Reference scan for `agent-dispatch.md`, `council-gate-process.md`, `council-hall-deliberation.md`, `session-lifecycle.md`, `mcp-gateway.md`, `aim-node.md`, `aim-node-release-process.md`, `aim-data-release-process.md`, `vz-release-process.md`, `docker-testing.md`, and `dual-brand-vectoraiz-aim-channel.md`.
6. Generated index lists all service repos.

### §9.5 Chunk 5 Tests

1. `runbook-index refresh --check`
2. `runbook-lint` absolute path smoke test against one service runbook.
3. `runbook-harness` absolute path smoke test against one service runbook.
4. `rg` stale central path scan.
5. README dashboard generated and current.
6. `INDEX.md` generated and current.
7. `runbook-index.json` schema-valid.
8. Origin-main verification after push.

### §9.6 Integration Test: Three Service Repos

The minimum integration test fixture must create or scan runbooks from three distinct repos:

1. `ai-market-backend/docs/crm-system.md`
2. `koskadeux-mcp/docs/koskadeux-operations.md` or approved equivalent
3. `aim-node/docs/aim-node-system.md`

Pass criteria:

1. All three rows appear in `runbook-index.json`.
2. All three rows appear in `INDEX.md`.
3. README summary shows three service repos with non-error status.
4. One row can be `NON_CONFORMANT` during migration, but status must be explicit.

## §10 Council Decisions

R2 closes the Gate 1 open questions as explicit Council-decision rows. Gate 2 may revise a row only by recording a new Council decision with replacement rationale; it must not treat any row below as unresolved.

### §10.1 Service Repos Hosting `/docs`

Decision: use these hosts:

1. `/Users/max/Projects/ai-market/ai-market-backend`
2. `/Users/max/Projects/ai-market/ai-market-frontend`
3. `/Users/max/koskadeux-mcp`
4. `/Users/max/Projects/ai-market/aim-node`
5. `/Users/max/Projects/vectoraiz/vectoraiz-monorepo`
6. `/Users/max/Projects/runbooks` as meta-repo only

Rationale: all except the originally requested vectoraiz path were verified locally. Council adopts `aidotmarket/vectoraiz` as the canonical GitHub repo, maps it to `/Users/max/Projects/vectoraiz/vectoraiz-monorepo`, and assigns `/docs` ownership to the vectoraiz service owner plus release owner. The absent `/Users/max/Projects/ai-market/vectoraiz` path is not part of this BQ.

### §10.2 Cross-Cutting Keep-Central List

Decision: retain these central candidates unless Gate 2 records a narrower owner:

1. `gcp-auth`
2. `infisical`
3. `gmail-oauth-watch`
4. `koskadeux-operations`
5. `rtk-token-optimization`
6. `vulcan-configuration`

If Koskadeux operations or Vulcan configuration become code-local, the target is `koskadeux-mcp/docs/...`, and runbooks repo only indexes it. Do not maintain central and service copies as independent SSOTs.

### §10.3 Index Format

Decision: `runbook-index.json` is canonical; README table and dedicated `INDEX.md` are generated from it.

Rationale: README is the stable human entry point; `INDEX.md` can hold more detail without bloating README; JSON serves agents and future dashboards. A live dashboard endpoint is deferred.

### §10.4 Lint and Harness CI Integration

Decision: shared GitHub Action published from runbooks meta-repo and consumed in each service repo, pinned to versioned tag or full SHA.

Rationale: duplicated config would diverge immediately across five repos. The meta-repo owns linter/harness release behavior; service repos own manifests, runbook content, and CODEOWNERS.

### §10.5 CODEOWNERS Implications

Decision: every service repo that receives runbooks must add CODEOWNERS entries for the moved docs.

Required process:

1. Target repo adds ownership for `/docs/*.md` and `/docs/runbook-manifest.yml`.
2. Owner must include service owner plus runbook owner agent or human maintainer.
3. Waivers from `BQ-RUNBOOK-IMPACT-GATE` require owner approval.
4. Central cross-cutting docs retain CODEOWNERS in runbooks meta-repo.

### §10.6 Bus Factor and Discoverability

Decision: mitigate fragmentation with a stable generated index path and agent lookup artifact:

1. `aidotmarket/runbooks/README.md` is the stable entry.
2. `aidotmarket/runbooks/INDEX.md` is the full human index.
3. `aidotmarket/runbooks/runbook-index.json` is the canonical agent lookup artifact.
4. Daily refresh and service merge dispatch prevent stale index state.
5. Deleted central files are not replaced with long-lived duplicate tombstones; the generated index carries replacements.

Rationale: decentralized docs without an index would reproduce AG's fragmentation risk at [/Users/max/.gemini/tmp/runbooks/runbook-audit-ag-2026-04-25.md:64](/Users/max/.gemini/tmp/runbooks/runbook-audit-ag-2026-04-25.md:64). The index is therefore a prerequisite, not a polish item.

## §11 Inbound-Reference Inventory

This inventory is non-exhaustive at Gate 1 by design. Migration chunks in Gate 2 and Gate 3 MUST run a fresh, complete `grep -rn '/Users/max/Projects/runbooks/'` and `rg 'aidotmarket/runbooks'` scan at migration time. Automated scan is a non-negotiable precondition for each migration PR.

### §11.1 Search Scope and Patterns

Search scope used for this Gate 1 draft:

1. `/Users/max/Projects/runbooks`
2. `/Users/max/Projects/ai-market/ai-market-backend`
3. `/Users/max/Projects/ai-market/ai-market-frontend`
4. `/Users/max/koskadeux-mcp`
5. `/Users/max/Projects/ai-market/aim-node`
6. `/Users/max/Projects/ai-market/vectoraiz` when present; it was absent
7. `/Users/max/Projects/vectoraiz`

Patterns:

1. `/Users/max/Projects/runbooks/`
2. `/Users/max/Projects/runbooks`
3. `runbooks/<filename>.md`
4. `aidotmarket/runbooks/<filename>.md`

Generated chats, logs, `node_modules`, `.git`, build outputs, and minified files are excluded from the active inventory. They may contain historical references but are not migration blockers unless consumed by a live prompt or config.

### §11.2 Active References in Runbooks Repo

| Reference | Location | Target | Migration handling |
|---|---|---|---|
| `aidotmarket/runbooks/vulcan-configuration.md` | [vulcan-configuration.md](/Users/max/Projects/runbooks/vulcan-configuration.md:118) | self | If moved in Chunk 4, update self-reference in same PR. If retained central policy, update wording to meta-repo central policy. |
| `/Users/max/Projects/runbooks/*.md` weekly sweep | [specs/BQ-AUTONOMOUS-OPERATIONS.md](/Users/max/Projects/runbooks/specs/BQ-AUTONOMOUS-OPERATIONS.md:77) | central root runbooks | Chunk 5 update to generated index and service repo scan. |
| `/Users/max/Projects/runbooks/operating-guide.md` | [specs/BQ-AUTONOMOUS-OPERATIONS.md](/Users/max/Projects/runbooks/specs/BQ-AUTONOMOUS-OPERATIONS.md:713) | future central runbook | Chunk 5 decide if this remains central or becomes service-local. |
| `runbook-lint` across `/Users/max/Projects/runbooks` | [specs/BQ-AUTONOMOUS-OPERATIONS.md](/Users/max/Projects/runbooks/specs/BQ-AUTONOMOUS-OPERATIONS.md:752) | central sweep | Chunk 5 update to index-driven multi-repo sweep. |
| `aidotmarket/runbooks/aim-node.md` | [specs/BQ-RUNBOOK-STANDARD.md](/Users/max/Projects/runbooks/specs/BQ-RUNBOOK-STANDARD.md:404) | AIM Node G4 target | Chunk 4 must reconcile with BQ-RUNBOOK-STANDARD frozen isolation requirements before moving. |
| `aidotmarket/runbooks/README.md` index | [specs/BQ-RUNBOOK-STANDARD.md](/Users/max/Projects/runbooks/specs/BQ-RUNBOOK-STANDARD.md:526) | central index | Chunk 1 preserves this as generated meta index. |

### §11.3 Source-File Deletion Inventory

For each migrated or deleted source file, the migration PR must run `C1(FILE)`: `rg -n 'FILE|aidotmarket/runbooks/FILE|/Users/max/Projects/runbooks/FILE' /Users/max/Projects/runbooks /Users/max/Projects/ai-market/ai-market-backend /Users/max/Projects/ai-market/ai-market-frontend /Users/max/koskadeux-mcp /Users/max/Projects/ai-market/aim-node /Users/max/Projects/vectoraiz --glob '!**/.git/**' --glob '!**/node_modules/**'`. Deletion is allowed only when `C1(FILE)` has zero live hits outside the source file, generated index, migration manifest, and explicitly classified historical specs.

| Source file | Target/classification | Gate 1 evidence and live/historical classification |
|---|---|---|
| `ai-market-backend.md` | backend `/docs/backend-platform.md`; `service-move` | `C1(ai-market-backend.md)` currently finds historical standard specs and this design; migration requires zero live service refs. |
| `crm-architecture.md` | backend `/docs/crm-system.md`; `service-merge` | R3 scan command: `rg -n 'crm-architecture' /Users/max/Projects/ai-market/ai-market-backend /Users/max/koskadeux-mcp /Users/max/Projects/runbooks --glob '!**/.git/**' --glob '!**/node_modules/**'`. Counts: backend 2, Koskadeux 0, runbooks 11. Live refs: backend `bq-crm-user-scoping-backfill-and-fallback-gate1.md` anchors and runbooks `crm-pipeline.md`; historical/self refs: this design and CRM S500 changelog. Update live refs to backend `/docs/crm-system.md` before deleting. |
| `crm-pipeline.md` | backend `/docs/crm-system.md`; `service-merge` | R3 scan command: `rg -n 'crm-pipeline' /Users/max/Projects/ai-market/ai-market-backend /Users/max/koskadeux-mcp /Users/max/Projects/runbooks --glob '!**/.git/**' --glob '!**/node_modules/**'`. Counts: backend 1, Koskadeux 0, runbooks 6. Live refs: backend `bq-crm-user-scoping-backfill-and-fallback-gate1.md:999`; historical/self refs: CRM S500 changelog and this design. Update active backend spec or mark frozen before deletion. |
| `crm-target-state.md` | backend `/docs/crm-system.md`; `service-merge` | R3 scan command: `rg -n 'crm-target-state' /Users/max/Projects/ai-market/ai-market-backend /Users/max/koskadeux-mcp /Users/max/Projects/runbooks --glob '!**/.git/**' --glob '!**/node_modules/**'`. Counts: backend 8, Koskadeux 0, runbooks 19. Live refs: backend CRM coverage, integration-contracts, and user-scoping specs; runbooks `crm-pipeline.md` and `crm-architecture.md`. Historical refs: standard retrofit specs and this design. Chunk 3 must redirect live refs to `/docs/crm-system.md` and classify frozen specs. |
| `morning-briefing.md` | backend `/docs/crm-system.md`; `service-merge` | Current live intra-runbooks reference in `crm-architecture.md`; update before deleting. |
| `gmail-drop-pipeline.md` | central `gmail-oauth-watch.md` plus backend CRM refs; `service-merge`/central split | R3 scan command: `rg -n 'gmail-drop-pipeline' /Users/max/Projects/ai-market/ai-market-backend /Users/max/koskadeux-mcp /Users/max/Projects/runbooks --glob '!**/.git/**' --glob '!**/node_modules/**'`. Counts: backend 0, Koskadeux 0, runbooks 4. Live refs: `crm-architecture.md:140` references the flow. Historical/self refs: this design. Split OAuth/watch content into central `gmail-oauth-watch.md`, move service behavior into backend `/docs/crm-system.md`, then update the CRM architecture reference. |
| `email-drafting.md` | backend `/docs/crm-system.md` or `/docs/email-system.md`; `service-merge` | `C1(email-drafting.md)` must prove zero live refs; no known service hit in Gate 1 scan. |
| `celery-infrastructure-deployment.md` | backend `/docs/celery-infrastructure.md`; `service-move` | R3 scan command: `rg -n 'celery-infrastructure-deployment' /Users/max/Projects/ai-market/ai-market-backend /Users/max/koskadeux-mcp /Users/max/Projects/runbooks --glob '!**/.git/**' --glob '!**/node_modules/**'`. Counts: backend 5, Koskadeux 0, runbooks 4. Live refs: backend `BQ-CELERY-INFRASTRUCTURE-DEPLOYMENT-GATE2.md` points at `docs/runbooks/celery-infrastructure-deployment.md`; runbooks `BQ-AUTONOMOUS-OPERATIONS.md` cites verification status. Historical refs: standard retrofit note and this design. Normalize active backend refs to `/docs/celery-infrastructure.md` or explicitly support `docs/runbooks/` before deletion. |
| `bq-124-retro-verification.md` | `ops/` evidence or backend Celery appendix; `retire-or-evidence` | R3 scan command: `rg -n 'bq-124-retro-verification' /Users/max/Projects/ai-market/ai-market-backend /Users/max/koskadeux-mcp /Users/max/Projects/runbooks --glob '!**/.git/**' --glob '!**/node_modules/**'`. Counts: backend 0, Koskadeux 0, runbooks 5. Live refs: none outside this design. Historical/design refs: this design records retirement. Decision: retire as standing runbook and preserve only dated evidence if useful. |
| `seo-infrastructure.md` | backend `/docs/seo-discovery.md`; `service-merge` | `C1(seo-infrastructure.md)` must prove zero live refs; no known service hit in Gate 1 scan. |
| `seo-seller-validation.md` | backend or frontend SEO docs; `service-merge` | `C1(seo-seller-validation.md)` must prove zero live refs after ownership decision. |
| `aimarket-mcp-server.md` | backend `/docs/marketplace-mcp-public.md`; `service-move` | `C1(aimarket-mcp-server.md)` must prove zero live refs; no known service hit in Gate 1 scan. |
| `allai-agents.md` | backend platform/CRM docs; `service-merge` | `C1(allai-agents.md)` must prove zero live refs; no known service hit in Gate 1 scan. |
| `marketing-tab.md` | backend or frontend marketing docs; `service-merge` | `C1(marketing-tab.md)` must prove zero live refs after ownership decision. |
| `ops-ai-market.md` | backend docs or central policy; `service-merge` or `central-cross-cutting` | `C1(ops-ai-market.md)` currently finds `BQ-AUTONOMOUS-OPERATIONS`; classify that spec as live or historical before deletion. |
| `meet-records-pipeline.md` | backend `/docs/meet-records-pipeline.md`; `service-move` | Live hit found at `/Users/max/Projects/ai-market/ai-market-backend/specs/BQ-MEET-RECORDS-CRM.md:181`; update or mark historical. |
| `agent-dispatch.md` | central `koskadeux-operations.md` or `koskadeux-mcp/docs`; `service-merge`/central | Live Koskadeux model-configuration refs found; update before deleting or retaining under new central target. |
| `council-gate-process.md` | Koskadeux operations target; `service-merge` | `C1(council-gate-process.md)` must prove zero live refs outside historical specs. |
| `council-hall-deliberation.md` | Koskadeux operations target; `service-merge` | `C1(council-hall-deliberation.md)` must prove zero live refs outside historical specs. |
| `session-lifecycle.md` | Koskadeux operations target; `service-merge` | Current live intra-runbooks reference from `mcp-gateway.md` must be updated with target path. |
| `mcp-gateway.md` | `koskadeux-mcp/docs/koskadeux-mcp-internal.md` or central; `service-move`/central | Current live intra-runbooks reference from `session-lifecycle.md` must be updated with target path. |
| `rtk-token-optimization.md` | central policy candidate; `central-cross-cutting` | `C1(rtk-token-optimization.md)` must prove no service-local owner before retaining central or moving. |
| `vulcan-configuration.md` | central policy candidate; `central-cross-cutting` | Live self-ref and Koskadeux refs found; update if renamed or moved. |
| `aim-node.md` | aim-node `/docs/aim-node-system.md`; `service-move` | Historical G4/standard specs contain many hits; classify frozen standard refs before deletion. |
| `aim-node-release-process.md` | aim-node release docs; `service-merge` | Current intra-runbooks release cross-links must be updated to new release docs. |
| `aim-data-release-process.md` | aim-node or vectoraiz release docs; `service-merge` | Current intra-runbooks release cross-links must be updated after ownership decision. |
| `vz-release-process.md` | vectoraiz `/docs/releasing.md`; `service-move` | Current release cross-links from AIM files must be updated. |
| `docker-testing.md` | aim-node or vectoraiz release docs; `service-merge` | Current release cross-links must be updated after ownership decision. |
| `cloudflare-worker.md` | backend/aim-node/vectoraiz split or central; `service-merge` | Current release cross-links from AIM files must be updated. |
| `dual-brand-vectoraiz-aim-channel.md` | vectoraiz `/docs/dual-brand-channel.md`; `service-move` | `C1(dual-brand-vectoraiz-aim-channel.md)` must prove zero live refs after vectoraiz mapping. |
| `ai-market-frontend.md` | frontend `/docs/frontend-marketplace.md`; `service-move` | R3 scan command: `rg -n 'ai-market-frontend' /Users/max/Projects/ai-market/ai-market-backend /Users/max/koskadeux-mcp /Users/max/Projects/runbooks --glob '!**/.git/**' --glob '!**/node_modules/**'`. Counts: backend 28, Koskadeux 19, runbooks 17. Live refs are mostly repo/service-name references in backend docs, tests, monitors, config, and Koskadeux specs/runbooks/tooling, not direct source-file links; direct source refs are runbooks `ai-market-frontend.md` self/header and this design. Chunk 4 preflight must rerun `C1(ai-market-frontend.md)` and update any direct source-file refs before deletion; repo-name inventory refs are non-blocking if they do not point to the deleted central file. |

### §11.4 Active References in Backend Repo

| Reference | Location | Target | Migration handling |
|---|---|---|---|
| `/Users/max/Projects/ai-market/runbooks/crm-target-state.md` | `/Users/max/Projects/ai-market/ai-market-backend/specs/BQ-CRM-AGENT-COVERAGE-GATE1.md:109` | likely stale CRM target | Chunk 3 update to backend `/docs/crm-system.md` if active; mark historical if frozen. |
| `/Users/max/Projects/runbooks/crm-target-state.md` | `/Users/max/Projects/ai-market/ai-market-backend/specs/BQ-CRM-INTEGRATION-CONTRACTS-GATE1.md:413` | CRM target-state | Chunk 3 update or mark historical. |
| `/Users/max/Projects/runbooks/crm-target-state.md` | `/Users/max/Projects/ai-market/ai-market-backend/specs/bq-crm-user-scoping-backfill-and-fallback-gate1.md:997` | CRM target-state | Chunk 3 update or mark historical. |
| `/Users/max/Projects/runbooks/crm-architecture.md` | `/Users/max/Projects/ai-market/ai-market-backend/specs/bq-crm-user-scoping-backfill-and-fallback-gate1.md:998` | CRM architecture | Chunk 3 update to `/docs/crm-system.md` or mark historical. |
| `/Users/max/Projects/runbooks/crm-pipeline.md` | `/Users/max/Projects/ai-market/ai-market-backend/specs/bq-crm-user-scoping-backfill-and-fallback-gate1.md:999` | CRM pipeline | Chunk 3 update to `/docs/crm-system.md` or mark historical. |
| `docs/runbooks/celery-infrastructure-deployment.md` | `/Users/max/Projects/ai-market/ai-market-backend/specs/BQ-CELERY-INFRASTRUCTURE-DEPLOYMENT-GATE2.md:17` | backend-local docs/runbooks | Chunk 3 normalize to `/docs/celery-infrastructure.md` or explicitly support `docs/runbooks/`. |
| `docs/runbooks/sysadmin_railway_env_recovery.md` | `/Users/max/Projects/ai-market/ai-market-backend/specs/BQ-SYSADMIN-INFRA-ACCESS-GATE2.md:62` | backend-local docs/runbooks | Not a central runbooks reference; index policy must decide whether to include `docs/runbooks/*.md`. |
| `../runbooks/backup-restore-drill.md` | `/Users/max/Projects/ai-market/ai-market-backend/docs/recovery/DR-PLAN.md:258` | backend-local docs/runbooks | Not central; include in backend manifest if operational. |
| `koskadeux-mcp/runbooks/activation-verification.md` | `/Users/max/Projects/ai-market/ai-market-backend/docs/core/PROTOCOLS.md:183` and related lines | koskadeux runbook path | Chunk 4 update if activation verification moves under `/docs`. |
| `aidotmarket/runbooks` | `/Users/max/Projects/ai-market/ai-market-backend/docs/core/CORE.md:183` | central repo as operational procedure source | Chunk 1/5 update to generated README/INDEX as meta entry, not flat service-runbook SSOT. |
| `meet-records-pipeline.md` | `/Users/max/Projects/ai-market/ai-market-backend/specs/BQ-MEET-RECORDS-CRM.md:181` | central meet-records draft | Chunk 3 update to backend `/docs/meet-records-pipeline.md` or mark spec historical. |
| `recovery_runbook: docs/runbooks/sysadmin_railway_env_recovery.md` | `/Users/max/Projects/ai-market/ai-market-backend/app/agents/sysadmin/skills/railway_ops.py:292` | backend-local runbook | Not central; include in backend manifest or update if normalized. |

### §11.5 Active References in Koskadeux Repo

| Reference | Location | Target | Migration handling |
|---|---|---|---|
| `aidotmarket/runbooks/model-configuration.md` | `/Users/max/koskadeux-mcp/specs/BQ-MODEL-CONFIGURATION-RUNBOOK-gate1.md:13` and many Gate 2 chunk specs | model configuration runbook | Many live refs exist across Gate 1/Gate 2 chunk specs; Chunk 4 must decide central vs `koskadeux-mcp/docs/model-configuration.md` and update active specs/prompts accordingly. |
| `aidotmarket/runbooks/agent-dispatch.md` | `/Users/max/koskadeux-mcp/specs/BQ-MODEL-CONFIGURATION-RUNBOOK-gate1.md:66` | agent dispatch | Chunk 4 update to `koskadeux-operations` target. |
| `aidotmarket/runbooks/vulcan-configuration.md` | `/Users/max/koskadeux-mcp/specs/BQ-MODEL-CONFIGURATION-RUNBOOK-gate1.md:75` | Vulcan configuration | Chunk 4 update based on central/service decision. |
| `koskadeux-mcp/runbooks/activation-verification.md` | `/Users/max/koskadeux-mcp/specs/BQ-DEPLOY-ACTIVATION-VERIFICATION/GATE2.md:27` | activation verification | Chunk 4 update if `/docs` becomes canonical. |
| `/Users/max/Projects/runbooks/specs/BQ-RUNBOOK-STANDARD.md` | `/Users/max/koskadeux-mcp/specs/BQ-KOSKADEUX-G4-PROTOCOL-GATE1.md:416` through `:429` | frozen parent standard citations | Do not update unless those specs are reopened; these cite frozen standard lines. |

### §11.6 Frontend, AIM Node, vectoraiz

No active references to `/Users/max/Projects/runbooks/` or `aidotmarket/runbooks/*.md` were found in:

1. `/Users/max/Projects/ai-market/ai-market-frontend`
2. `/Users/max/Projects/ai-market/aim-node`
3. `/Users/max/Projects/vectoraiz`

This is a Gate 1 search result, not a permanent guarantee. Each migration chunk must rerun the scan from the target repo before deleting source files.

### §11.7 Living State and Prompt References

Known Living State references from `build:bq-runbook-decentralization`:

1. `BQ-CRM-RUNBOOK-STANDARD` currently needs a target adjustment to backend `/docs/crm-system.md`.
2. `BQ-RUNBOOK-STANDARD` continues unchanged but its preview migration plan names central runbook targets.
3. `decision:runbook-architecture-decentralization` records Option B and should remain as the architectural decision record.

Migration requirement:

1. Chunk 3 updates Living State references for CRM and briefing targets.
2. Chunk 4 updates Living State references for Koskadeux/AIM/vectoraiz runbook targets.
3. Chunk 5 updates any global resource registry or lookup prompt to point to `INDEX.md` or `runbook-index.json`.

### §11.8 Reference Update Policy

Every reference row gets one of these statuses during migration:

1. `updated`: changed to new target path.
2. `historical`: left unchanged because it cites a frozen historical spec or commit.
3. `central-retained`: left unchanged because target remains central.
4. `normalized`: changed from service-local `docs/runbooks` to service `/docs` target.
5. `blocked`: requires a recorded replacement path or owner decision before deletion.

Deletion of a central source file is blocked while any live reference row is `blocked`.

## §12 Final Gate 1 Recommendation

Approve Option B with strict sequencing:

1. Build index first.
2. Classify every existing file second.
3. Migrate backend/CRM/Gmail/Celery before lower-risk services.
4. Delete central files only after trace matrix, reference rewrites, index generation, lint, harness, and CODEOWNERS evidence exist.
5. Keep central cross-cutting SSOT docs only where central ownership prevents copying drift.

The design accepts AG's architecture while preserving MP's concrete cluster audit. The main tradeoff is higher upfront CI and indexing work, but it directly addresses the root cause: service docs must be versioned and reviewed with the service code they describe.
