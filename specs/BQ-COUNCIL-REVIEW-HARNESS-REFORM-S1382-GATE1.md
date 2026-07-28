# BQ-COUNCIL-REVIEW-HARNESS-REFORM-S1382 — Gate 1 Design

- **Author:** Mars, S1382, 2026-07-28
- **Status:** GATE 1 R2 — CC R1 mandates M1–M5 and both minor findings folded (CC task 66d4e782, APPROVED_WITH_MANDATES) — for unanimous Council review (CC, Kimi, GLM). This is the machinery that enforces every other gate; it gets the strictest review class.
- **Authority chain:** RCA `specs/RCA-COUNCIL-REVIEW-FAILURES-S1382.md` @ `852c2a1f` (R5, Council-approved) → Max GO (event `ea8d4c12`) → Max adopt-first boundary decision (event `d7c3bd3c`), verbatim: *"Our issue is getting the right files to the LLM and getting the answer back. I believe open source solves that. What we do with it after that is our own code."*
- **Builder:** MP (CORE §4). MP excluded from review.

## 1. Goal

Make the GLM and Kimi Council seats reliable by replacing our bespoke in/out plumbing with adopted open-source components, while keeping everything downstream of the returned structured answer — verdict handling, voting/unanimity, gate semantics, Living State — bespoke and unchanged in ownership.

## 2. The boundary (normative)

**Adopted layer** (open source is the default; keeping any bespoke component here requires written justification in the Gate 2 spec):
- Deterministic context/diff packing: the reviewer receives the complete, verified `base..head` changed-set, generated deterministically. Candidate: PR-Agent's packing approach or the tool itself (Apache-2.0).
- Multi-provider dispatch with correct token and cost accounting. Candidate: LiteLLM. Retires the byte-as-token budget projector (T-2026-000460b).
- Structured answer return via provider-native `response_format`/`json_schema` (see §3 — verified).

**Owned layer** (bespoke, unchanged): the **authoritative structured-answer schema itself** — the interface contract between the two layers — defined in exactly one canonical in-repo location (`council_dispatch_middleware/verdict_schema.json` in koskadeux-mcp; C4 creates it if absent) and consumed by both provider enforcement and the fallback validator; verdict handling after the structured answer returns, voting and unanimity rules, gate semantics, reviewer roster, Living State integration, audit/evidence trail, and the CC agentic repo-loop review path.

## 3. AC1 evidence — provider enforcement is real (probe run 2026-07-28, S1382)

Probe: adversarial prompt explicitly instructing the model to add an extra key, omit a required key, and wrap output in markdown fences; schema `{verdict: enum, findings: array, summary: string}` with `additionalProperties=false`, `strict=true`. Two runs per provider against the exact production model IDs.

| Target | With json_schema | Control (no schema, same prompt) |
|---|---|---|
| `z-ai/glm-5.2` via OpenRouter | **STRICT, 2/2**: clean JSON, no fences, no extra/missing keys, enum respected, `finish_reason=stop` | BEST-EFFORT: fenced JSON, four wrong keys, all three required keys missing |
| `kimi-k3` via Moonshot | **STRICT, 2/2**: clean JSON, no fences, no extra/missing keys, enum respected, `finish_reason=stop` | Non-JSON empty content, `finish_reason=length` |

Conclusion: server-side enforcement holds for our exact models, and the controls reproduce precisely the failure classes the RCA documented. The load-bearing assumption of this design is verified, not asserted. (Probe script committed as `specs/tools/ac1_enforcement_canary.py` in this repo — the durable, version-controlled source that C5 promotes to a continuously running CI canary.)

**Fallback rule (normative):** the single post-hoc validator fail-closes, with the raw completion always preserved for operator adjudication, in BOTH of these distinct cases: (a) enforcement regression (provider routing change, model swap, parameter silently ignored), and (b) **truncation-under-enforcement** — any completion whose `finish_reason` is not `stop` (`length`, content-filter, etc.), which the probe's own Kimi control demonstrated can yield empty or invalid content even when schema enforcement is nominally active. Raw completions are never discarded in any path (RCA failure class 4 must be structurally impossible under enforcement, regression, and truncation alike). The §3 snapshot is a point-in-time signal, not a stability guarantee; the continuously running C5 canary is what carries the assumption forward.

