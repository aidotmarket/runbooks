# BQ-RUNBOOK-STANDARD — Gate 2 Chunk 1 (Infrastructure)

**Status:** Gate 2 R1 (Vulcan authoring — S487)
**Parent:** `specs/BQ-RUNBOOK-STANDARD.md` (Gate 1 APPROVED at commit `365c198`, 670 lines)
**Priority:** P0
**Repo:** `aidotmarket/runbooks`
**Chunk scope (this spec):** §9 Gate 2 deliverables 1–3
- **D1** `runbook-lint` + template validator
- **D2** stateless-agent harness scaffold
- **D3** runbook index `README.md`
**Out of chunk scope (follow-on chunk):** §9 deliverables 4–5 (Infisical reference runbook, AIM Node G4 falsifiability runbook) — covered by `BQ-RUNBOOK-STANDARD-GATE-2-CHUNK-2.md` authored after D1–D3 ship. Retrofits (steps 6–8) are child BQs.

---

## 1. Purpose

Ship the enforcement infrastructure that makes the Gate 1 standard compulsory and measurable in CI. Without this chunk, the standard is documentation; with it, the standard is a PR-blocking contract. Everything Chunk 2 and the retrofit child BQs produce runs through the tooling this chunk ships.

**What this chunk unlocks:**
- Any PR that adds a non-conformant runbook to `aidotmarket/runbooks` fails CI.
- New-runbook scaffolds are one command (`runbook-new <s>`).
- Stateless-agent legibility has a reproducible nightly number per runbook.
- Every system under the standard has a central index showing its conformance state and gate progress.

