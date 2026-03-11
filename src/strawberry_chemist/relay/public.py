from __future__ import annotations

import inspect as pyinspect
from dataclasses import dataclass
from functools import reduce, wraps
import operator
from typing import Annotated, Any, Optional, Protocol, Sequence, Union, cast
from urllib.parse import quote, unquote

import strawberry
from sqlalchemy import and_, inspect as sa_inspect, select
from sqlalchemy.orm import Mapper
from strawberry import BasePermission
from strawberry.types import Info

from strawberry_chemist.fields.field import field


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


class ReadableIdCodec:
    def encode(self, node_name: str, values: tuple[str, ...]) -> str:
        payload = ",".join(quote(value, safe="") for value in values)
        return f"{node_name}_{payload}"

    def decode(
        self,
        token: str,
        *,
        node_names: Optional[Sequence[str]] = None,
    ) -> tuple[str, tuple[str, ...]]:
        if node_names:
            for node_name in sorted(node_names, key=len, reverse=True):
                prefix = f"{node_name}_"
                if token.startswith(prefix):
                    payload = token[len(prefix) :]
                    values = tuple(
                        unquote(item) for item in payload.split(",") if item != ""
                    )
                    return node_name, values
            raise ValueError(f"Unknown node token: {token}")

        node_name, _, payload = token.partition("_")
        if not node_name or not _:
            raise ValueError(f"Unknown node token: {token}")
        values = tuple(unquote(item) for item in payload.split(",") if item != "")
        return node_name, values

    def register(self, *, model: type, node_name: str) -> None:
        return None


class IntRegistryCodec:
    def __init__(self, registry: dict[type, int]):
        self.registry = registry
        self._node_name_to_int: dict[str, int] = {}
        self._int_to_node_name: dict[int, str] = {}

    def register(self, *, model: type, node_name: str) -> None:
        if model not in self.registry:
            return
        code = self.registry[model]
        self._node_name_to_int[node_name] = code
        self._int_to_node_name[code] = node_name

    def encode(self, node_name: str, values: tuple[str, ...]) -> str:
        if node_name not in self._node_name_to_int:
            raise ValueError(f"Node '{node_name}' is not registered with this codec")
        payload = ",".join(quote(value, safe="") for value in values)
        return f"{self._node_name_to_int[node_name]}:{payload}"

    def decode(
        self,
        token: str,
        *,
        node_names: Optional[Sequence[str]] = None,
    ) -> tuple[str, tuple[str, ...]]:
        code_str, _, payload = token.partition(":")
        if not code_str or not _:
            raise ValueError(f"Unknown node token: {token}")
        code = int(code_str)
        if code not in self._int_to_node_name:
            raise ValueError(f"Unknown node token: {token}")
        node_name = self._int_to_node_name[code]
        if node_names is not None and node_name not in node_names:
            raise ValueError(f"Unknown node token: {token}")
        values = tuple(unquote(item) for item in payload.split(",") if item != "")
        return node_name, values


@dataclass(frozen=True)
class NodeDefinition:
    graphql_type: type[Any]
    model: type[Any]
    node_name: str
    ids: tuple[str, ...]
    codec: RelayIdCodec


DEFAULT_ID_CODEC = ReadableIdCodec()
_NODE_DEFINITIONS_BY_TYPE: dict[type[Any], NodeDefinition] = {}
_NODE_DEFINITIONS_BY_NAME: dict[str, NodeDefinition] = {}


def get_node_definition(node_type: type[Any]) -> Optional[NodeDefinition]:
    return _NODE_DEFINITIONS_BY_TYPE.get(node_type)


def iter_node_definitions() -> tuple[NodeDefinition, ...]:
    return tuple(_NODE_DEFINITIONS_BY_TYPE.values())


def clear_node_registry() -> None:
    _NODE_DEFINITIONS_BY_TYPE.clear()
    _NODE_DEFINITIONS_BY_NAME.clear()


def infer_node_ids(model: type[Any]) -> tuple[str, ...]:
    mapper: Mapper[Any] = cast(Mapper[Any], sa_inspect(model))
    ids = tuple(str(column.key) for column in mapper.primary_key)
    if not ids:
        raise ValueError(f"Model {model} has no primary key columns")
    return ids


def compose_node_id(source: Any, definition: NodeDefinition) -> strawberry.ID:
    values = tuple(str(getattr(source, field_name)) for field_name in definition.ids)
    return strawberry.ID(definition.codec.encode(definition.node_name, values))


