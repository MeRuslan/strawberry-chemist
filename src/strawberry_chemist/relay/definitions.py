from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional, Protocol, Sequence

import strawberry


@strawberry.interface
class Node:
    id: strawberry.ID


class RelayIdCodec(Protocol):
    def encode(self, node_name: str, values: tuple[str, ...]) -> str: ...

    def decode(
        self,
        token: str,
        *,
        node_names: Optional[Sequence[str]] = None,
    ) -> tuple[str, tuple[str, ...]]: ...


@dataclass(frozen=True)
class NodeDefinition:
    graphql_type: type[Any]
    model: type[Any]
    node_name: str
    ids: tuple[str, ...]
    codec: RelayIdCodec
    has_custom_codec: bool = False


@dataclass(frozen=True)
class DecodedNodeId:
    node_type: type[Any]
    node_name: str
    values: tuple[str, ...]


@dataclass(frozen=True)
class RelaySchemaState:
    default_codec: RelayIdCodec
    definitions_by_type: dict[type[Any], NodeDefinition]
    definitions_by_name: dict[str, NodeDefinition]