**What this chunk does NOT unlock:**
- Any actual runbook authored to the standard (that's Chunk 2 for Infisical/AIM Node; subsequent child BQs for retrofits).
- The G4 falsifiability protocol running on a real target (Chunk 2 is the first G4 dry-run).

---

## 2. Scope boundary

**In scope for Gate 2 Chunk 1:**
- Python package `runbook_tools/` in `aidotmarket/runbooks/` implementing `runbook-lint`, `runbook-new`, and the harness runner.
- `harness/` scaffold: scenario YAML grammar, MP dispatch wrapper, scorer, result writer.
- `README.md` at repo root listing adoption targets + per-system conformance status + per-system gate status.
- GitHub Actions: PR-blocking `runbook-lint` workflow + nightly harness workflow.
- `schemas/` directory: JSON Schema for each agent form (machine-readable grammar companion to §4 of the Gate 1 spec).
- Test suite for the tooling itself (pytest).

**Out of scope for Gate 2 Chunk 1:**
- Any runbook content. This chunk MUST land and pass its own tests against fixture runbooks (`tests/fixtures/`) — no real runbook is required to exist before this chunk merges.
- G4 protocol implementation (lives in Koskadeux MCP + Living State per Gate 1 §7; not in this repo).
- Auto-remediation (lint is reporting, not fixing; scaffolds are separate from lint).

**Deferred to Gate 2 Chunk 2:**
- Infisical runbook (initial reference, §9 step 4)
- AIM Node runbook (G4 falsifiability, §9 step 5)

**Deferred to child BQs:**
- CRM retrofit (`BQ-CRM-RUNBOOK-STANDARD`, Gate 1 APPROVED at commit `1dbb822b`, needs re-scope to retrofit)
- Celery retrofit (child BQ TBD)
- Remaining systems (child BQs per §9 step 8)

---

## 3. Repository layout (post-Gate 2 Chunk 1)

```
aidotmarket/runbooks/
├── README.md                       # D3 runbook index (§7 of this spec)
├── pyproject.toml                  # Python packaging (§8.1)
├── .github/
│   └── workflows/
│       ├── runbook-lint.yml        # PR-blocking (§4.9)
│       └── runbook-harness.yml     # Nightly (§6.7)
├── runbook_tools/                  # Python package
│   ├── __init__.py
│   ├── cli.py                      # entry points: runbook-lint, runbook-new, runbook-harness
│   ├── parser/                     # markdown → AST → typed sections
│   │   ├── __init__.py
│   │   ├── markdown_ast.py         # mistune-based AST wrapper
│   │   └── sections.py             # §A–§K section extractor
│   ├── lint/                       # §K.1 validation checks (20 checks, §4.4)
│   │   ├── __init__.py
│   │   ├── checks.py               # all 20 checks as named functions
│   │   ├── forms.py                # agent-form grammar validators (§4.4)
│   │   └── staleness.py            # §J STALE predicate + grace workflow (§4.6)
│   ├── scaffold/                   # runbook-new (§5)
│   │   ├── __init__.py
│   │   └── template.py
│   ├── harness/                    # stateless-agent harness (§6)
│   │   ├── __init__.py
│   │   ├── loader.py               # scenario YAML loader (§6.1)
│   │   ├── runner.py               # MP dispatch wrapper (§6.3)
│   │   ├── scorer.py               # scoring algorithm (§6.4)
│   │   └── writer.py               # result JSON writer (§6.6)
│   └── version.py                  # LINTER_VERSION constant (§4.8)
├── schemas/                        # JSON Schema per agent form (§4.4)
│   ├── section_a_header.schema.json
│   ├── section_b_capability_matrix.schema.json
│   ├── section_c_architecture.schema.json
│   ├── section_d_capability_map.schema.json
│   ├── section_e_operate.schema.json
│   ├── section_f_isolate.schema.json
│   ├── section_g_repair.schema.json
│   ├── section_h_evolve.schema.json
│   ├── section_i_acceptance.schema.json
│   ├── section_j_lifecycle.schema.json
│   ├── section_k_conformance.schema.json
│   └── scenario.schema.json        # harness scenario YAML (§6.1)
├── templates/
│   └── runbook.template.md         # §5.4 scaffold template
├── harness/
│   ├── scenarios/                  # populated by per-system runbooks (empty in Chunk 1)
│   │   └── .gitkeep
│   └── results/                    # populated by nightly CI
│       └── .gitkeep
├── tests/
│   ├── __init__.py
│   ├── conftest.py
│   ├── fixtures/
│   │   ├── conformant.md
│   │   ├── missing_section_c.md
│   │   ├── bad_table_columns.md
│   │   ├── dangling_repair_ref.md
│   │   ├── unbalanced_weights.md
│   │   ├── stale_unrefreshed.md
│   │   └── … (one fixture per check #1–#20)
│   ├── test_parser.py
│   ├── test_forms.py
│   ├── test_checks.py
│   ├── test_staleness.py
│   ├── test_scaffold.py
│   ├── test_harness_loader.py
│   ├── test_harness_scorer.py
│   └── test_integration.py         # end-to-end lint + harness on a conformant fixture
├── specs/                          # (existing)
│   └── BQ-RUNBOOK-STANDARD.md
│   └── BQ-RUNBOOK-STANDARD-GATE-2-CHUNK-1.md  # this document
└── <existing legacy runbooks>       # ai-market-backend.md, crm-target-state.md, etc.
```

**Legacy runbooks** (pre-standard) are NOT validated by `runbook-lint` in Chunk 1. Linting runs in one of three modes per the CI workflow (§4.9):
- **`strict`** — all runbooks listed in the README Conformant section must pass
- **`probationary`** — runbooks listed as Gate 1/2 in progress are linted informationally (results posted as PR comments, not PR-blocking)
- **`legacy`** — runbooks not yet under the standard are skipped entirely

The README (§7) is the source of truth for which mode applies to each runbook.

---

## 4. `runbook-lint` design

### 4.1 CLI interface

```
runbook-lint [options] [PATH ...]

Arguments:
  PATH                              One or more runbook paths or directories. If a
                                    directory, lints all *.md files at the directory
                                    root (not recursive; runbooks live at repo root).
                                    Default: repo root.

Options:
  --version                         Print LINTER_VERSION and exit 0.
  --mode {strict,probationary,legacy}
                                    Override the per-runbook mode from README.md.
                                    Default: derived from README.md index (§7).
  --format {text,json,github}       Output format.
                                    text: human-readable, used in local dev.
                                    json: structured, one object per finding.
                                    github: GitHub Actions workflow-command syntax
                                           (::error::, ::warning::) for PR annotations.
                                    Default: text.
  --fix-hints {on,off}              Include fix hints in findings. Default: on.
  --schemas-dir PATH                Override schemas/ directory. Default: ./schemas/
                                    (discovered relative to repo root).
  --readme PATH                     Override README.md path for mode derivation.
                                    Default: ./README.md.
  --summary                         Print only the aggregate PASS/WARN/FAIL summary
                                    (suppress per-finding output).
```

**Exit codes:**
- `0` — no FAIL findings (WARN findings allowed)
- `1` — at least one FAIL finding
- `2` — usage error (bad arguments, missing schemas, unreadable file)
- `3` — internal error (parser crash, schema validation library failure)

**Rationale for the exit-code split:** CI treats `0` as green, `1` as red, `2`–`3` as infrastructure failure (alert on-call, not PR author). The PR-blocking contract is exit `0` or `1`.

### 4.2 Markdown parsing strategy

**Library:** `mistune >= 3.0` (CommonMark, table extension, fenced code block extension). Chosen because: pure Python, no native deps, AST mode supported, stable API, already installable via pip.

**Strategy:**
1. Parse runbook markdown → mistune AST (tokens).
2. Walk AST; extract §A–§K as typed `Section` objects keyed by heading regex (`^##\s+§[A-K]\.\s+`).
3. Each `Section` retains its heading, raw markdown, parsed AST subtree, and computed line range.
4. Agent forms (§4.4) are extracted from within each section by form-specific extractors.

**Section identification rule:** The heading regex MUST match `## §<letter>. <title>` with the dot and space after the letter. Headings like `### §E.1 Sub-form` do not start a new top-level section — they are sub-content of §E. Missing dot (`## §E Operate`) is a §K.1 check #1 FAIL.

**Ordering rule:** §K.1 check #1 requires sections appear in alphabetical order. The linter compares the sequence of `Section.letter` values against `['A','B','C','D','E','F','G','H','I','J','K']`. Missing letters and out-of-order letters both trigger check #1 FAIL with distinct messages (`missing §<letter>` vs `§<letter> appears out of order`).

### 4.3 Section-presence validation

Implemented by `lint/checks.py:check_01_sections_present_and_ordered`. This is §K.1 check #1.

```python
def check_01_sections_present_and_ordered(sections: list[Section]) -> list[Finding]:
    letters = [s.letter for s in sections]
    expected = list("ABCDEFGHIJK")
    findings = []
    for e in expected:
        if e not in letters:
            findings.append(Finding(severity="FAIL", check=1, message=f"missing §{e}"))
    if letters != sorted(letters):
        findings.append(Finding(severity="FAIL", check=1,
            message=f"sections out of order: got {letters}, expected {expected[:len(letters)]}"))
    return findings
```

All 20 checks live in `lint/checks.py` as `check_NN_*` functions with the same signature. `cli.py` aggregates and dispatches.

### 4.4 Agent-form grammars

This is the most substantial part of Gate 2 Chunk 1. Each §C–§K section has a single required agent form per Gate 1 §4. Chunk 1 ships a JSON Schema per form in `schemas/` AND a per-form extractor in `lint/forms.py` that parses the markdown form into a Python dict and validates against the schema.

The JSON Schemas are authoritative machine-readable grammars for the agent forms. The markdown is what humans and the linter parse; the Schema defines the acceptable post-parse shape.

#### 4.4.1 §A Header — YAML frontmatter

**Grammar:** YAML frontmatter at the very top of the file, delimited by `---`. Must precede any other content including the `# <title>` H1.

```yaml
---
system_name: infisical-secrets
purpose_sentence: Centralized secret storage and distribution for ai.market backend, frontend, aim-node, and CI.
owner_agent: sysadmin
escalation_contact: max
lifecycle_ref: §J
authoritative_scope: Secret values, access policies, rotation schedule, and sync to deployment environments.
linter_version: 1.0.0
---
```

**JSON Schema** (`schemas/section_a_header.schema.json`) — key excerpt:

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "type": "object",
  "required": ["system_name", "purpose_sentence", "owner_agent", "escalation_contact",
               "lifecycle_ref", "authoritative_scope", "linter_version"],
  "additionalProperties": false,
  "properties": {
    "system_name":       {"type": "string", "pattern": "^[a-z0-9][a-z0-9-]*[a-z0-9]$"},
    "purpose_sentence":  {"type": "string", "minLength": 20, "maxLength": 300,
                          "pattern": "\\.$"},
    "owner_agent":       {"type": "string",
                          "enum": ["vulcan","mp","ag","xai","cc","sysadmin","crm_steward",
                                   "matchmaker","marketing","ralph","listing_enricher",
                                   "allai_brain","agent_log","max"]},
    "escalation_contact":{"type": "string"},
    "lifecycle_ref":     {"const": "§J"},
    "authoritative_scope":{"type": "string", "minLength": 20},
    "linter_version":    {"type": "string", "pattern": "^\\d+\\.\\d+\\.\\d+$"}
  }
}
```

**Rationale for the fixed `lifecycle_ref: §J`:** Gate 1 §4 §A declares §J is authoritative; this schema enforces that the header cannot claim a different authority source. Any divergence is §K.1 check #3 FAIL.

#### 4.4.2 §B Capability Matrix — markdown table, exact columns

**Grammar:** GitHub-flavored markdown table with EXACT header row:

```markdown
| Feature/Capability | Status | Backing Code | Test Coverage | Last Verified |
|---|---|---|---|---|
| Secret read via CLI | SHIPPED | `runbook_tools/secrets.py:read_secret` | `tests/test_secrets.py::test_read` | 2026-04-15 |
| Secret rotation UI | PLANNED | — | — | — |
```

**Column rules:**
- Header row must match `Feature/Capability | Status | Backing Code | Test Coverage | Last Verified` byte-for-byte (check #20).
- `Status` cell must be one of `SHIPPED`, `PARTIAL`, `PLANNED`, `DEPRECATED`, `BROKEN` (check #5).
- `Backing Code` cell must be a backticked path of form `<file>:<function>` or `<module>` OR the literal `—` (em dash) if `Status` is `PLANNED` or `DEPRECATED`. Non-PLANNED/DEPRECATED rows with `—` backing code are check #6 FAIL.
- `Test Coverage` cell: backticked test path or `—`. No severity check on `—` values in Chunk 1 (may be elevated in a future chunk).
- `Last Verified` cell: ISO date `YYYY-MM-DD` or empty or `—`. Empty/em-dash triggers check #7 WARN (UNVERIFIED overlay) and contributes to STALE per §J.

**UNVERIFIED overlay rendering:** The linter does not modify the runbook. The overlay is an in-memory annotation used for staleness calculation (check #15) and for `--format text` human output (`SHIPPED (UNVERIFIED)`).

#### 4.4.3 §C Architecture & Interactions — markdown table

**Grammar:** GitHub-flavored markdown table with EXACT header:

```markdown
| Component | Component Entry Point | State Stores | Integrates With | Notes |
|---|---|---|---|---|
| CLI | `infisical/cli.py:main` | — | Infisical API, `~/.infisical/config` | … |
```

**Column rules:**
- `Component Entry Point` cell: backticked `<file>:<function>` or `<module>`. Exactly one per component. Additional per-repair-path entry points live in §G, not §C (Gate 1 §C/§G distinction).
- `State Stores` cell: comma-separated list of named stores (`users table`, `sessions cache`, `user_sessions`, `infisical-config Living State key`). Empty cell uses `—`.
- `Integrates With` cell: comma-separated. May reference by endpoint path, queue name, file path, or other system's §C Component.

Prose narrative MAY appear above or below the table. Diagrams optional.

#### 4.4.4 §D Agent Capability Map — markdown table

```markdown
| Agent | Operation | Skill/Tool | Auth Scope | Coverage Status |
|---|---|---|---|---|
| vulcan | read secret | `Koskadeux:shell_request → infisical secrets get` | service-account-readonly | COMPLETE |
| allai_brain | read secret | — | — | GAP — skill registration pending (BQ-ALLAI-INFISICAL-SKILL) |
```

**Column rules:**
- `Coverage Status` ∈ {`COMPLETE`, `PARTIAL`, `GAP`, `PLANNED`}.
- Rows with `GAP` or `PARTIAL` Status MUST name the closure path in Notes (via trailing `— <text>` in the `Coverage Status` cell). Check: if Status is GAP or PARTIAL and no `— ` separator present, FAIL with "coverage gap row requires closure text after '— '".

#### 4.4.5 §E Operate — scenario list in fenced YAML block

**Grammar:** A fenced code block with info string `yaml operate` containing a YAML list. One or more blocks allowed; concatenated by the parser.

    ```yaml operate
    - id: E-01
      trigger: Support ticket reporting a missing secret in the prod frontend deploy
      pre_conditions:
        - user_authenticated
        - infisical_reachable
      tool_or_endpoint: infisical secrets get --project-id <id> --env prod --path <path>
      argument_sourcing:
        project_id: constant — see §A authoritative_scope
        env: constant prod
        path: from ticket body
      idempotency: IDEMPOTENT
      expected_success:
        shape: Plaintext secret printed to stdout
        verification: Compare against CI job value at the same commit SHA
      expected_failures:
        - signature: "secret not found"
          cause: path typo or env misconfigured
      next_step_success: Return secret to caller via secure channel (§G-02)
      next_step_failure: Escalate to §F-03 symptom search
    ```

**JSON Schema** (`schemas/section_e_operate.schema.json`):

```json
{
  "type": "array",
  "minItems": 3,
  "items": {
    "type": "object",
    "required": ["id", "trigger", "pre_conditions", "tool_or_endpoint",
                 "argument_sourcing", "idempotency", "expected_success",
                 "expected_failures", "next_step_success", "next_step_failure"],
    "additionalProperties": false,
    "properties": {
      "id":                 {"type": "string", "pattern": "^E-\\d{2,}$"},
      "trigger":            {"type": "string", "minLength": 10},
      "pre_conditions":     {"type": "array", "items": {"type": "string"}},
      "tool_or_endpoint":   {"type": "string"},
      "argument_sourcing":  {"type": "object", "additionalProperties": {"type": "string"}},
      "idempotency":        {"enum": ["IDEMPOTENT","NOT_IDEMPOTENT","IDEMPOTENT_WITH_KEY"]},
      "idempotency_key":    {"type": "string"},
      "expected_success":   {"type": "object",
                             "required": ["shape","verification"],
                             "properties": {"shape":{"type":"string"},
                                            "verification":{"type":"string"}}},
      "expected_failures":  {"type": "array",
                             "items": {"type": "object",
                                       "required":["signature","cause"],
                                       "properties":{"signature":{"type":"string"},
                                                     "cause":{"type":"string"}}}},
      "next_step_success":  {"type": "string"},
      "next_step_failure":  {"type": "string"}
    },
    "allOf": [
      {
        "if": {"properties": {"idempotency": {"const": "IDEMPOTENT_WITH_KEY"}}},
        "then": {"required": ["idempotency_key"]}
      }
    ]
  }
}
```

**Rationale for YAML (not markdown table):** §E scenarios have nested structure (`expected_failures` is a list of objects; `argument_sourcing` is a dict). Markdown tables can't carry this; prose makes linting unreliable. YAML in a fenced block is unambiguous and parseable.

**Rationale for `minItems: 3`:** Matches Gate 1 §4 §I "at least 3 §E Operate scenarios."

#### 4.4.6 §F Isolate — markdown table

```markdown
| ID | Symptom | Probable Causes | Verification Procedure | Repair Ref | Confidence |
|---|---|---|---|---|---|
| F-01 | "secret not found" in prod | env misconfigured, path typo | `infisical secrets list` to confirm path existence | §G-02 | CONFIRMED |
```

**Column rules:**
- `ID` matches `^F-\d{2,}$` (check: pattern).
- `Repair Ref` cell: `§G-\d{2,}` or empty. If non-empty, check #8 verifies it resolves to a real §G `id`.
- `Confidence` ∈ {`CONFIRMED`, `HYPOTHESIZED`, `DEPRECATED`} (per Gate 1 §5).

#### 4.4.7 §G Repair — fenced YAML block

    ```yaml repair
    - id: G-02
      symptom_ref: F-01
      component_ref: CLI
      root_cause: User supplied wrong env flag
      repair_entry_point: infisical/cli.py:resolve_env
      change_pattern: Add env-name normalization + helpful error for common typos
      rollback_procedure: Revert commit; no data migration.
      integrity_check: Re-run the failing scenario end-to-end, confirm secret returns.
    ```

**JSON Schema:**

```json
{
  "type": "array",
  "items": {
    "type": "object",
    "required": ["id", "symptom_ref", "component_ref", "root_cause",
                 "repair_entry_point", "change_pattern", "rollback_procedure",
                 "integrity_check"],
    "additionalProperties": false,
    "properties": {
      "id":                 {"type": "string", "pattern": "^G-\\d{2,}$"},
      "symptom_ref":        {"type": "string", "pattern": "^F-\\d{2,}$"},
      "component_ref":      {"type": "string"},
      "root_cause":         {"type": "string"},
      "repair_entry_point": {"type": "string"},
      "change_pattern":     {"type": "string"},
      "rollback_procedure": {"type": "string"},
      "integrity_check":    {"type": "string"}
    }
  }
}
```

**Cross-reference checks:**
- Check #9: every `symptom_ref` resolves to an §F row `ID`.
- Check #10: every `component_ref` resolves to a §C row `Component`.

#### 4.4.8 §H Evolve — change-class predicate tree as structured subsections

**Grammar:** §H has sub-heading structure, not a single form block. Required subsections:
- `### §H.1 Invariants` — bulleted list
- `### §H.2 BREAKING predicates` — bulleted list
- `### §H.3 REVIEW predicates` — bulleted list
- `### §H.4 SAFE predicates` — bulleted list
- `### §H.5 Boundary definitions` — definition list or sub-subheadings for `module`, `public contract`, `runtime dependency`, `config default`
- `### §H.6 Adjudication` — prose

