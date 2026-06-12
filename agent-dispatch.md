
## §R — MP spec-file dispatch standard (canonical, S827)

Canonical pattern for any MP dispatch grounded in a spec (Max directive S826, probe-verified S827; Living State: `infra:council-comms.mp_spec_file_dispatch_standard`).

Reference the COMMITTED spec path at a pinned commit SHA — never a bare path, never long specs pasted inline (Codex /goal objectives cap at 4,000 chars; real specs do not fit). Required thin-contract wrapper elements:

1. Read instruction: "use `git show <SHA>:<path>` — do not trust the working tree".
2. Scope guards: READ-ONLY for reviews, plus the S452 prefix (DO NOT git add/commit/push/modify) — MP treats READ-ONLY as advisory.
3. Output contract: numbered parts, §-citation requirement against the spec's own section numbers.
4. Untruncated-read proof: demand the exact first and last line of the file verbatim.
5. Explicit stop condition.

/goal prefix is optional: the goals feature is stable+enabled on Titan-1 Codex 0.139.0 and /goal-prefixed prompts are accepted via `codex exec`, but goal-LOOP engagement (multi-turn autonomy to a stop condition) in non-interactive exec is UNVERIFIED on long builds. Do not rely on loop autonomy until a long-build dispatch demonstrates it; the load-bearing, proven element is path@SHA + wrapper.

Evidence: S827 probe — MP read specs/BQ-ALLAI-ACTIVATION-S826-GATE1.md @ 4e9cfec6 (koskadeux-mcp), exact first+last lines returned verbatim, accurate §-citations, zero file modifications, 66s.
