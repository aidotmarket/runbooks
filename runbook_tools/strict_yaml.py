from __future__ import annotations

from typing import Any

import yaml
from yaml.constructor import ConstructorError
from yaml.nodes import MappingNode
from yaml.resolver import BaseResolver
from yaml.tokens import AliasToken, AnchorToken


class UniqueKeySafeLoader(yaml.SafeLoader):
    """PyYAML safe loader that rejects every duplicate mapping key."""


def _construct_unique_mapping(
    loader: UniqueKeySafeLoader,
    node: MappingNode,
    deep: bool = False,
) -> dict[Any, Any]:
    loader.flatten_mapping(node)
    mapping: dict[Any, Any] = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        try:
            duplicate = key in mapping
        except TypeError as exc:
            raise ConstructorError(
                "while constructing a mapping",
                node.start_mark,
                "found an unhashable key",
                key_node.start_mark,
            ) from exc
        if duplicate:
            raise ConstructorError(
                "while constructing a mapping",
                node.start_mark,
                f"found duplicate key {key!r}",
                key_node.start_mark,
            )
        mapping[key] = loader.construct_object(value_node, deep=deep)
    return mapping


UniqueKeySafeLoader.add_constructor(
    BaseResolver.DEFAULT_MAPPING_TAG,
    _construct_unique_mapping,
)


def strict_yaml_load(source: str) -> Any:
    """Parse one YAML document without aliases or last-key-wins ambiguity."""

    for token in yaml.scan(source):
        if isinstance(token, (AnchorToken, AliasToken)):
            raise ConstructorError(
                "while scanning strict YAML",
                token.start_mark,
                "anchors and aliases are not allowed",
                token.start_mark,
            )

    return yaml.load(source, Loader=UniqueKeySafeLoader)