**Check:** the six subsections must be present and in order. The linter does not validate the prose content of the predicates themselves at Chunk 1 (deferred to human review and the harness scenarios that classify changes).

**Rationale for prose-not-code predicates:** The predicates are cross-cutting business rules that humans adjudicate. The harness (§I Evolve scenarios) exercises them; the linter enforces structural presence only.

#### 4.4.9 §I Acceptance Criteria — fenced YAML block

    ```yaml acceptance
    scenario_set:
      - id: I-01
        type: operate          # operate | isolate | repair | evolve | ambiguous
        refs: [E-01]
        scenario: Support reports missing prod secret at path foo/bar/baz
        expected_answers:
          - kind: tool_call
            tool: infisical secrets get
            argument_keys: [project-id, env, path]
          - kind: tool_call
            tool: runbook_tools.secrets.read_secret
            argument_keys: [env, path]
        weight: 0.10
      - id: I-02
        …
    ```

**Required fields per scenario:**
- `id` — unique string matching `^I-\d{2,}$`
- `type` — one of `operate`, `isolate`, `repair`, `evolve`, `ambiguous`
- `refs` — list of referenced §E/§F/§G/§H IDs (validated by cross-check: every ref must resolve)
- `scenario` — prose description fed to the stateless MP
- `expected_answers` — list of accepted answer shapes (see §6.4 for shape definitions)
- `weight` — float in `[0, 1]`

