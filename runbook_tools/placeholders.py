from __future__ import annotations

import re

# Any bounded complete `<<...>>` token in current content is unresolved,
# regardless of a legacy suffix such as `required`, `example`, or `optional`.
# The second and third alternatives catch scaffold-shaped tokens with one
# missing delimiter or a malformed suffix. Requiring a `:`/`-` separator after
# the uppercase placeholder name avoids treating normal shell heredocs
# (`<<'PY'`, `<<PY`, or `<<END_JSON`) as placeholders.
UNRESOLVED_PLACEHOLDER_RE = re.compile(
    r"<<[^<>\n]{1,256}>>"
    r"|<<[A-Z][A-Z0-9_-]{0,63}[:-][A-Za-z0-9_-]{1,64}"
    r"(?:>(?!>)|(?=\s|$))"
    r"|(?<!<)<[A-Z][A-Z0-9_-]{0,63}[:-][A-Za-z0-9_-]{1,64}>>"
)
