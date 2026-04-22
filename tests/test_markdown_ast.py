from __future__ import annotations

from runbook_tools.parser.markdown_ast import parse_markdown, walk_tokens


def test_parse_markdown_returns_table_ast() -> None:
    tokens = parse_markdown(
        "| A | B |\n"
        "|---|---|\n"
        "| 1 | 2 |\n"
    )

    assert any(token["type"] == "table" for token in tokens)


def test_walk_tokens_recurses_and_skips_non_list_children() -> None:
    tokens = [
        {
            "type": "root",
            "children": [
                {"type": "leaf", "raw": "x"},
                {"type": "non-list-child", "children": "ignore-me"},
            ],
        },
        {"type": "standalone"},
    ]

    walked = [(token["type"], depth) for token, depth in walk_tokens(tokens)]

    assert walked == [
        ("root", 0),
        ("leaf", 1),
        ("non-list-child", 1),
        ("standalone", 0),
    ]