## 4. Vote-equivalence rule (normative; ratified by approving this Gate 1)

A GLM/Kimi single-completion vote counts **full-weight** under the unanimity rule **only when** the packer verifies the complete deterministic `base..head` changed-set was delivered (fail-closed on truncation or mismatch, verified by file count and content digest). Otherwise the vote is recorded as scope-limited. **Operational effect (normative):** a scope-limited seat leaves unanimity UNREACHABLE for that gate unless one of exactly two things happens: (i) the seat is re-dispatched with a complete verified pack and returns a full-weight vote, or (ii) CC performs a full-weight agentic repo-loop review explicitly covering the scope-limited seat's gap, in which case the gate records CC-coverage-substitution as an audited event and the scope-limited vote stands as advisory. A scope-limited REJECT always blocks regardless. CC retains the agentic repo-loop path. Council approval of this Gate 1 ratifies this rule (CC R1 M2 on the RCA); Max retains override per CORE §5.

## 5. Chunking

- **C1 — Enforcement probe. DONE** (§3). Remaining C1 work: none.
- **C2 — Dispatch + accounting:** adopt LiteLLM for GLM/Kimi calls; `max_budget_usd` honored end-to-end; retire the byte-as-token projector and the env-pinned $2 cap (T-2026-000460b). **Measurable exit bar:** library-reported tokens and cost reconcile against provider-reported usage on every call within an explicit tolerance (±1% tokens, ±2% cost, tightened or justified in the C2 Gate 2 spec); reconciliation failures are logged and surfaced, never silently absorbed.
- **C3 — Deterministic packing:** complete `base..head` generation with verification digest; retire the coverage controller for GLM/Kimi (`base` parameter defect T-2026-000460a dies with it); oversize changed-sets fail closed with an explicit scope-limited option, never silent truncation.
- **C4 — Extraction collapse:** one enforced answer path (provider `json_schema` per §3, fallback per §3); delete the two legacy extraction modes (RCA failure class 5); dispatcher rejects brief-requested keys outside the authoritative schema at dispatch time (failure class 4).
- **C5 — Trial + canary:** time-boxed reversible trial with acceptance criteria — verdict-agreement with CC on a shared sample, defect-escape rate, and zero harness-caused non-verdicts; the §3 probe becomes a CI canary. Old path stays behind a flag until the trial passes; rollback is a flag flip.

Each chunk: Gate 2 implementation spec, MP build, unanimous Council Gate 3.

## 6. Dependency policy (normative)

Adopted dependencies are pinned by **integrity hash via lockfile, covering the full transitive closure** — version numbers alone are insufficient on a safety-critical path (re-published tags, dependency confusion, compromised releases). Selection in the C2/C3 Gate 2 specs must additionally record: a vulnerability scan of the complete dependency closure as a selection gate, upstream health (release cadence, license, maintainer status), and a fork-readiness statement. Known signal: the original PR-Agent maintainer is drifting toward closed SaaS — pin an audited version or adopt the packing approach rather than the whole tool if health checks fail.

## 7. Out of scope

The CC review path; Council roster and composition; T422 terminal-wrapper repair (Vulcan's, addresses RCA class 1 on the legacy path and remains valuable until C2–C4 land); the backend repo; any change to gate definitions or CORE.

## 8. Risks

Upstream drift on a safety-critical path (mitigated by §6 pinning and the C5 canary); enforcement regression (mitigated by §3 fallback + canary); unequal review depth across seats (governed by §4); migration-period dual paths (bounded by C5's flag and time-box); and the new failure surface the adopted libraries themselves introduce (LiteLLM mis-accounting, packer edge cases on unusual diffs) — guarded by the C2 reconciliation bar and the C3 verification digest, and accepted as a better-understood surface than the bespoke code it replaces.
