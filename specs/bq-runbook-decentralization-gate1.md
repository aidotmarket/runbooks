# BQ-RUNBOOK-DECENTRALIZATION Gate 1 Design Spec

## §0 Header

| Field | Value |
|---|---|
| BQ code | `BQ-RUNBOOK-DECENTRALIZATION` |
| Status | Gate 1 R1 design spec |
| Target repo | `aidotmarket/runbooks` |
| Local repo | `/Users/max/Projects/runbooks` |
| Repo HEAD at authoring | `5937a52424a2f0cd9f5ef186b3a0052792acf887` |
| Branch | `main` |
| Authored date | 2026-04-25 |
| Authoring session | S505 |
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
| runbooks meta-repo | `/Users/max/Projects/runbooks` | `5937a52` | n/a | Remains standard, linter, harness, generated index, central cross-cutting runbooks, and dated evidence. |

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
  koskadeux-operations.md central cross-cutting SSOT, if Council confirms
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

The generated index reads service repo manifests and runbook frontmatter, then writes:

1. A concise dashboard table in `README.md`.
2. A full `INDEX.md` with one row per indexed runbook, stale-reference warnings, conformance status, and source repo path.
3. A machine-readable `runbook-index.json` artifact for Vulcan lookup and future dashboards.

### §4.5 Central Retained Topics

This Gate 1 recommends retaining these central cross-cutting topics:

| Topic | Central target | Rationale |
|---|---|---|
| GCP auth | `gcp-auth.md` or `gcp-auth.md` retrofit target | Shared OAuth/GCP setup is not owned by one service. |
| Infisical | `infisical.md` eventual target, replacing `infisical-secrets.md` per existing standard chunk intent | Secret lifecycle and emergency recovery span service repos. |
| Gmail OAuth/watch | `gmail-oauth-watch.md` | Gmail watch and OAuth token handling are shared infrastructure; service runbooks reference it. |
| Koskadeux operations | `koskadeux-operations.md` if Council confirms | Council/dispatch/session operation is cross-agent infrastructure; however, code-local subprocedures may still live in `koskadeux-mcp/docs`. |

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
2. GitHub token or local clone access for service repos.
3. `BQ-RUNBOOK-IMPACT-GATE` for later PR-time enforcement, not for Chunk 1 index generation.
4. Service repo list confirmed or corrected by Council, especially vectoraiz path.

### §5.1.6 Test/Verification Strategy

1. Unit test schema validation for index rows.
2. Unit test frontmatter extraction from conformant runbook fixture.
3. Unit test manifest override when frontmatter is missing.
4. Unit test evidence exclusion: `ops/*.md` is not treated as operational runbook.
5. Integration test scans at least three local service repos and produces rows.
6. `runbook-index refresh --check` fails if generated files are stale.
7. `git diff --check` passes.

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
| [agent-dispatch.md](/Users/max/Projects/runbooks/agent-dispatch.md:1) and Council files | central `koskadeux-operations.md` or `koskadeux-mcp/docs` | Council decision required. |

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
3. Max/Council confirmation of central keep-list.

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
3. Council resolves whether `koskadeux-operations` is central or service-local.
4. Council resolves vectoraiz canonical repo path.
5. Frontend `/docs` directory is created.

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
3. `runbook-lint` can run against service repo paths from the runbooks repo CLI.
4. `runbook-harness` can run against service repo paths from the runbooks repo CLI.
5. README and INDEX generated block hashes match `runbook-index.json`.

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
6. Missing `/Users/max/Projects/ai-market/vectoraiz` is not silently ignored; Council must confirm replacement path or create the requested path.

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

## §7 Cross-Repo Index Design

### §7.1 Recommendation Summary

Use both static configuration and GitHub API discovery:

1. Static config in runbooks repo is authoritative for repo list and local fallback.
2. GitHub API discovery reads `/docs` contents and latest commits for configured repos.
3. A scheduled GitHub Action refreshes daily.
4. Service repo PR merges trigger `repository_dispatch` back to runbooks repo where available.
5. Output goes to both README dashboard and dedicated `INDEX.md`, plus `runbook-index.json`.

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
    open_question: "Confirm replacement for missing /Users/max/Projects/ai-market/vectoraiz."
