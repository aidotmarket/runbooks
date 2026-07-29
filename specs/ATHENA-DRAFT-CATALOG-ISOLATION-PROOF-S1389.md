# ATHENA-DRAFT-CATALOG-ISOLATION-PROOF-S1389

Status: PROOF RECORDED — DRAFT isolation only  
Owner: Athena  
Session: S1389  
Evidence commit: ae7195407a2c79a6a1bf834f397ac256d27eaaee  
Reviewed mandate: CC task 83cafa22, M1  
Scope: runbooks/session-operations.md while status is DRAFT

## 1. Question and conclusion

CC required proof that the populated authoritative_for, aliases, error signatures,
and supersedes fields on a DRAFT cannot make the document canonical or retire
its live sources before promotion.

At the exact evidence commit, the answer is yes: the generator discards every
frontmatter-bearing document whose status is not exactly ACTIVE before it
constructs a catalog entry. The loader and resolver consume only catalog entries
and indexes, reject non-ACTIVE entries, and have no filesystem fallback. Therefore
session-operations cannot be served or resolved as catalog authority while its
status is DRAFT, and its supersedes value has no catalog effect.

This is a canonical-isolation statement, not an access-control statement. A
person or agent with an explicit Git path can still read the DRAFT as review
material. It cannot discover or consult it as the catalog's canonical authority.

## 2. Exact evidence set

All line references below are to
ae7195407a2c79a6a1bf834f397ac256d27eaaee.

| Artifact | Git blob SHA |
|---|---|
| runbook_tools/catalog/generator.py | 41ce6ca2808fbad48f7130ea4827b3dfb3b9d54b |
| runbook_tools/catalog/resolver.py | 5dc48b228707fceff1acdf047c40ef3e428f0754 |
| runbook_tools/catalog/validator.py | 128c17eaafedf0d3d15d4727650628e6021d6efa |
| runbooks/session-operations.md | 5337d431b65086bbc8203e2841d8c895b8e0a46f |
| CATALOG.json | f682df183831172df2b7c6d3bb975b15419ee48d |

The checkout was clean and its HEAD equalled the evidence commit when the
empirical probe in §6 ran.

## 3. Generator exclusion happens before authority metadata is read

In generator.py:56-71, build_catalog reads frontmatter, checks that an opted-in
document has a status, and executes continue at lines 69-70 whenever status is
not exactly ACTIVE. Only line 71 constructs CatalogEntry from the remaining
frontmatter.

Consequences:

1. session-operations.md is parsed because it has a runbook_id.
2. Its status is DRAFT, so line 70 skips it.
3. CatalogEntry.from_frontmatter never receives its authoritative_for, aliases,
   error signatures, or supersedes.
4. It contributes no entry to the catalog.

In generator.py:164-179, aliases, topics, and error-signature indexes are built
only by iterating the entries that survived this ACTIVE filter. A skipped DRAFT
therefore cannot contribute a lookup key indirectly.

## 4. Loader rejects non-ACTIVE entries and derives active targets from the same filter

In validator.py:141-143, active_catalog_paths rebuilds the expected catalog from
build_catalog and fails closed if committed CATALOG.json differs from ACTIVE
frontmatter.

In validator.py:148-159, every loaded entry must have status ACTIVE; any other
status raises CatalogError. The pinned validator repeats the same rule at lines
181-188.

This gives two independent barriers:

- the generator does not emit DRAFT entries; and
- the loader rejects a hand-inserted non-ACTIVE entry.

Strict lint and harness selection use active_catalog_paths, so the DRAFT also
cannot enter those canonical target sets until promotion.

## 5. Resolver has no path fallback

In resolver.py:10-17, resolve_catalog_key loads a validated catalog and creates
its runbook map only from catalog entries.

Lines 22-38 search only:

- catalog runbook ids;
- the generated alias index;
- the generated topic index; and
- the generated error-signature index.

Lines 40-41 raise CatalogError with catalog key not found when none match. The
resolver never scans Markdown paths or frontmatter after catalog load. A DRAFT
excluded by the generator therefore cannot become canonical through a resolver
fallback.

## 6. Empirical probe at the evidence commit

The probe called build_catalog(Path(".")) in memory and separately loaded the
committed catalog using git show of the evidence SHA. It did not call
generate_catalog and wrote no catalog file.

Observed result:

~~~json
{
  "clean": true,
  "head": "ae7195407a2c79a6a1bf834f397ac256d27eaaee",
  "generated_from_frontmatter": {
    "entry": false,
    "path": false,
    "alias_open": null,
    "alias_close": null,
    "topic_open": null,
    "topic_plan": null,
    "topic_close": null
  },
  "committed_catalog": {
    "entry": false,
    "path": false,
    "alias_open": null,
    "alias_close": null,
    "topic_open": null,
    "topic_plan": null,
    "topic_close": null
  }
}
~~~

The checked keys were:

- runbook id session-operations;
- path runbooks/session-operations.md;
- aliases session-open-protocol and session-close-protocol; and
- topics session-open, session-plan, and session-close.

All were absent from both the in-memory generated result and the committed
catalog.

## 7. Known catalog drift does not invalidate this proof

The evidence commit inherits unrelated drift in CATALOG.json and
TOPIC-ROUTER.md. This proof does not claim the whole committed catalog is
current or valid. It proves the narrower mandate twice:

1. rebuilding the expected catalog in memory from the exact frontmatter excludes
   this DRAFT; and
2. the committed catalog also contains none of its entry or index keys.

The unrelated drift remains untouched and belongs to its owning lane.

## 8. Promotion switch and retirement safety

The canonical switch is a reviewed content change from status DRAFT to status
ACTIVE, followed by generation of catalog surfaces through the existing tool.
Only then does generator.py line 71 construct the entry and only then can
supersedes participate in catalog metadata.

Before that switch:

- the source protocols remain live;
- the DRAFT has no catalog identity, alias, topic, signature, or supersession
  effect;
- direct reads of the DRAFT are review reads, not canonical consultation; and
- no source retirement is authorized.

The M1 mandate is therefore discharged for the DRAFT state. Promotion still
requires a valid lint verdict, coherent authority boundaries, clean reference
checks, generated-surface verification, and review of the exact final SHA.
