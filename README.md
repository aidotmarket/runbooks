# ai.market runbooks

Operational pages live at the repository root and in `runbooks/`. Older pages that are still useful for history live in `archive/` and are marked archived in `INDEX.md`.

Find a page by browsing `INDEX.md`, looking up a literal failure in `ERRORS.md`, or searching the Markdown directly. Edit the relevant page in place. Keep its five frontmatter fields and operational prose accurate, and give every current page a `## When it breaks` section. If no break/fix procedure applies, say so plainly instead of inventing one.

After editing, run:

```sh
python3 scripts/index.py
python3 scripts/check.py
git diff --exit-code -- INDEX.md ERRORS.md
```

Max's standing W4 rule: do not add runbook tooling, schemas, lint rules, promotion systems, or authority categories without Max's explicit recorded decision. Runbook work means writing or correcting runbooks. This is guidance, not an enforcement gate.