```

Discovery order:

1. If running in CI with GitHub token, query configured GitHub repos and branch `main`.
2. If GitHub query fails, use local clone paths when present.
3. If both fail for a required repo, emit an error row and nonzero exit in `--check`.
4. If repo exists but `/docs` is absent, emit `docs_status: MISSING` and fail AC3 until fixed.
5. Parse only files with `runbook: true` in frontmatter or files listed in `docs/runbook-manifest.yml` as `type: runbook`.

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

Use both:

1. `README.md` table for stable human entry point.
2. `INDEX.md` for full detail.
3. `runbook-index.json` for agents and future dashboard endpoint.

Do not build a dashboard endpoint in this BQ. The JSON artifact is the future dashboard contract.

### §7.5 Refresh Trigger

Required triggers:

1. Daily cron on runbooks repo, recommended 06:10 UTC.
2. Manual `workflow_dispatch`.
3. `repository_dispatch` event from each service repo after PR merge when docs or manifest changes.

Fallback:

1. If service repos cannot emit repository_dispatch immediately, daily cron is sufficient for initial migration.
2. Generated output must show `last_refreshed` so stale index state is visible.

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
uses: aidotmarket/runbooks/.github/actions/runbook-ci@main
with:
  runbook_globs: "docs/*.md docs/runbooks/*.md"
  manifest_path: "docs/runbook-manifest.yml"
  mode: "lint-and-harness"
```

Service repos consume the action. They do not duplicate linter or harness scripts. This keeps CI behavior consistent and lets the meta-repo remain the tooling owner.

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
3. Decide central vs service-local Koskadeux operations.
4. Audit Koskadeux specs that hardcode `aidotmarket/runbooks/model-configuration.md`.
5. Confirm aim-node standard G4 constraints do not forbid reading migrated AIM Node content during standard falsifiability flows.

### §8.5 Rollback

1. Chunk 1 rollback removes generated index tooling and restores README from git.
2. Chunk 2 rollback removes the manifest; no content deleted.
3. Chunk 3 rollback restores deleted central files from the prior commit and removes index replacement rows.
4. Chunk 4 rollback restores deleted central files for the affected service only.
5. Chunk 5 rollback restores any mistakenly deleted central files and reruns index refresh.

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

## §10 Open Questions for Council

### §10.1 Q1 - Which Service Repos Host `/docs`?

Recommendation: use these hosts:

1. `/Users/max/Projects/ai-market/ai-market-backend`
2. `/Users/max/Projects/ai-market/ai-market-frontend`
3. `/Users/max/koskadeux-mcp`
4. `/Users/max/Projects/ai-market/aim-node`
5. `/Users/max/Projects/vectoraiz/vectoraiz-monorepo`, pending Council confirmation
6. `/Users/max/Projects/runbooks` as meta-repo only

Rationale: all except the requested vectoraiz path were verified locally. The requested `/Users/max/Projects/ai-market/vectoraiz` path is absent; `/Users/max/Projects/vectoraiz/vectoraiz-monorepo` exists and has `/docs`.

### §10.2 Q2 - Cross-Cutting Keep-Central List

Recommendation: confirm central retention for:

1. `gcp-auth`
2. `infisical`
3. `gmail-oauth-watch`
4. `koskadeux-operations`, with one caveat

Caveat: if Council decides Koskadeux operations are code-local rather than cross-cutting, the target should be `koskadeux-mcp/docs/koskadeux-operations.md`, and runbooks repo should only index it. Do not maintain both as independent copies.

### §10.3 Q3 - Index Format

Recommendation: both README table and dedicated `INDEX.md`, plus `runbook-index.json`.

Rationale: README is the stable human entry point; `INDEX.md` can hold more detail without bloating README; JSON serves agents and future dashboards. A live dashboard endpoint is deferred.

### §10.4 Q4 - Lint and Harness CI Integration

Recommendation: shared GitHub Action published from runbooks meta-repo and consumed in each service repo.

Rationale: duplicated config would diverge immediately across five repos. The meta-repo owns linter/harness release behavior; service repos own manifests, runbook content, and CODEOWNERS.

### §10.5 Q5 - CODEOWNERS Implications

Recommendation: every service repo that receives runbooks must add CODEOWNERS entries for the moved docs.

Required process:

1. Target repo adds ownership for `/docs/*.md` and `/docs/runbook-manifest.yml`.
2. Owner must include service owner plus runbook owner agent or human maintainer.
3. Waivers from `BQ-RUNBOOK-IMPACT-GATE` require owner approval.
4. Central cross-cutting docs retain CODEOWNERS in runbooks meta-repo.

### §10.6 Q6 - Bus Factor and Discoverability

Recommendation: mitigate fragmentation with a stable generated index path and agent lookup artifact:

1. `aidotmarket/runbooks/README.md` is the stable entry.
2. `aidotmarket/runbooks/INDEX.md` is the full human index.
3. `aidotmarket/runbooks/runbook-index.json` is the agent lookup artifact.
4. Daily refresh and service merge dispatch prevent stale index state.
5. Deleted central files are not replaced with long-lived duplicate tombstones; the generated index carries replacements.

