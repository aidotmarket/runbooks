# Boot Kernel v2 Companion Source Cross-walk

**Authority:** evidence-only cross-walk for the seven versioned delivery companions. It is not a catalog authority and cannot override CORE, the Boot Kernel, or any companion's explicit authority boundary.

**Current source:** byte-identical canonical CORE v9.11 text at `/Users/max/Projects/ai-market/ai-market-backend/docs/core/CORE.md`, SHA-256 `3fd79b73debfae8f084ca4ccc4a4199e2b574d44e60c489567d6bc6b40941632`.

The source path records the exact file hashed during this build. Runtime integrity must compare the current `infra:constitution.body.content`; a path alone is never authority.

| Companion catalog id | Content class | CORE section(s) carried | Projection treatment | Source constitution SHA-256 |
|---|---|---|---|---|
| `council-roster-quirks` | Live roster, provider/model/tool details, and behavioral quirks | §4 Council Communications; §5 Council roster and peer frame | Marked normative extracts plus subordinate operational synthesis; volatile values route to `infra:council-comms` | `3fd79b73debfae8f084ca4ccc4a4199e2b574d44e60c489567d6bc6b40941632` |
| `agent-completeness` | Endpoint, skill, health, manifest, and monitoring completeness | §3 Agent Completeness Contract; §4 Agent Discovery | Marked normative extracts | `3fd79b73debfae8f084ca4ccc4a4199e2b574d44e60c489567d6bc6b40941632` |
| `gate-procedure` | Gate 1–4, CCP rounds and thresholds, dispatch tokens, leases, and syntax | §5 Council Consensus Protocol and Build Gates | Marked normative extracts plus subordinate kernel-design and live-dispatch synthesis | `3fd79b73debfae8f084ca4ccc4a4199e2b574d44e60c489567d6bc6b40941632` |
| `infrastructure-discovery` | Discovery directory and location workflow | §3 Data and Security; §4 Infrastructure discovery | Marked normative extracts plus three-surface route | `3fd79b73debfae8f084ca4ccc4a4199e2b574d44e60c489567d6bc6b40941632` |
| `aging-policy` | Staleness, WIP, repeat incidents, boot obligations, close carry, and anti-duplication | §6 Execution Discipline | Marked normative extracts | `3fd79b73debfae8f084ca4ccc4a4199e2b574d44e60c489567d6bc6b40941632` |
| `product-elaboration` | Detailed product narrative, surfaces, boundaries, and deferred history | §2 The Four Pillars; §9 Product Surface | Marked normative extracts | `3fd79b73debfae8f084ca4ccc4a4199e2b574d44e60c489567d6bc6b40941632` |
| `constitution-history` | Amendment history, source provenance, and prior versions | Version preamble; §5 decision rules by reference; final amendment clause | Marked normative extracts plus non-normative Git-history index | `3fd79b73debfae8f084ca4ccc4a4199e2b574d44e60c489567d6bc6b40941632` |

## Verification rules

- Every copied normative block in a companion names its exact CORE section and the same source SHA above.
- Companion synthesis is explicitly subordinate and cannot add, remove, weaken, strengthen, or reinterpret a CORE or kernel obligation.
- A change in current constitution bytes invalidates this cross-walk and all seven companion source labels until regenerated and reviewed.
- Publishing or revising a companion never edits `infra:constitution` or canonical `docs/core/CORE.md`; such an edit requires the separate amendment gate.
- Catalog membership and paths come only from generated `CATALOG.json`; this cross-walk is deliberately not a thirteenth catalog member.

## The boot catalog reference is resolved, not pinned (S1579, de-lockstepped)

Superseded: "The catalog pin and the installed validator move together (S1575)". That section described a three-surface pin that had to switch in one operation. Those surfaces are gone. `koskadeux-mcp` merge `4915866be9` deleted the four `BOOT_KERNEL_V2_CATALOG_{REF,DIGEST,ENTRIES,SECTIONS}` constants, the matching catalog fields in `boot_kernel/v2/manifest`, and the pairing between them (Gate 3: GLM and CC both APPROVE_WITH_NITS; Max directive 2026-08-19, BQ-GATE-ESTATE-REDUCTION-S1472 part (a)).

How it works now. At every session open, `tools/session.py::_resolve_boot_kernel_catalog` runs `git -C <installed runbooks checkout> rev-parse HEAD`, builds `git:aidotmarket/runbooks@<sha>:CATALOG.json` from the resulting 40-hex commit, and validates that reference through the installed `runbook-catalog` CLI with a 60-second timeout. It accepts only `status` in `("pass", "integrity_pass_unverified")` and additionally requires the report's `catalog_ref` and `catalog_sha` to equal what it asked for. Anything else raises `BOOT_KERNEL_CATALOG_INVALID` and the open fails. Kernel obligation I6 is preserved unchanged: the envelope still carries exactly one concrete 40-lowercase-hex SHA-pinned reference, and it is still fail-closed. What changed is only where that SHA comes from: the installed checkout's own committed HEAD, rather than a constant that had to be hand-moved in two files.

The corpus and the catalog no longer drift apart. `scripts/hooks/pre-commit` (installed via `scripts/install-hooks.sh`, which sets `core.hooksPath=scripts/hooks`) regenerates `CATALOG.json`, `TOPIC-ROUTER.md` and `README.md` and stages them on EVERY commit in this repository. It is advisory and can never block a commit; it traps all 23 catchable macOS signals whose default action is terminate, core or stop and exits 0 on every failure path. So the checkout HEAD's catalog is current with the checkout HEAD's corpus by construction, which is what makes resolving the reference from HEAD safe.

What still moves together. Exactly two things: the installed runbooks checkout and the installed `runbook-catalog` CLI (`/opt/homebrew/bin/runbook-catalog`, an editable pip install of `runbook_tools` from this repo, reached through PATH). A validator upgrade still means swapping the editable install (`python3.14 -m pip install -e /Users/max/Projects/ai-market/runbooks --break-system-packages`) alongside the checkout it must validate. Cross-schema mismatches still do not validate in either direction.

**Before flipping any instance to boot-kernel `shadow` or `on`, confirm the installed checkout sits on a commit the installed CLI validates.** Shadow is NOT purely observational where the catalog is concerned. In `tools/session.py` (currently lines 3388-3407), a `BootAssemblyError` raised while assembling the shadow kernel is recorded as a shadow-open event and then re-raised, so a catalog failure aborts the open in shadow mode exactly as it does in `on` mode. Verify by hand first: `runbook-catalog validate --catalog-ref git:aidotmarket/runbooks@$(git -C <checkout> rev-parse HEAD):CATALOG.json`, run from the checkout. (This discharges CC's LOW advisory from the part (a) Gate 3 review.)

Merging is not deploying. The MCP server keeps running its in-memory code until the reload-when-idle guard restarts it, and that guard defers while any background build is running AND while any session is live. Measured in S1580: the part (a) merge landed at 19:07 local, the guard deferred behind builds until 18:04Z and then behind the open session, so the very next session still booted on pre-merge code and its envelope still carried the old pinned SHA `396657dd`. Do not read a merge as live. The live proof is a FRESH open, after the last session has closed and the build queue has drained, whose envelope `catalog_ref` equals the installed checkout's current HEAD.