def _resolve_node_name(graphql_type: type[Any], node_name: Optional[str]) -> str:
    if node_name is not None:
        return node_name

    definition = getattr(graphql_type, "__strawberry_definition__", None)
    if definition is None:
        raise ValueError(f"GraphQL type {graphql_type} is not a Strawberry type")
    return str(definition.name)


def build_node_id_field(
    *,
    model: type[Any],
    node_name: str,
    ids: Optional[Sequence[str]] = None,
    codec: Optional[RelayIdCodec] = None,
):
    resolved_ids = tuple(ids or infer_node_ids(model))
    definition = NodeDefinition(
        graphql_type=object,
        model=model,
        node_name=node_name,
        ids=resolved_ids,
        codec=codec or DEFAULT_ID_CODEC,
    )

    def resolve_node_id(root) -> strawberry.ID:
        return compose_node_id(root, definition)

    return field(resolve_node_id, select=resolved_ids)


def register_node_type(
    graphql_type: type[Any],
    *,
    model: type[Any],
    ids: Optional[Sequence[str]] = None,
    codec: Optional[RelayIdCodec] = None,
    node_name: Optional[str] = None,
) -> NodeDefinition:
    resolved_codec = codec or DEFAULT_ID_CODEC
    resolved_name = _resolve_node_name(graphql_type, node_name)
    definition = NodeDefinition(
        graphql_type=graphql_type,
        model=model,
        node_name=resolved_name,
        ids=tuple(ids or infer_node_ids(model)),
        codec=resolved_codec,
    )
    register = getattr(resolved_codec, "register", None)
    if callable(register):
        register(model=model, node_name=resolved_name)
    _NODE_DEFINITIONS_BY_TYPE[graphql_type] = definition
    _NODE_DEFINITIONS_BY_NAME[resolved_name] = definition
    return definition


def _candidate_definitions(
    allowed_types: Optional[Sequence[type[Any]]] = None,
) -> tuple[NodeDefinition, ...]:
    if allowed_types is None:
        return iter_node_definitions()
    return tuple(
        definition
        for node_type in allowed_types
        if (definition := get_node_definition(node_type)) is not None
    )


def _node_types_for_model(model: type[Any]) -> tuple[type[Any], ...]:
    return tuple(
        definition.graphql_type
        for definition in iter_node_definitions()
        if issubclass(definition.model, model)
    )


def decode_node_token(
    token: str,
    *,
    allowed_types: Optional[Sequence[type[Any]]] = None,
) -> tuple[NodeDefinition, tuple[str, ...]]:
    candidates = _candidate_definitions(allowed_types)
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


async def resolve_node(
    info: Info,
    token: strawberry.ID | str,
    *,
    allowed_types: Optional[Sequence[type[Any]]] = None,
):
    definition, values = decode_node_token(str(token), allowed_types=allowed_types)
    if len(values) != len(definition.ids):
        return None

    conditions = [
        getattr(definition.model, field_name)
        == _coerce_identifier_value(definition, field_name, raw_value)
        for field_name, raw_value in zip(definition.ids, values)
    ]
    async with info.context.get_session() as session:
        return await session.scalar(select(definition.model).where(and_(*conditions)))


def _build_union_return_type(allowed_types: Sequence[type[Any]]) -> Any:
    if len(allowed_types) == 1:
        return Optional[allowed_types[0]]
    union_name = "ChemistNode_" + "_".join(
        node_type.__name__ for node_type in allowed_types
    )
    union_type = reduce(operator.or_, allowed_types[1:], allowed_types[0])
    return Optional[Annotated[union_type, strawberry.union(union_name)]]


def node_field(
    *,
    allowed_types: Optional[Sequence[type[Any]]] = None,
    name: Optional[str] = None,
):
    candidate_types = tuple(
        allowed_types
        or (definition.graphql_type for definition in iter_node_definitions())
    )
    if not candidate_types:
        raise ValueError("No node types have been registered")

    async def resolver(info: Info, id: strawberry.ID):
        return await resolve_node(info, id, allowed_types=candidate_types)

    resolver.__annotations__["return"] = _build_union_return_type(candidate_types)
    return strawberry.field(resolver=resolver, name=name)


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
                candidate_types = _node_types_for_model(model)
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


__all__ = [
    "DEFAULT_ID_CODEC",
    "IntRegistryCodec",
    "Node",
    "NodeDefinition",
    "ReadableIdCodec",
    "RelayIdCodec",
    "build_node_id_field",
    "clear_node_registry",
    "compose_node_id",
    "decode_node_token",
    "get_node_definition",
    "iter_node_definitions",
    "node_field",
    "node_lookup",
    "register_node_type",
    "resolve_node",
]
