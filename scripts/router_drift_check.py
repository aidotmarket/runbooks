#!/usr/bin/env python3
"""Router drift guard (BQ-RUNBOOK-TOPIC-ROUTER-AND-STANDARD-S740, mandate M3).
Asserts: (a) every runbook .md at repo root is referenced in TOPIC-ROUTER.md;
(b) every router link target file+anchor resolves (anchor = GitHub heading slug);
(c) the router carries a Credentials / Source-of-Truth section.
No graph validation, embeddings, or misroute heuristics. Exit 1 on any failure."""
import re, sys, glob, os
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROUTER = os.path.join(ROOT, "TOPIC-ROUTER.md")
EXCLUDE = {"README.md", "TOPIC-ROUTER.md"}

def gh_slug(h):
    s = h.strip().lower()
    s = re.sub(r"[^\w\- ]+", "", s)   # drop chars GitHub drops (. § — : ( ) etc.)
    return s.replace(" ", "-")

def main():
    if not os.path.exists(ROUTER):
        print("FAIL: TOPIC-ROUTER.md missing"); return 1
    router = open(ROUTER, encoding="utf-8").read()
    errs = []
    runbooks = [os.path.basename(p) for p in glob.glob(os.path.join(ROOT, "*.md"))
                if os.path.basename(p) not in EXCLUDE]
    for rb in sorted(runbooks):
        if rb not in router:
            errs.append(f"COVERAGE: {rb} not referenced in TOPIC-ROUTER.md")
    for m in re.finditer(r"\]\(([A-Za-z0-9._\-]+\.md)(?:#([^)]+))?\)", router):
        f, anchor = m.group(1), m.group(2)
        fp = os.path.join(ROOT, f)
        if not os.path.exists(fp):
            errs.append(f"DEADLINK: {f}"); continue
        if anchor:
            heads = re.findall(r"(?m)^#{1,6}\s+(.*)$", open(fp, encoding="utf-8").read())
            if anchor not in {gh_slug(h) for h in heads}:
                errs.append(f"DEADANCHOR: {f}#{anchor}")
    if not re.search(r"(?im)^#{2,}\s+.*(credential|source.?of.?truth)", router):
        errs.append("M1: router missing a Credentials / Source-of-Truth section")
    if errs:
        print("ROUTER DRIFT CHECK: FAIL")
        for e in errs: print("  -", e)
        return 1
    print(f"ROUTER DRIFT CHECK: PASS ({len(runbooks)} runbooks covered)")
    return 0

if __name__ == "__main__":
    sys.exit(main())
