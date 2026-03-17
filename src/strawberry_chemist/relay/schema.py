from __future__ import annotations

from typing import Any, Optional, Sequence

from graphql import (
    GraphQLNamedType,
    GraphQLNonNull,
    GraphQLSchema,
    is_introspection_type,
    is_specified_scalar_type,
    validate_schema,
)
import strawberry

from .codecs import DEFAULT_ID_CODEC
from .definitions import RelayIdCodec
from .registry import (
    _make_schema_state,
    _resolve_configured_node_types,
    get_existing_schema_state,
    set_schema_state,
)


def configure(
    schema: strawberry.Schema,
    *,
    default_codec: Optional[RelayIdCodec] = None,
    node_types: Optional[Sequence[type[Any]]] = None,
) -> strawberry.Schema:
    existing_state = get_existing_schema_state(schema)
    resolved_default_codec = (
        default_codec
        if default_codec is not None
        else (
            existing_state.default_codec
            if existing_state is not None
            else DEFAULT_ID_CODEC
        )
    )
    resolved_node_types = _resolve_configured_node_types(schema, node_types=node_types)
    _rebuild_schema_with_node_types(schema, resolved_node_types)
    set_schema_state(
        schema,
        _make_schema_state(
            resolved_default_codec,
            resolved_node_types,
        ),
    )
    return schema


def _rebuild_schema_with_node_types(
    schema: strawberry.Schema, node_types: Sequence[type[Any]]
) -> None:
    current = schema._schema
    root_type_names = {
        root_type.name
        for root_type in (
            current.query_type,
            current.mutation_type,
            current.subscription_type,
        )
        if root_type is not None
    }
    graphql_types_by_name: dict[str, GraphQLNamedType] = {}

    for graphql_type in current.type_map.values():
        if not isinstance(graphql_type, GraphQLNamedType):
            continue
        if graphql_type.name in root_type_names:
            continue
        if is_specified_scalar_type(graphql_type):
            continue
        if is_introspection_type(graphql_type):
            continue
        graphql_types_by_name[graphql_type.name] = graphql_type

    for node_type in node_types:
        graphql_type = schema.schema_converter.from_object(
            node_type.__strawberry_definition__
        )
        if isinstance(graphql_type, GraphQLNonNull):
            graphql_type = graphql_type.of_type
        if not isinstance(graphql_type, GraphQLNamedType):
            raise TypeError(f"{graphql_type} is not a named GraphQL type")
        graphql_types_by_name[graphql_type.name] = graphql_type

    schema._schema = GraphQLSchema(
        query=current.query_type,
        mutation=current.mutation_type,
        subscription=current.subscription_type,
        directives=current.directives,
        types=list(graphql_types_by_name.values()),
        description=current.description,
        extensions=current.extensions,
        ast_node=current.ast_node,
        extension_ast_nodes=current.extension_ast_nodes,
    )
    schema._schema._strawberry_schema = schema  # type: ignore[attr-defined]
    schema._extend_introspection()
    schema.get_type_by_name.cache_clear()

    errors = validate_schema(schema._schema)
    if errors:
        formatted_errors = "\n\n".join(f"❌ {error.message}" for error in errors)
        raise ValueError(f"Invalid Schema. Errors:\n\n{formatted_errors}")
