from __future__ import annotations

import inspect as pyinspect
import operator
from functools import reduce, wraps
from typing import Annotated, Any, Optional, Sequence, Type

import strawberry
from sqlalchemy import and_, select
from strawberry import BasePermission
from strawberry.types import Info

from strawberry_chemist import utils
from strawberry_chemist.fields.field import field

from .codecs import DEFAULT_ID_CODEC
from .definitions import (
    DecodedNodeId,
    Node,
    NodeDefinition,
    NodeIdConfig,
    RelayIdCodec,
    get_attached_node_definition,
)
from sqlalchemy import inspect as sa_inspect
from sqlalchemy.orm import Mapper


def compose_node_id(
    source: Any,
    definition: NodeDefinition,
    *,
    schema: Optional[strawberry.Schema] = None,
) -> strawberry.ID:
    del schema
    values = tuple(str(getattr(source, field_name)) for field_name in definition.ids)
    return strawberry.ID(definition.codec.encode(definition.node_name, values))


def build_node_id_field(
    *,
    model: type[Any],
    node_name: str,
    ids: Optional[Sequence[str]] = None,
    codec: Optional[RelayIdCodec] = None,
):
    resolved_ids = tuple(ids or infer_node_ids(model))
    resolved_codec = codec or DEFAULT_ID_CODEC
    definition = NodeDefinition(
        graphql_type=object,
        model=model,
        node_name=node_name,
        ids=resolved_ids,
        codec=resolved_codec,
    )
    _register_codec(definition)

    def resolve_node_id(root, info: Info) -> strawberry.ID:
        del info
        return compose_node_id(root, definition)

    return field(resolve_node_id, select=resolved_ids)


def decode_node_token(
    token: str,
    *,
    schema: Optional[strawberry.Schema] = None,
    allowed_types: Optional[Sequence[type[Any]]] = None,
) -> tuple[NodeDefinition, tuple[str, ...]]:
    candidates = _candidate_definitions(schema=schema, allowed_types=allowed_types)
    for definition in candidates:
        try:
            node_name, values = definition.codec.decode(
                token,
                node_names=[definition.node_name],
            )
        except Exception:
            continue
        if node_name == definition.node_name:
            return definition, values
    raise ValueError(f"Unknown node token: {token}")


async def resolve_node(
    info: Info,
    token: strawberry.ID | str,
    *,
    allowed_types: Optional[Sequence[type[Any]]] = None,
):
    definition, values = decode_node_token(
        str(token), schema=info.schema, allowed_types=allowed_types
    )
    if len(values) != len(definition.ids):
        return None

    conditions = [
        getattr(definition.model, field_name)
        == _coerce_identifier_value(definition, field_name, raw_value)
        for field_name, raw_value in zip(definition.ids, values)
    ]
    async with info.context.get_session() as session:
        node = await session.scalar(select(definition.model).where(and_(*conditions)))
    return strawberry.cast(definition.graphql_type, node)


def node_field(
    *,
    allowed_types: Optional[Sequence[type[Any]]] = None,
    name: Optional[str] = None,
):
    candidate_types = tuple(allowed_types or ())
    if allowed_types is not None and not candidate_types:
        raise ValueError("No node types have been registered")

    async def resolver(info: Info, id: strawberry.ID):
        return await resolve_node(
            info,
            id,
            allowed_types=candidate_types or None,
        )

    resolver.__annotations__["return"] = (
        _build_union_return_type(candidate_types) if candidate_types else Optional[Node]
    )
    field_definition = strawberry.field(resolver=resolver, name=name)
    field_definition._chemist_node_field_allowed_types = candidate_types or None
    field_definition._chemist_node_field_allows_all = not candidate_types
    return field_definition