Rationale: decentralized docs without an index would reproduce AG's fragmentation risk at [/Users/max/.gemini/tmp/runbooks/runbook-audit-ag-2026-04-25.md:64](/Users/max/.gemini/tmp/runbooks/runbook-audit-ag-2026-04-25.md:64). The index is therefore a prerequisite, not a polish item.

## §11 Inbound-Reference Inventory

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

### §11.3 Active References in Backend Repo

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
| `recovery_runbook: docs/runbooks/sysadmin_railway_env_recovery.md` | `/Users/max/Projects/ai-market/ai-market-backend/app/agents/sysadmin/skills/railway_ops.py:292` | backend-local runbook | Not central; include in backend manifest or update if normalized. |

### §11.4 Active References in Koskadeux Repo

| Reference | Location | Target | Migration handling |
|---|---|---|---|
| `aidotmarket/runbooks/model-configuration.md` | `/Users/max/koskadeux-mcp/specs/BQ-MODEL-CONFIGURATION-RUNBOOK-gate1.md:13` and many Gate 2 chunk specs | model configuration runbook | Chunk 4 must decide central vs `koskadeux-mcp/docs/model-configuration.md`; update active specs/prompts accordingly. |
| `aidotmarket/runbooks/agent-dispatch.md` | `/Users/max/koskadeux-mcp/specs/BQ-MODEL-CONFIGURATION-RUNBOOK-gate1.md:66` | agent dispatch | Chunk 4 update to `koskadeux-operations` target. |
| `aidotmarket/runbooks/vulcan-configuration.md` | `/Users/max/koskadeux-mcp/specs/BQ-MODEL-CONFIGURATION-RUNBOOK-gate1.md:75` | Vulcan configuration | Chunk 4 update based on central/service decision. |
| `koskadeux-mcp/runbooks/activation-verification.md` | `/Users/max/koskadeux-mcp/specs/BQ-DEPLOY-ACTIVATION-VERIFICATION/GATE2.md:27` | activation verification | Chunk 4 update if `/docs` becomes canonical. |
| `/Users/max/Projects/runbooks/specs/BQ-RUNBOOK-STANDARD.md` | `/Users/max/koskadeux-mcp/specs/BQ-KOSKADEUX-G4-PROTOCOL-GATE1.md:416` through `:429` | frozen parent standard citations | Do not update unless those specs are reopened; these cite frozen standard lines. |

### §11.5 Frontend, AIM Node, vectoraiz

No active references to `/Users/max/Projects/runbooks/` or `aidotmarket/runbooks/*.md` were found in:

1. `/Users/max/Projects/ai-market/ai-market-frontend`
2. `/Users/max/Projects/ai-market/aim-node`
3. `/Users/max/Projects/vectoraiz`

This is a Gate 1 search result, not a permanent guarantee. Each migration chunk must rerun the scan from the target repo before deleting source files.

### §11.6 Living State and Prompt References

Known Living State references from `build:bq-runbook-decentralization`:

1. `BQ-CRM-RUNBOOK-STANDARD` currently needs a target adjustment to backend `/docs/crm-system.md`.
2. `BQ-RUNBOOK-STANDARD` continues unchanged but its preview migration plan names central runbook targets.
3. `decision:runbook-architecture-decentralization` records Option B and should remain as the architectural decision record.

Migration requirement:

1. Chunk 3 updates Living State references for CRM and briefing targets.
2. Chunk 4 updates Living State references for Koskadeux/AIM/vectoraiz runbook targets.
3. Chunk 5 updates any global resource registry or lookup prompt to point to `INDEX.md` or `runbook-index.json`.

### §11.7 Reference Update Policy

Every reference row gets one of these statuses during migration:

1. `updated`: changed to new target path.
2. `historical`: left unchanged because it cites a frozen historical spec or commit.
3. `central-retained`: left unchanged because target remains central.
4. `normalized`: changed from service-local `docs/runbooks` to service `/docs` target.
5. `blocked`: requires Council path decision.

Deletion of a central source file is blocked while any live reference row is `blocked`.

## §12 Final Gate 1 Recommendation

Approve Option B with strict sequencing:

1. Build index first.
2. Classify every existing file second.
3. Migrate backend/CRM/Gmail/Celery before lower-risk services.
4. Delete central files only after trace matrix, reference rewrites, index generation, lint, harness, and CODEOWNERS evidence exist.
5. Keep central cross-cutting SSOT docs only where central ownership prevents copying drift.

The design accepts AG's architecture while preserving MP's concrete cluster audit. The main tradeoff is higher upfront CI and indexing work, but it directly addresses the root cause: service docs must be versioned and reviewed with the service code they describe.
