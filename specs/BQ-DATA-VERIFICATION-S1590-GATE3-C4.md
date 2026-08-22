# BQ-DATA-VERIFICATION-S1590 — Gate 3 record, Chunk 4

Chunk: 4 of 6 (bounded allAI narrative, grounding validation, S1396 corpus capture, terminal-error report shape).
Repo: ai-market-backend. Branch: build/bq-data-verification-s1590-c4-s1596.
Base: 977e5802d5f0b2e7d170df5966a5fb39fb0c4b7b (origin/main fork point).
Approved head: 0e61b47585ea3921dc6ae2b72b90265f80d102cf.
Merged to main: 3286e0726382d4a5713e529d10c3d1fb0e87a023 (2026-08-22). Alembic head after merge: s1590_corpus_events (single).
Builder: MP (excluded from review). Orchestrator: Mars S1596 (non-voting). Panel: CC, Kimi, GLM (CORE S3 full panel — customer-data wire + payments).

## Outcome

Gate 3 APPROVED on unanimous approval-class at R5, head 0e61b4758: GLM APPROVE (zero findings), CC APPROVE_WITH_NITS, Kimi APPROVE_WITH_NITS. Zero open HIGH/MEDIUM findings.

## Round history

- R1 at d982508b9: REQUEST_CHANGES x3. CC: missing corpus-contract snapshot fixture left test_corpus_schema red (executed). Kimi: zero corpus lifecycle appends on payment-service terminal transitions (AC5). GLM: quote-time-only input budget; numeric grounding grammar gaps. Fold 1 (MP): snapshot+digest, maximal alnum-digit grounding rule, _transition_terminal_epoch wrapper on all terminal sites, pre/post budget checks, our-fault net, 2MB ingest body cap.
- R2 at 6eaa744e5: CC AWN, Kimi APPROVE_WITH_MANDATES (branch-ref repair — done), GLM RC (sign regression; bytes//3 not provably conservative; missing output cap). Fold 2 (MP): signed-lexical rule; provider-exact count_tokens preflight (zero chat calls on over-budget by construction); usage.output_tokens cap.
- R3 at 74504cfb1: CC AWN, Kimi AWN, GLM RC (sign-drop direction: evidence -3 authorized bare 3). Fold 3 (MP): one maximal signed numeric lexical grammar, symmetric whole-unit matching.
- R4 at 0bcce7c54: CC AWN (new NIT: non-ASCII sign glyphs, proven pre-existing), Kimi AWN, GLM RC (leading-dot fractions -.5 tokenized as bare 5). Micro-fold (mars, +7/-2, both remedies verbatim from the reviews): GLM's alternation for leading-dot fractions; CC's U+2212 -> '-' fold, symmetric.
- R5 at 0e61b4758: GLM APPROVE, CC AWN, Kimi AWN. Terminal.

R5 responses: cc/response-20260822-173936-717099.md, kimi/response-20260822-173946-892509.md, glm/response-20260822-173927-330035.md (under /Users/max/council/).

## Independent verification highlights

- CC executed the test suites at every round (final: nine suites 227 passed; all-12 set 248 passed), ran the migration chain live up/down/up on real PostgreSQL with append-only trigger enforcement confirmed, and ran ~45 adversarial grounding probes empirically.
- Kimi traced every terminal payment transition to the corpus-event wrapper site-by-site and verified exactly-once semantics on duplicate webhook delivery; caught the stale local branch ref that would have merged the wrong head.
- GLM drove four successive grounding-grammar hardenings (fused units, sign insertion, sign drop, leading-dot fractions) and the provider-exact pre-call budget gate; each closed with its own prescribed remedy.
- Mars independently re-ran the suites and the full grounding mutation/control matrix at every head before each dispatch and before merge.

## Non-blocking findings carried on the BQ entity (gate3_chunk4.nonblocking_carried)

Non-U+2212 sign decorations (en/em-dash, fullwidth, parenthesized negatives) remain magnitude-checked but sign-unchecked — pre-existing, narrowed by this chunk, one-line remedies recorded. Two-row our-fault corpus contract pinned by test. DB-level RLS backstop advisory. Bridge secret-scan push block is bypassable by the builder pushing from its worktree (control-integrity observation, S1596 evidence; systemic fix belongs to a builder-controls BQ). Grounding notice derivable from persisted narrative_state (literal storage not required).

## Ships disabled

All Chunk 4 behavior remains behind DATA_VERIFICATION_ENABLED=false. Production enablement still gated on CORE S3 checkpoints 8.1 (wire manifest) and 8.2 (payment state machine) per Gate 2.