def node_lookup(
    *,
    model: type[Any],
    id_name: str = "id",
    node_param_name: str = "node",
    name: Optional[str] = None,
    id_nullable: bool = False,
    permission_classes: Optional[Sequence[type[BasePermission]]] = None,
    node_permission_classes: Optional[Sequence[type[BasePermission]]] = None,
    description: Optional[str] = None,
    deprecation_reason: Optional[str] = None,
    directives: Sequence[object] = (),
):
    def decorator(resolver: Any):
        original_signature = pyinspect.signature(resolver)
        original_parameters = list(original_signature.parameters.values())
        parameter_names = {parameter.name for parameter in original_parameters}

        if "info" not in parameter_names:
            raise TypeError("node_lookup resolver must declare an 'info' parameter")
        if node_param_name not in parameter_names:
            raise TypeError(
                f"node_lookup resolver must declare a '{node_param_name}' parameter"
            )
        if id_name in parameter_names and id_name != node_param_name:
            raise TypeError(
                f"node_lookup id_name '{id_name}' conflicts with an existing resolver parameter"
            )

        id_annotation: Any = Optional[strawberry.ID] if id_nullable else strawberry.ID
        id_default = None if id_nullable else pyinspect.Parameter.empty
        id_parameter = pyinspect.Parameter(
            name=id_name,
            kind=pyinspect.Parameter.POSITIONAL_OR_KEYWORD,
            default=id_default,
            annotation=id_annotation,
        )
        wrapper_parameters = [
            id_parameter if parameter.name == node_param_name else parameter
            for parameter in original_parameters
        ]
        wrapper_signature = original_signature.replace(parameters=wrapper_parameters)

        @wraps(resolver)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            bound = wrapper_signature.bind_partial(*args, **kwargs)
            resolver_arguments = dict(bound.arguments)
            info = resolver_arguments.get("info")
            if info is None:
                raise TypeError("node_lookup resolver was called without 'info'")

            token = resolver_arguments.pop(id_name, None)
            node = None
            if token is not None:
                candidate_types = _node_types_for_model(model, schema=info.schema)
                if not candidate_types:
                    raise ValueError(
                        f"No @node types are registered for model {model.__name__}"
                    )
                try:
                    node = await resolve_node(
                        info, token, allowed_types=candidate_types
                    )
                except ValueError:
                    node = None

            resolver_arguments[node_param_name] = node
            permission_kwargs = {
                key: value for key, value in resolver_arguments.items() if key != "self"
            }
            for permission_class in node_permission_classes or ():
                permission = permission_class()
                has_permission = permission.has_permission(node, **permission_kwargs)
                if pyinspect.isawaitable(has_permission):
                    has_permission = await has_permission
                if has_permission:
                    continue
                raise PermissionError(getattr(permission, "message", None))

            result = resolver(**resolver_arguments)
            if pyinspect.isawaitable(result):
                return await result
            return result

        wrapper_fn: Any = wrapper
        wrapper_fn.__signature__ = wrapper_signature
        wrapper_fn.__annotations__ = {
            parameter.name: parameter.annotation
            for parameter in wrapper_parameters
            if parameter.annotation is not pyinspect.Parameter.empty
        }
        if original_signature.return_annotation is not pyinspect.Signature.empty:
            wrapper_fn.__annotations__["return"] = original_signature.return_annotation

        return strawberry.field(
            resolver=wrapper_fn,
            name=name,
            description=description,
            permission_classes=list(permission_classes or ()),
            deprecation_reason=deprecation_reason,
            directives=tuple(directives),
        )

    return decorator


def encode_node_id(
    schema: strawberry.Schema,
    node_type: type[Any],
    *,
    source: Any = None,
    values: Optional[Sequence[Any]] = None,
) -> strawberry.ID:
    if (source is None) == (values is None):
        raise ValueError("encode_node_id requires exactly one of 'source' or 'values'")
    definition = get_node_definition(node_type, schema=schema)
    if definition is None:
        raise ValueError(f"Node type {node_type.__name__} is not configured for schema")
    if source is not None:
        return compose_node_id(source, definition, schema=schema)
    assert values is not None
    if len(values) != len(definition.ids):
        raise ValueError(
            f"Node '{definition.node_name}' expects {len(definition.ids)} id values, "
            f"got {len(values)}"
        )
    return strawberry.ID(
        definition.codec.encode(
            definition.node_name,
            tuple(str(value) for value in values),
        )
    )


def decode_node_id(
    schema: strawberry.Schema,
    token: strawberry.ID | str,
    *,
    allowed_types: Optional[Sequence[type[Any]]] = None,
) -> DecodedNodeId:
    definition, values = decode_node_token(
        str(token),
        schema=schema,
        allowed_types=allowed_types,
    )
    return DecodedNodeId(
        node_type=definition.graphql_type,
        node_name=definition.node_name,
        values=values,
    )


def get_node_definition(
    node_type: type[Any], *, schema: Optional[strawberry.Schema] = None
) -> Optional[NodeDefinition]:
    definition = get_attached_node_definition(node_type)
    if definition is None:
        return None
    if schema is None:
        return definition
    if node_type in {
        item.graphql_type for item in iter_node_definitions(schema=schema)
    }:
        return definition
    return None


