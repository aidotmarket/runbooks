from __future__ import annotations

from collections.abc import Iterator

import mistune


_MARKDOWN = mistune.create_markdown(
    renderer="ast",
    plugins=["table", "strikethrough"],
)


def parse_markdown(text: str) -> list:
    return _MARKDOWN(text)


def walk_tokens(tokens: list, depth: int = 0) -> Iterator[tuple[dict, int]]:
    for token in tokens:
        yield token, depth
        children = token.get("children")
        if isinstance(children, list):
            yield from walk_tokens(children, depth + 1)
