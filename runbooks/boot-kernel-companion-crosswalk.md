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