def iter_node_definitions(
    *, schema: Optional[strawberry.Schema] = None
) -> tuple[NodeDefinition, ...]:
    if schema is None:
        return ()

    definitions: list[NodeDefinition] = []
    seen: set[type[Any]] = set()
    for concrete_type in schema.schema_converter.type_map.values():
        definition = getattr(concrete_type, "definition", None)
        origin = getattr(definition, "origin", None)
        if not isinstance(origin, type):
            continue
        if origin in seen:
            continue
        node_definition = get_attached_node_definition(origin)
        if node_definition is None:
            continue
        seen.add(origin)
        definitions.append(node_definition)
    return tuple(definitions)


def _candidate_definitions(
    *,
    schema: Optional[strawberry.Schema] = None,
    allowed_types: Optional[Sequence[type[Any]]] = None,
) -> tuple[NodeDefinition, ...]:
    if allowed_types is None:
        return iter_node_definitions(schema=schema)
    return tuple(
        definition
        for node_type in allowed_types
        if (definition := get_node_definition(node_type, schema=schema)) is not None
    )


def _node_types_for_model(
    model: type[Any], *, schema: Optional[strawberry.Schema] = None
) -> tuple[type[Any], ...]:
    return tuple(
        definition.graphql_type
        for definition in iter_node_definitions(schema=schema)
        if issubclass(definition.model, model)
    )


def _coerce_identifier_value(
    definition: NodeDefinition, field_name: str, raw_value: str
):
    attribute = getattr(definition.model, field_name)
    try:
        python_type = attribute.property.columns[0].type.python_type
    except Exception:
        return raw_value
    if python_type is str:
        return raw_value
    return python_type(raw_value)


def _build_union_return_type(allowed_types: Sequence[type[Any]]) -> Any:
    if len(allowed_types) == 1:
        return Optional[allowed_types[0]]
    union_name = "ChemistNode_" + "_".join(
        node_type.__name__ for node_type in allowed_types
    )
    union_type = reduce(operator.or_, allowed_types[1:], allowed_types[0])
    return Optional[Annotated[union_type, strawberry.union(union_name)]]


def infer_node_ids(model: type[Any]) -> tuple[str, ...]:
    mapper: Mapper[Any] = sa_inspect(model)
    ids = tuple(str(column.key) for column in mapper.primary_key)
    if not ids:
        raise ValueError(f"Model {model} has no primary key columns")
    return ids


def finalize_node_type(
    graphql_type: type[Any],
    *,
    model: type[Any],
    node_name: str,
    config: NodeIdConfig,
) -> None:
    definition = NodeDefinition(
        graphql_type=graphql_type,
        model=model,
        node_name=node_name,
        ids=tuple(config.ids or infer_node_ids(model)),
        codec=config.codec or DEFAULT_ID_CODEC,
    )
    _register_codec(definition)
    setattr(graphql_type, "__chemist_node_definition__", definition)


def _register_codec(definition: NodeDefinition) -> None:
    register = getattr(definition.codec, "register", None)
    if callable(register):
        register(model=definition.model, node_name=definition.node_name)


def prepare_node_type(
    cls: Type[Any],
    *,
    model: Type[Any],
    graphql_name: Optional[str] = None,
) -> Optional[NodeIdConfig]:
    if not issubclass(cls, Node):
        return None

    existing_id = utils.get_type_attr(cls, "id")
    inherited_definition = next(
        (
            definition
            for base in cls.__mro__[1:]
            if (definition := get_attached_node_definition(base)) is not None
        ),
        None,
    )
    node_config: Optional[NodeIdConfig]
    if isinstance(existing_id, NodeIdConfig):
        node_config = existing_id
    elif existing_id in {utils.UNSET, None} or utils.is_field(existing_id):
        node_config = NodeIdConfig()
    elif inherited_definition is not None:
        node_config = NodeIdConfig(
            ids=inherited_definition.ids,
            codec=inherited_definition.codec,
        )
    else:
        raise TypeError(
            f"Relay Node type {cls.__name__} must use the default node id or define "
            "id = sc.node_id(...)."
        )

    annotations = dict(getattr(cls, "__annotations__", {}))
    annotations["id"] = strawberry.ID
    cls.__annotations__ = annotations
    setattr(
        cls,
        "id",
        build_node_id_field(
            model=model,
            node_name=graphql_name or cls.__name__,
            ids=node_config.ids,
            codec=node_config.codec,
        ),
    )
    return node_config
