# Plan: make the runbooks findable, editable, and trusted — by removing what makes them hard

Author: Mars, S1635 (2026-08-29). Status: PROPOSAL for Max to assign. No implementation started.

## 1. Why this has been hard (ground truth, not opinion)

- The documentation is 82 Markdown files, 18,700 lines, in git. Findable by `grep`, by the topic router, by `allai_search`. That part has never been the problem.
- The tooling that governs the documentation is 17,900 lines of Python (`runbook_tools/`: catalog, linter with 15 checks, JSON schemas for every section, conformance, staleness, discovery vectors, harness). It is as large as the documentation itself.
- Since June, 185 of 796 commits to this repo were about the tooling, the router, the catalog, or the § standard — not about the systems the runbooks describe.
- The standard requires every runbook to have eleven sections in fixed YAML/table shapes with enum-validated cells. 5 of 82 runbooks pass it. The tooling then labels the other 77 "discovery-only, not eligible to authorize action". The "promotion" command that would make any runbook ACTIVE has never been deployed; it refuses by design.
- So the system we built tells the agents that almost nothing they read is authoritative, the agents then argue about which page counts, and every session spends time on the argument instead of the work. That is the loop you are tired of. It is self-inflicted.

The hard part was never findability or editability. We over-governed. Documentation is not code; it does not need a compiler.

## 2. Would an open-source system solve it?

Partly, and only the browsing part. The docs are already in the best possible store for AI agents (plain Markdown in git, read through the filesystem/MCP). Moving them into a wiki database (Outline, Wiki.js, Confluence-likes) creates a sync problem between the wiki and git and makes agent access worse. A static site generator that renders the git repo (MkDocs Material) gives you a searchable, browsable, editable-through-git site with zero infrastructure and no sync problem. That is the only external tool worth adopting, and it is optional.

Recommendation: keep Markdown in git; delete most of our tooling; add MkDocs Material for humans.

## 3. The new standard (fits on one screen)

A runbook is a Markdown file with a YAML header and free-form body. The header has five fields, nothing else is validated:

```yaml
title: Issue Channel
owner: mars                # who fixes it
last_verified: 2026-08-29  # date someone last confirmed the body is true
aliases: [CI health board, failure channel]
error_signatures: ["observation_complete\":false", "nodename nor servname"]
```

The body must contain a section named `## When it breaks` with a table of symptom | cause | fix. Everything else (architecture, procedures, invariants) is free prose, as long as the author likes. No enums, no schemas, no ACTIVE/DRAFT authority, no promotion. A runbook is authoritative because it exists and is dated; if it is wrong, fix it in the same session (existing rule).

## 4. Work plan (assignable units)

### W1 — Replace the tooling (one build, one review round)
- New `scripts/index.py` (~100 lines): reads the five header fields from every `*.md`, writes `INDEX.md` (alphabetical list with one-line purpose, aliases, owner, last_verified) and `ERRORS.md` (every error signature → file). Run by a pre-commit hook and CI. That is the entire router.
- A 30-line `scripts/check.py`: every runbook has the five fields, a `## When it breaks` section, a `last_verified` date; every `error_signature` is unique. CI fails only on these.
- Delete: `runbook_tools/` (all 17,900 lines), `CATALOG.json`, generated `TOPIC-ROUTER.md`/`README.md`, `templates/runbook.template.md`, `harness/`, `scripts/router_drift_check.py`, `scripts/generate_runbook_discovery_vectors.py` (allai indexing moves to a plain "index all *.md" job, W3). Keep the git history.
- Update the boot/session-open rule in koskadeux-mcp: `runbook_consultation` requires a file path and a heading, nothing else. Builder-output verification (`builder_output_verification.py`) reads sections by heading text, which keeps working.
- Acceptance: `INDEX.md` lists 82 files; `check.py` passes on all of them after W2's header rewrite; a new agent can answer "where is X documented" with `grep -i X INDEX.md ERRORS.md`.

### W2 — Convert and triage the 82 runbooks (three sessions, one repo, no Council)
- Mechanical: strip the §A–§K scaffolding to the five-field header + body; keep all prose; convert each §F table into `## When it breaks`. Scriptable for the 5 conforming files and the ~40 that are mostly prose; hand-edit the rest.
- Triage in the same pass: for each file decide keep / merge / archive (`archive/` folder, still indexed, marked archived in INDEX). Expected: ~55 keep, ~15 merge, ~12 archive.
- Freshness: any file whose `last_verified` is older than 90 days gets a one-line "unverified since <date>" banner from `index.py`; nothing is deleted for age.
- Acceptance: `check.py` green; INDEX shows every page; no page references CATALOG, promotion, ACTIVE/DRAFT, or discovery-only.

### W3 — Findability for agents and for Max (one build)
- Agents: `allai_search` indexes every `*.md` under `runbooks/` by heading chunk, re-indexed by CI on every push (replaces the discovery-vector generator). `INDEX.md` and `ERRORS.md` are read at session open; that is the only router.
- Max: MkDocs Material site built by CI from the same repo, published at a URL you can open on any device (GitHub Pages under the org, or ops.ai.market/docs behind the existing auth). Search box, sidebar from INDEX, "edit this page" opens the file in GitHub.
- Acceptance: a search for "Kimi cannot fetch branch" in either surface returns issue-channel.md within the top three.

### W4 — Stop the loop from re-forming (policy, no build)
- Rule added to the constitution/boot: no new runbook tooling, schema, linter check, or "authority" concept is built without a Max decision in the Event Ledger. Runbook work is writing and fixing runbooks, nothing else.
- The BQ that owns W1–W3 is closed with the tooling line count as evidence (target: under 300 lines of Python in this repo).

## 5. Sequencing and effort

W1 and W3 are builds (MP, one Gate 3 each; W3's site is low-risk). W2 is operator work, mostly Vulcan/Mars sessions with no Council. W4 is a one-line decision. Order: W1 → W2 → W3 → W4. Total: roughly five sessions across both instances. Nothing here touches production systems; the only runtime change is the allai index job and the session-open rule.

## 6. What is deliberately not in this plan

- No new wiki database, no CMS, no per-page approval workflow, no "authority" tiers.
- No attempt to make the current 15-check linter pass on 82 files; that is the work that has been failing since June.
