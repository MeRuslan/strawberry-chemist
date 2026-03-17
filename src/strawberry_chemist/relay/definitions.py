from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional, Protocol, Sequence

import strawberry

from strawberry_chemist.settings import get_default_relay_id_codec


class RelayIdCodec(Protocol):
    def encode(self, node_name: str, values: tuple[str, ...]) -> str: ...

    def decode(
        self,
        token: str,
        *,
        node_names: Optional[Sequence[str]] = None,
    ) -> tuple[str, tuple[str, ...]]: ...


@dataclass(frozen=True)
class NodeIdConfig:
    ids: Optional[tuple[str, ...]] = None
    codec: Optional[RelayIdCodec] = None


def node_id(
    *,
    ids: Optional[Sequence[str]] = None,
    codec: Optional[RelayIdCodec] = None,
) -> NodeIdConfig:
    return NodeIdConfig(
        ids=tuple(ids) if ids is not None else None,
        codec=codec,
    )


@strawberry.interface
class Node:
    id: strawberry.ID


@dataclass(frozen=True)
class NodeDefinition:
    graphql_type: type[Any]
    model: type[Any]
    node_name: str
    ids: tuple[str, ...]
    explicit_codec: Optional[RelayIdCodec] = None

    @property
    def codec(self) -> RelayIdCodec:
        codec = self.explicit_codec or get_default_relay_id_codec()
        register = getattr(codec, "register", None)
        if callable(register):
            register(model=self.model, node_name=self.node_name)
        return codec


@dataclass(frozen=True)
class DecodedNodeId:
    node_type: type[Any]
    node_name: str
    values: tuple[str, ...]


def get_attached_node_definition(node_type: type[Any]) -> Optional[NodeDefinition]:
    definition = getattr(node_type, "__chemist_node_definition__", None)
    if isinstance(definition, NodeDefinition):
        return definition
    return None