**Scenario-set constraints (check #11):**
- Total count ≥ 10
- ≥ 3 with `type: operate`
- ≥ 3 with `type: isolate`
- ≥ 2 with `type: repair`
- ≥ 2 with `type: evolve`
- ≥ 1 with `type: ambiguous`

**Weight constraints (checks #12, #13):**
- Sum of all weights = 1.0 ± 0.001
- Default: equal weight (`1.0 / N`) per scenario; when default, the linter computes and allows any weight within `1/N ± 1e-6`
- If weights are unequal (any weight differs from `1/N` by > `1e-6`), an `### §I.1 Weight Justification` subsection MUST be present with one bulleted entry per scenario whose weight differs from default, each entry starting with the scenario `id`

#### 4.4.10 §J Lifecycle — fenced YAML block

    ```yaml lifecycle
    last_refresh_session: S487
    last_refresh_commit: 365c198
    last_refresh_date: 2026-04-21T17:30:00Z
    owner_agent: sysadmin
    refresh_triggers:
      - bq_completion
      - gate_approval
      - incident
    scheduled_cadence: 90d
    last_harness_pass_rate: 0.90
    last_harness_date: 2026-04-20T02:00:00Z
    first_staleness_detected_at: null
    ```

**JSON Schema:**

```json
{
  "type": "object",
  "required": ["last_refresh_session", "last_refresh_commit", "last_refresh_date",
               "owner_agent", "refresh_triggers",
               "last_harness_pass_rate", "last_harness_date",
               "first_staleness_detected_at"],
  "additionalProperties": false,
  "properties": {
    "last_refresh_session":        {"type": "string", "pattern": "^S\\d+$"},
    "last_refresh_commit":         {"type": "string", "pattern": "^[a-f0-9]{7,40}$"},
    "last_refresh_date":           {"type": "string", "format": "date-time"},
    "owner_agent":                 {"type": "string"},
    "refresh_triggers":            {"type": "array", "minItems": 1,
                                    "items": {"type": "string"}},
    "scheduled_cadence":           {"type": "string", "pattern": "^\\d+[dwmy]$"},
    "last_harness_pass_rate":      {"type": "number", "minimum": 0.0, "maximum": 1.0},
    "last_harness_date":           {"type": "string", "format": "date-time"},
    "first_staleness_detected_at": {"oneOf": [{"type":"null"},
                                              {"type":"string","format":"date-time"}]}
  }
}
```

**Cross-reference checks:**
- Check #3: §A `system_name` + `owner_agent` + `escalation_contact` must match §J (authoritative). Divergence is FAIL naming §J as source of truth.
- Check #4: §A `linter_version` must match §K.0 `linter_version`.

#### 4.4.11 §K Conformance — fenced YAML block

    ```yaml conformance
    linter_version: 1.0.0
    last_lint_run: S487 / 2026-04-21T17:35:00Z
    last_lint_result: PASS
    trace_matrix_path: null
    word_count_delta: null
    ```

**§K.0 note:** the `linter_version` field in this block is authoritative (§K.0 of Gate 1 spec). §A is a display mirror; any divergence is check #4 FAIL naming §K.0 as source of truth.

**Retrofit fields:**
- `trace_matrix_path` and `word_count_delta` required non-null if the runbook is a retrofit. Retrofit status is declared by presence of a `retrofit: true` key at the top of the §K block (optional default `false`). If `retrofit: true` and either trace_matrix_path or word_count_delta is null, check #18 FAIL.

### 4.5 Cross-reference validation

Implemented by `lint/checks.py` checks #3, #4, #8, #9, #10. All follow the same pattern: extract source field, extract target collection, assert source ∈ target collection (or some field-equality predicate), emit FAIL with specific message if violated. Unit tests exist one-per-check in `tests/test_checks.py`.

### 4.6 STALE predicate evaluation + grace workflow

Implemented in `lint/staleness.py:evaluate_staleness(sections, now, git_head)`. Returns `(is_stale: bool, triggered_predicates: list[str], new_first_detected_at: str | None)`.

**Pseudocode** (faithful to Gate 1 §4 §J):

```python
def evaluate_staleness(sections, now, git_head):
    j = sections["J"].form
    k_01 = sections["B"].unverified_overlay_rows  # from check #7 pass

    predicates_triggered = []

    # Predicate 1: commit drift + date threshold
    commit_drift = (j["last_refresh_commit"] != git_head)
    date_expired = (now - parse(j["last_refresh_date"])) > timedelta(days=60)
    if commit_drift and date_expired:
        predicates_triggered.append("commit_drift_60d")

    # Predicate 2: harness age
    if (now - parse(j["last_harness_date"])) > timedelta(days=90):
        predicates_triggered.append("harness_90d")

    # Predicate 3: any unverified §B row
    if k_01:
        predicates_triggered.append("unverified_b_rows")

    is_stale = len(predicates_triggered) > 0

    prev_first = j["first_staleness_detected_at"]
    if is_stale and prev_first is None:
        new_first = now.isoformat()
    elif not is_stale and prev_first is not None:
        new_first = None  # clear grace clock only when all predicates fall
    else:
        new_first = prev_first

    return is_stale, predicates_triggered, new_first
```

**Emission behavior** (check #15):
- `is_stale == True` AND `now - first_staleness_detected_at <= 30 days`: emit WARN
- `is_stale == True` AND `now - first_staleness_detected_at > 30 days`: emit FAIL
- `is_stale == False`: no finding; if the runbook's on-disk §J has a non-null `first_staleness_detected_at`, emit INFO ("grace clock would be cleared on next refresh commit")

**Linter-does-not-write policy:** The linter does NOT modify the runbook to clear the grace clock. Clearing happens when the runbook author commits an updated §J (`last_refresh_*` fields refreshed) AND the re-evaluation predicates are all false. Check #15 is evaluated against the committed §J; the linter reports the state, the author controls the state.

### 4.7 CLI output formats

**`--format text`** (default, local dev):

```
ai-market-backend.md: FAIL (2 errors, 1 warning)
  [FAIL check-01] Missing §G section
  [FAIL check-09] §F-03 Repair Ref "§G-02" does not resolve to any §G id
  [WARN check-07] §B row "Webhook retries" Last Verified older than 90 days

crm-target-state.md: PASS (3 warnings)
  [WARN check-07] §B row "Composite skills" Last Verified empty
  …

Summary: 1 runbook PASS, 1 runbook FAIL (2 errors, 4 warnings total)
```

**`--format json`** (programmatic consumers):

```json
{
  "linter_version": "1.0.0",
  "runs": [
    {"path": "ai-market-backend.md",
     "result": "FAIL",
     "findings": [
       {"check": 1, "severity": "FAIL", "message": "missing §G section",
        "line": null, "hint": "add ## §G. Repair between §F and §H"},
       {"check": 9, "severity": "FAIL", "message": "§F-03 Repair Ref \"§G-02\" does not resolve",
        "line": 143, "hint": "create §G-02 repair entry, or clear the Repair Ref cell"}
     ]}
   ],
  "summary": {"pass": 1, "fail": 1, "warn_total": 4, "error_total": 2}
}
```

**`--format github`** (CI annotations):

```
::error file=ai-market-backend.md,line=143::[check-09] §F-03 Repair Ref "§G-02" does not resolve to any §G id
::warning file=ai-market-backend.md::[check-07] §B row "Webhook retries" Last Verified older than 90 days
```

GitHub Actions renders these as inline PR annotations on the offending lines.

### 4.8 Version compatibility matrix

`runbook_tools/version.py`:

```python
LINTER_VERSION = "1.0.0"
# (major, minor): supported_standard_versions
COMPATIBILITY_MATRIX = {
    (1, 0): ["1.0"],
    # future: (1, 1): ["1.0", "1.1"],
    #         (2, 0): ["2.0"],
}
```

**Standard version** is declared at the top of the Gate 1 spec (new field added at Chunk 1 merge):

```markdown
## Standard version: 1.0
```

**Behavior when runbook's §A `linter_version` does not match `LINTER_VERSION`:**
- If runbook's major+minor is listed in `COMPATIBILITY_MATRIX[(LINTER_VERSION major, minor)]`: no finding.
- If not listed: check #16 WARN `runbook validated against unsupported standard version`.

**Behavior on a major version bump:** A new `COMPATIBILITY_MATRIX` entry is added; old runbooks continue to emit only WARN until they re-validate. No auto-migration. Migration paths are documented in a future Gate 2 amendment.

### 4.9 CI integration — `runbook-lint.yml`

**Trigger:** `pull_request` on paths `['*.md', 'runbook_tools/**', 'schemas/**']`.

**Workflow steps:**

```yaml
name: runbook-lint
on:
  pull_request:
    paths: ['*.md', 'runbook_tools/**', 'schemas/**']
jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: {python-version: '3.11'}
      - name: Install
        run: pip install -e .
      - name: Lint conformant runbooks (strict)
        run: runbook-lint --mode strict --format github
      - name: Lint in-progress runbooks (probationary)
        run: runbook-lint --mode probationary --format github || true
```

**Mode derivation:** the `--mode` flag selects which runbooks to lint based on README §7 status:
- `strict`: paths with status `CONFORMANT` (exit code propagates; FAIL blocks PR)
- `probationary`: paths with status `GATE_1_IN_PROGRESS` or `GATE_2_IN_PROGRESS` (exit code suppressed; findings surface as PR comments)
- `legacy`: paths with status `LEGACY_NOT_UNDER_STANDARD` (skipped)

**PR-blocking contract:** the `strict` step's exit code is authoritative. The `probationary` step never blocks.

---

## 5. Template validator (`runbook-new`)

### 5.1 CLI

```
runbook-new <system-name> [--owner AGENT] [--dry-run]

  system-name       Lowercase, dash-separated. Must match pattern [a-z0-9][a-z0-9-]*[a-z0-9]
  --owner AGENT     Pre-fill §A.owner_agent and §J.owner_agent. Default: max
  --dry-run         Print to stdout; do not write file.
```

Writes `<system-name>.md` at repo root. Refuses to overwrite existing files.

### 5.2 Placeholder token format

All placeholders are of form `<<TOKEN:kind>>` where `kind` ∈ {`required`, `optional`, `example`}. The linter recognizes placeholders:

- `kind=required` (unfilled) → check #19 FAIL (§A required-fields check) with message "placeholder not filled: <<TOKEN>>"
- `kind=example` → WARN ("example text; replace before conformance")
- `kind=optional` → no finding

Example placeholder in the template:

```yaml
---
system_name: <<SYSTEM_NAME:required>>
purpose_sentence: <<PURPOSE:required>>
owner_agent: <<OWNER:required>>
escalation_contact: <<ESCALATION:required>>
lifecycle_ref: §J
authoritative_scope: <<AUTHORITATIVE_SCOPE:required>>
linter_version: 1.0.0
---
```

### 5.3 WARN vs FAIL derivation rules

- A scaffold generated by `runbook-new` passes check #1 (sections present), #2 (agent forms present), #14 (§J fields populated with placeholders that parse as strings), #17 (§K fields populated).
- It FAILs check #19 and #20 where placeholders exist in required positions (by design, until the author fills them).
- A fully filled-in runbook with no placeholders passes all checks.

### 5.4 Template structure

`templates/runbook.template.md` contains the full §A–§K structure with `<<…:required>>` placeholders in every required field and `<<…:example>>` in every optional-with-example field. The §B/§C/§D tables are single-row examples with `<<…:example>>` values. §E/§G/§I YAML blocks contain one example entry each. §H.1–§H.6 sub-headings are present with placeholder bullets. §J and §K blocks have all required keys with placeholders.

---

## 6. Stateless-agent harness

### 6.1 Scenario YAML grammar

Scenarios live in `harness/scenarios/<system-name>/<scenario-id>.yaml`. One file per scenario.

```yaml
# harness/scenarios/infisical-secrets/I-01.yaml
id: I-01
runbook: infisical-secrets.md
type: operate
refs: [E-01]
scenario: |
  A support engineer reports "missing secret in prod frontend deploy for path api/keys/stripe".
  The first action is to verify the secret exists at that path in the prod environment.
expected_answers:
  - kind: tool_call
    tool: infisical secrets get
    argument_keys: [project-id, env, path]
    argument_values:
      env: prod
      path: api/keys/stripe
  - kind: tool_call
    tool: runbook_tools.secrets.read_secret
    argument_keys: [env, path]
    argument_values:
      env: prod
      path: api/keys/stripe
weight: 0.10
notes: |
  Both CLI and library invocations are acceptable first actions.
```

**JSON Schema** (`schemas/scenario.schema.json`) matches 4.4.9 `§I` structure plus two harness-only fields:
- `runbook` — path (relative to repo root) of the target runbook
- `notes` — optional commentary, not fed to MP

Section §I in the runbook is the authoritative scenario *set* (IDs + weights). The per-file YAMLs in `harness/scenarios/<s>/` are the authoritative scenario *content* (prose + expected_answers). The harness cross-validates: every §I `id` must have a matching YAML file and vice versa. Missing file or missing §I entry is a harness-time FAIL (surfaces via the nightly workflow, not `runbook-lint`).

### 6.2 Expected-answer key format

Three answer kinds:

**1. `tool_call`**
```yaml
kind: tool_call
tool: <exact-tool-name>                     # matched case-sensitive exact
argument_keys: [key1, key2]                 # set equality required
argument_values:                            # optional; when present, values matched per rubric
  key1: <expected value>                    # string equality, or regex if wrapped in /.../, or {any_of: […]}
```

**2. `human_action`**
```yaml
kind: human_action
verb: <canonical action verb>                 # see 6.4.3 canonical verb list
object: <noun>
target: <target subsystem or resource>
```

**3. `classification`**
```yaml
kind: classification
verdict: SAFE | REVIEW | BREAKING              # for §H Evolve scenarios
```

### 6.3 MP dispatch invocation

Implemented in `harness/runner.py:dispatch_for_scenario(scenario, runbook_path)`.

Uses Koskadeux MCP `council_request(agent=mp, mode=review, …)` with:
- `allowed_tools = ["Read", "Grep", "Glob", "LS"]`
- Tool scope restricted to the runbook path (via system prompt + tool-use instructions; MP honors this by convention — enforcement is a best-effort constraint since MP can technically access other files, but the prompt explicitly instructs not to)
- Timeout: 180s per scenario
- Single attempt per scenario per run (retries handled at the nightly-workflow level, not per scenario)

**System prompt preamble** (fixed, version-controlled in `runbook_tools/harness/prompts.py`):

```
You are evaluating a runbook for stateless-agent legibility. You have access only to
Read, Grep, Glob, and LS tools restricted to the file <runbook_path>. You have no prior
context about this system. Given the scenario below, produce your first action.

Your first action is either:
  (a) a tool call — specify the tool name and argument key-value pairs
  (b) a human instruction — specify the verb, object, and target
  (c) a classification verdict (only for §H Evolve scenarios): SAFE, REVIEW, or BREAKING

Output ONLY a JSON object matching this schema:
  {"kind": "tool_call", "tool": "...", "arguments": {...}}
  OR
  {"kind": "human_action", "verb": "...", "object": "...", "target": "..."}
  OR
  {"kind": "classification", "verdict": "SAFE|REVIEW|BREAKING"}

No prose. No markdown fences. One JSON object.
```

**Rationale for enforced JSON output:** the scorer needs a reliably parseable response. Prose responses would require another agent to normalize, expanding failure surface. JSON constraints are within MP's capability.

### 6.4 Scoring algorithm

Implemented in `harness/scorer.py:score_response(response, scenario)`. Returns `(score: float, matched_answer_index: int | None, reason: str)`.

#### 6.4.1 Tool-call matching

For each `expected_answers[i]` of `kind: tool_call`:
1. Normalize tool name: `lower(strip(tool))`. Compare to response's normalized tool.
2. If tool names match: compare `set(argument_keys)` to `set(response.arguments.keys())`. Must be equal.
3. If `argument_values` present for any key `k`: apply value-matching rubric to `response.arguments[k]`:
   - If expected is a plain string: exact match after `strip`.
   - If expected is `/regex/`: regex match.
   - If expected is `{any_of: [v1, v2, …]}`: one of the values matches.
4. Score:
   - All above pass → **1.0**
   - Tool name + argument key-set match; value-matching partially fails (N of M values wrong) → **0.5** (partial credit, mirrors Gate 1 §I rubric)
   - Tool name matches but argument key-set differs → **0.5**
   - Tool name does not match → continue to next expected answer

If no expected answer matches: **0.0**.

#### 6.4.2 Human-action matching

Normalize verb via the canonical-verb list (§6.4.3). Normalize object by stripping articles (`the`, `a`, `an`) and lowercasing. Normalize target similarly.
- Verb + object + target all match → 1.0
- Verb + object match, target differs → 0.5
- Verb matches, object differs → 0.0

#### 6.4.3 Canonical verb list

```python
CANONICAL_VERBS = {
    "run":        ["execute", "invoke", "trigger"],
    "restart":    ["reboot", "bounce", "cycle"],
    "read":       ["fetch", "get", "retrieve", "look up"],
    "write":      ["set", "update", "create", "push", "upload"],
    "delete":     ["remove", "destroy", "clear"],
    "rotate":     [],
    "escalate":   ["page", "alert", "notify"],
    "verify":     ["check", "confirm", "validate"],
    "search":     ["grep", "find", "locate"],
}
```

Verb matching canonicalizes synonyms to the key. Unknown verbs match only themselves (case-insensitive).

#### 6.4.4 Classification matching

Exact case-sensitive match on verdict. No partial credit for §H (SAFE/REVIEW/BREAKING is trinary, not a spectrum).

### 6.5 Partial-credit detection

Already embedded in §6.4. The scorer returns a float in `{0.0, 0.5, 1.0}`. Scenario scores multiply by `weight`; pass threshold is sum ≥ 0.80.

### 6.6 Result output format

`harness/results/<system-name>/<session-id>-<date>.json`:

```json
{
  "session_id": "S487",
  "runbook": "infisical-secrets.md",
  "linter_version": "1.0.0",
  "standard_version": "1.0",
  "run_started_at": "2026-04-22T02:00:00Z",
  "run_finished_at": "2026-04-22T02:03:14Z",
  "scenarios": [
    {"id": "I-01", "weight": 0.10,
     "response": {"kind": "tool_call", "tool": "infisical secrets get",
                  "arguments": {"project-id": "…", "env": "prod", "path": "api/keys/stripe"}},
     "score": 1.0,
     "matched_answer_index": 0,
     "reason": "exact_tool_and_value_match"},
    …
  ],
  "aggregate_score": 0.92,
  "pass_threshold": 0.80,
  "result": "PASS"
}
```

### 6.7 Nightly CI — `runbook-harness.yml`

```yaml
name: runbook-harness
on:
  schedule:
    - cron: '0 7 * * *'   # 02:00 EST = 07:00 UTC
  workflow_dispatch:

jobs:
  harness:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: {python-version: '3.11'}
      - run: pip install -e .
      - name: Run harness against all conformant runbooks
        env:
          KOSKADEUX_MCP_URL:   ${{ secrets.KOSKADEUX_MCP_URL }}
          KOSKADEUX_MCP_TOKEN: ${{ secrets.KOSKADEUX_MCP_TOKEN }}
        run: runbook-harness --mode conformant --session "CI-$(date -u +%Y%m%d)"
      - name: Commit results
        run: |
          git config user.name "runbook-harness"
          git config user.email "noreply@ai.market"
          git add harness/results/
          git commit -m "harness: nightly $(date -u +%Y-%m-%d)" || exit 0
          git push
```

**Result retention:** results are committed to the repo (git history is the archive). `harness/results/<s>/` grows indefinitely; retention trimming is deferred to a follow-on chunk. 30 days of nightly runs = 30 small JSON files per system = negligible size. Trim policy TBD after 6 months of data.

**Failure handling:** if the harness workflow fails (MCP unreachable, MP times out on every scenario, etc.), the failure is logged but does not block any PR. The result file records `"result": "INFRASTRUCTURE_FAILURE"` with the root cause. A follow-on failure → alert wiring is a deferred concern.

---

## 7. Runbook index — `README.md`

### 7.1 Structure

```markdown
# ai.market Runbooks

This repository is the source of truth for every system-level runbook in ai.market.
Every runbook conforms to the standard defined in `specs/BQ-RUNBOOK-STANDARD.md`
(standard version 1.0).

## Adoption status

| System | Runbook | Status | Gate | Linter | Harness | Owner |
|---|---|---|---|---|---|---|
| Infisical Secrets | [infisical-secrets.md](infisical-secrets.md) | CONFORMANT | gate4_passed | PASS | 0.92 (2026-04-22) | sysadmin |
| AIM Node          | [aim-node.md](aim-node.md)                    | GATE_1_IN_PROGRESS | gate1_r2 | — | — | vulcan |
| CRM               | [crm-target-state.md](crm-target-state.md)    | RETROFIT_CANDIDATE | — | — | — | crm_steward |
| ai-market-backend | [ai-market-backend.md](ai-market-backend.md)  | LEGACY_NOT_UNDER_STANDARD | — | — | — | max |
…

## Status values

- `NOT_STARTED` — adoption planned, no BQ filed
- `GATE_1_IN_PROGRESS` — runbook BQ open at Gate 1
- `GATE_1_APPROVED` — Gate 1 passed, Gate 2 not yet open
- `GATE_2_IN_PROGRESS` — Gate 2 authoring and build
- `GATE_3_IN_PROGRESS` — code audit underway
- `GATE_4_IN_PROGRESS` — production verification
- `CONFORMANT` — all four gates passed, lint + harness passing
- `RETROFIT_CANDIDATE` — pre-existing runbook needs structural rework (content stays valid)
- `LEGACY_NOT_UNDER_STANDARD` — predates the standard, not on adoption roadmap
- `DEPRECATED` — system is being retired; runbook kept for history

## Working on a runbook

- Create a new runbook: `runbook-new <system-name>`
- Validate a runbook: `runbook-lint <path>`
- Run the harness locally: `runbook-harness --runbook <path>`

…
```

### 7.2 Status values

As listed in §7.1. Authoritative.

### 7.3 Update contract

- The `README.md` index is hand-maintained by the Vulcan authoring each Gate transition — the Gate N → Gate N+1 commit includes a README row update.
- The linter parses README in `--mode` derivation. A status field not listed in §7.2 is a CLI error (exit 2, infrastructure fault).
- Harness score column is auto-updated by the nightly workflow commit. Linter column is auto-updated by the PR workflow on main branch pushes.
- Drift between README and actual per-runbook §J lifecycle block is NOT validated in Chunk 1 (deferred).

---

## 8. Dependencies and runtime

### 8.1 `pyproject.toml`

```toml
[project]
name = "runbook-tools"
version = "1.0.0"
requires-python = ">=3.11"
dependencies = [
    "mistune>=3.0,<4",
    "pyyaml>=6.0,<7",
    "jsonschema>=4.20,<5",
    "click>=8.1,<9",
    "python-dateutil>=2.8,<3",
]

[project.optional-dependencies]
dev = ["pytest>=7.4", "pytest-cov>=4.1", "ruff>=0.2"]

[project.scripts]
runbook-lint     = "runbook_tools.cli:lint_cmd"
runbook-new      = "runbook_tools.cli:new_cmd"
runbook-harness  = "runbook_tools.cli:harness_cmd"
```

### 8.2 Python version

3.11. Matches the ai-market-backend target. No 3.12+ features used.

### 8.3 External service calls

Only the harness touches external services (Koskadeux MCP for MP dispatch). The linter and scaffold are pure-local.

---

## 9. Test suite — Gate 3 acceptance criteria

Gate 3 code audit will verify the following are implemented and passing:

**Linter checks** (one pytest per check):
- `tests/test_checks.py::test_check_01_sections_present_and_ordered` — conformant fixture passes; missing-§G fixture FAILs; out-of-order fixture FAILs
- `test_check_02_agent_forms_present` — conformant passes; missing-§B-table FAILs
- `test_check_03_a_j_consistency` — divergent header/lifecycle FAILs
- `test_check_04_a_k0_consistency` — linter_version mismatch FAILs
- `test_check_05_status_values` — `WORKING` (non-canonical) FAILs
- `test_check_06_backing_code` — SHIPPED row with `—` backing FAILs
- `test_check_07_last_verified_warn` — empty Last Verified emits WARN (not FAIL)
- `test_check_08_repair_ref_resolves` — dangling §G-02 FAILs
- `test_check_09_symptom_ref_resolves` — §G entry with unknown F-ref FAILs
- `test_check_10_component_ref_resolves` — §G entry with unknown component FAILs
- `test_check_11_scenario_distribution` — 9 scenarios FAILs; 10 scenarios with no ambiguous FAILs
- `test_check_12_weights_sum` — weights summing 0.99 FAILs
- `test_check_13_unequal_weights_justified` — unequal weights without §I.1 FAILs
- `test_check_14_lifecycle_fields` — missing `last_harness_date` FAILs
- `test_check_15_staleness_grace_workflow` — covers transition `false → true` (WARN emitted, first_staleness_detected_at logged); 30-day threshold (FAIL emitted); grace clear on all-predicates-false (INFO emitted)
- `test_check_16_linter_version_compat` — future-standard WARN
- `test_check_17_conformance_fields` — missing `last_lint_run` FAILs
- `test_check_18_retrofit_fields` — retrofit=true with null trace_matrix FAILs
- `test_check_19_header_required_fields` — missing `escalation_contact` FAILs; unfilled `<<…:required>>` placeholder FAILs
- `test_check_20_b_exact_columns` — mis-ordered or renamed column FAILs

**Staleness workflow integration tests** (`test_staleness.py`):
- All three STALE predicates fire independently and in combination
- Grace clock: starts null, sets on first stale, preserves across lints while stale, clears only when all predicates fall
- 30-day threshold produces WARN → FAIL transition

**Scaffold tests** (`test_scaffold.py`):
- `runbook-new foo` produces a file that passes checks #1, #2, #14, #17 and FAILs checks #19, #20 (because of `<<…:required>>` placeholders in §A required fields and §B example row)
- Filling all required placeholders manually produces a PASS
- `runbook-new` on an existing path errors out

**Harness tests** (`test_harness_loader.py`, `test_harness_scorer.py`):
- Scenario YAML with missing required field FAILs validation
- Response with matching tool + matching argument keys + matching values → score 1.0
- Response with matching tool + matching argument keys + 1 wrong value out of 3 → score 0.5
- Response with matching tool + extra argument key → score 0.5
- Response with non-matching tool → score 0.0 (tries remaining expected answers)
- Response with `kind=classification` + verdict mismatch → score 0.0
- Human-action: "restart the gateway" matches expected (`reboot`, `gateway`, `gateway`) via canonical-verb normalization

**Integration test** (`test_integration.py`):
- A conformant fixture runbook with all §A–§K lints PASS and a 10-scenario harness set scores ≥ 0.80 against a stubbed MP responder that emits the expected first answer for each scenario.

**Coverage target:** pytest-cov ≥ 90% line coverage on `runbook_tools/`.

**Runbook-lint self-test:** `runbook-lint --format json tests/fixtures/conformant.md` exit 0 + `"result": "PASS"` in output. Enforced in the CI workflow pre-merge.

---

## 10. Gate boundaries (Gate 2 vs Gate 3 for this chunk)

**Gate 2 (this spec) delivers design:**
- Exact CLI argument shapes for `runbook-lint`, `runbook-new`, `runbook-harness`
- Exact grammar per agent form (markdown-table columns, YAML-block key sets, JSON Schema)
- Exact check algorithm per §K.1 item (20 checks)
- Exact scoring algorithm for the harness (partial-credit rules, canonical verbs, matching order)
- Exact repository layout
- Exact CI workflow structure
- Exact test-suite acceptance criteria per check/test
- Exact dependency list (pyproject.toml)

**Gate 3 (code audit, post-build) delivers:**
- Linter and scaffold executables installed and invocable locally
- All 20 checks implemented with associated pytest suite passing
- All 5 harness test scenarios (loader, scorer, tool-match, human-action, classification) passing
- Integration test end-to-end green on a fixture runbook
- Both GitHub Actions workflows pass on the PR introducing this chunk
- Coverage ≥ 90% on `runbook_tools/`
- No dependencies outside §8.1

**Gate 4 (production verification) delivers:**
- First PR to `aidotmarket/runbooks` after Chunk 1 merge is blocked by a seeded conformance failure in a probationary fixture; fix lands, CI passes. Evidence: PR number + failure screenshot + fix commit.
- First harness nightly run produces a result file committed to `harness/results/` by the `runbook-harness` GitHub actor. Evidence: commit link.

---

## 11. Chunk 2 preview

Chunk 2 will be filed as a separate spec (`BQ-RUNBOOK-STANDARD-GATE-2-CHUNK-2.md`) with Gate 2 authoring starting after this Chunk 1 merges to main. Chunk 2 scope:

- **D4 Infisical runbook** — authored from scratch by Vulcan, validated by `runbook-lint` from Chunk 1. First exercise of the standard end-to-end. Must score ≥ 0.80 on its own §I harness set.
- **D5 AIM Node runbook** — G4 falsifiability test per Gate 1 §7. Authored against the frozen standard (commit `365c198`) with no access to the Infisical reference. Evaluated on a hidden scenario set authored by MP + AG.

Chunk 2 does NOT re-open Gate 1 of the parent BQ. It is a follow-on Gate 2 spec chunk on the same BQ entity. Living State version increments; gate status stays `gate2_in_progress` until Chunk 2 merges, at which point the parent BQ transitions to `gate3_in_progress` (code audit of this Chunk 1's tooling + the two Chunk 2 runbooks).

---

## 12. Open questions for reviewers (R1 only)

1. **Markdown parser choice.** Is `mistune>=3.0` acceptable? Alternative: `marko`, `markdown-it-py`. Preferred for table+YAML-frontmatter support, pure-Python, AST access. MP/AG review should flag if a specific parser is known to mis-handle GFM tables.

2. **Canonical verb list scope.** §6.4.3 has 9 entries. Is this sufficient coverage for likely §E Operate scenarios? Over-specified verbs risk false positives; under-specified ones risk false negatives. Propose: keep the list as-is for Chunk 1; expand via Chunk 2 experience.

3. **Harness committing results to the repo.** §6.7 commits nightly results to `harness/results/`. Alternative: post to S3/R2 with a summary commit, or a GitHub artifact. Git-in-repo is simplest and traceable; retention trimming deferred. MP/AG review: is this acceptable Chunk 1 scope or should results go to object storage from the start?

4. **Probationary mode PR comments vs annotations.** §4.9 uses `continue-on-error: true` pattern for probationary lint. Does the default GitHub annotations surface properly for a non-blocking job? Alternative: explicit PR comment via GitHub API. Defer implementation detail to Gate 3 but flag now if the shape is wrong.

5. **Standard version declaration.** §4.8 introduces a "standard version" as a new field to be added at the top of the Gate 1 spec. This is a minor amendment to the Gate 1 APPROVED spec. Acceptable? Or should standard versioning be deferred to a future Gate 1 amendment?

---

## Appendix A: Mapping Chunk 1 deliverables to Gate 1 §9 order

| Gate 1 §9 Deliverable | Chunk 1 Section | Repo Artifact |
|---|---|---|
| D1 runbook-lint + template validator | §4 + §5 | `runbook_tools/lint/`, `runbook_tools/scaffold/`, `schemas/`, `templates/` |
| D2 stateless-agent harness scaffold | §6 | `runbook_tools/harness/`, `harness/scenarios/`, `harness/results/` |
| D3 runbook index README | §7 | `README.md` |

## Appendix B: Dependencies on Gate 1 spec sections

| Chunk 1 Section | Gate 1 Spec Dependency |
|---|---|
| §4.4 Agent-form grammars | Gate 1 §4 §A–§K (prescribed forms) |
| §4.3, §4.5 Linter checks | Gate 1 §4 §K.1 (checks #1–#20) |
| §4.6 Staleness | Gate 1 §4 §J (STALE predicates, grace workflow) |
| §4.8 Version compatibility | Gate 1 §4 §K.0 (authoritative linter_version) |
| §5 Template validator | Gate 1 §4 §K.3 |
| §6 Harness | Gate 1 §4 §K.2 + §4 §I (scoring rubric, equal-weight default) |
| §7 Runbook index | Gate 1 §2 (scope), §9 (deliverable order) |
| §10 Gate boundaries | Gate 1 §12 (Gate 1 vs Gate 2) |
| §11 Chunk 2 preview | Gate 1 §9 steps 4–5 |
