from __future__ import annotations

from typing import Any, Optional, Sequence, cast
from weakref import WeakKeyDictionary

import strawberry
from sqlalchemy import inspect as sa_inspect
from sqlalchemy.orm import Mapper

from .codecs import DEFAULT_ID_CODEC
from .definitions import NodeDefinition, RelayIdCodec, RelaySchemaState


_NODE_DEFINITIONS_BY_TYPE: dict[type[Any], NodeDefinition] = {}
_NODE_DEFINITIONS_BY_NAME: dict[str, NodeDefinition] = {}
_SCHEMA_STATES: WeakKeyDictionary[strawberry.Schema, RelaySchemaState] = (
    WeakKeyDictionary()
)


def get_node_definition(
    node_type: type[Any], *, schema: Optional[strawberry.Schema] = None
) -> Optional[NodeDefinition]:
    if schema is not None:
        return _get_schema_state(schema).definitions_by_type.get(node_type)
    return _NODE_DEFINITIONS_BY_TYPE.get(node_type)


def iter_node_definitions(
    *, schema: Optional[strawberry.Schema] = None
) -> tuple[NodeDefinition, ...]:
    if schema is not None:
        return tuple(_get_schema_state(schema).definitions_by_type.values())
    return tuple(_NODE_DEFINITIONS_BY_TYPE.values())


def clear_node_registry() -> None:
    _NODE_DEFINITIONS_BY_TYPE.clear()
    _NODE_DEFINITIONS_BY_NAME.clear()
    _SCHEMA_STATES.clear()


def infer_node_ids(model: type[Any]) -> tuple[str, ...]:
    mapper: Mapper[Any] = cast(Mapper[Any], sa_inspect(model))
    ids = tuple(str(column.key) for column in mapper.primary_key)
    if not ids:
        raise ValueError(f"Model {model} has no primary key columns")
    return ids


def register_node_type(
    graphql_type: type[Any],
    *,
    model: type[Any],
    ids: Optional[Sequence[str]] = None,
    codec: Optional[RelayIdCodec] = None,
    node_name: Optional[str] = None,
) -> NodeDefinition:
    resolved_name = _resolve_node_name(graphql_type, node_name)
    definition = NodeDefinition(
        graphql_type=graphql_type,
        model=model,
        node_name=resolved_name,
        ids=tuple(ids or infer_node_ids(model)),
        codec=codec or DEFAULT_ID_CODEC,
        has_custom_codec=codec is not None,
    )
    if definition.has_custom_codec:
        _register_codec(definition.codec, definition)
    _NODE_DEFINITIONS_BY_TYPE[graphql_type] = definition
    _NODE_DEFINITIONS_BY_NAME[resolved_name] = definition
    return definition


def get_existing_schema_state(schema: strawberry.Schema) -> Optional[RelaySchemaState]:
    return _SCHEMA_STATES.get(schema)


def set_schema_state(schema: strawberry.Schema, state: RelaySchemaState) -> None:
    _SCHEMA_STATES[schema] = state


def _resolve_node_name(graphql_type: type[Any], node_name: Optional[str]) -> str:
    if node_name is not None:
        return node_name

    definition = getattr(graphql_type, "__strawberry_definition__", None)
    if definition is None:
        raise ValueError(f"GraphQL type {graphql_type} is not a Strawberry type")
    return str(definition.name)


def _register_codec(codec: RelayIdCodec, definition: NodeDefinition) -> None:
    register = getattr(codec, "register", None)
    if callable(register):
        register(model=definition.model, node_name=definition.node_name)


def _resolve_definition_codec(
    definition: NodeDefinition, *, schema: Optional[strawberry.Schema] = None
) -> RelayIdCodec:
    if definition.has_custom_codec:
        return definition.codec
    if schema is None:
        return definition.codec
    state = _SCHEMA_STATES.get(schema)
    if state is None:
        return definition.codec
    return state.default_codec


def _get_schema_state(schema: strawberry.Schema) -> RelaySchemaState:
    state = _SCHEMA_STATES.get(schema)
    if state is not None:
        return state
    state = _make_schema_state(DEFAULT_ID_CODEC, _discover_schema_node_types(schema))
    _SCHEMA_STATES[schema] = state
    return state


def _make_schema_state(
    default_codec: RelayIdCodec,
    node_types: Sequence[type[Any]],
) -> RelaySchemaState:
    definitions_by_type: dict[type[Any], NodeDefinition] = {}
    definitions_by_name: dict[str, NodeDefinition] = {}
    for node_type in node_types:
        definition = _NODE_DEFINITIONS_BY_TYPE.get(node_type)
        if definition is None:
            raise ValueError(f"Node type {node_type.__name__} is not registered")
        definitions_by_type[node_type] = definition
        definitions_by_name[definition.node_name] = definition
        _register_codec(
            definition.codec if definition.has_custom_codec else default_codec,
            definition,
        )
    return RelaySchemaState(
        default_codec=default_codec,
        definitions_by_type=definitions_by_type,
        definitions_by_name=definitions_by_name,
    )


def _discover_schema_node_types(schema: strawberry.Schema) -> tuple[type[Any], ...]:
    return tuple(
        definition.graphql_type
        for definition in iter_node_definitions()
        if _schema_contains_node_type(schema, definition)
    )


def _resolve_configured_node_types(
    schema: strawberry.Schema,
    *,
    node_types: Optional[Sequence[type[Any]]] = None,
) -> tuple[type[Any], ...]:
    resolved_types: list[type[Any]] = []
    seen: set[type[Any]] = set()

    def add(node_type: type[Any]) -> None:
        if node_type in seen:
            return
        if node_type not in _NODE_DEFINITIONS_BY_TYPE:
            raise ValueError(f"Node type {node_type.__name__} is not registered")
        seen.add(node_type)
        resolved_types.append(node_type)

    for node_type in _discover_schema_node_types(schema):
        add(node_type)
    if node_types is not None:
        for node_type in node_types:
            add(node_type)
    elif _schema_has_unrestricted_node_field(schema):
        for definition in iter_node_definitions():
            add(definition.graphql_type)
    return tuple(resolved_types)


def _schema_contains_node_type(
    schema: strawberry.Schema, definition: NodeDefinition
) -> bool:
    graphql_type = schema.schema_converter.type_map.get(definition.node_name)
    graphql_definition = getattr(graphql_type, "definition", None)
    return getattr(graphql_definition, "origin", None) is definition.graphql_type


def _schema_has_unrestricted_node_field(schema: strawberry.Schema) -> bool:
    for concrete_type in schema.schema_converter.type_map.values():
        definition = getattr(concrete_type, "definition", None)
        fields = getattr(definition, "fields", ())
        for field_definition in fields:
            if getattr(field_definition, "_chemist_node_field_allows_all", False):
                return True
    return False
