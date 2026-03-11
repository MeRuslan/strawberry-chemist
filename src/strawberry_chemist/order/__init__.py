import enum
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional

import strawberry
from sqlalchemy import asc, desc, nullsfirst, nullslast
from sqlalchemy.sql import Select
from strawberry import UNSET
from strawberry.annotation import StrawberryAnnotation
from strawberry.types.arguments import StrawberryArgument

from strawberry_chemist.querying import (
    QueryBuildContext,
    infer_model_from_query,
    resolve_model_path,
)


def _pythonize_name(name: str) -> str:
    return re.sub(r"(?<!^)(?=[A-Z])", "_", name).lower()


def _graphql_enum_name(name: str) -> str:
    return _pythonize_name(name).upper()


def _freeze_value(value: Any) -> Any:
    if hasattr(value, "__dataclass_fields__"):
        return tuple(
            (field_name, _freeze_value(getattr(value, field_name)))
            for field_name in value.__dataclass_fields__
        )
    if isinstance(value, enum.Enum):
        return value.value
    if isinstance(value, dict):
        return tuple(sorted((key, _freeze_value(item)) for key, item in value.items()))
    if isinstance(value, (list, tuple)):
        return tuple(_freeze_value(item) for item in value)
    return value


class OrderDefinition(ABC):
    python_name: str
    gql_name: str
    default: Any
    argument_annotation: Any

    def __init__(
        self,
        *,
        argument_annotation: Any,
        python_name: str = "order",
        gql_name: str = "order",
        default: Any = UNSET,
        required: bool = False,
        description: Optional[str] = None,
    ):
        self.argument_annotation = argument_annotation
        self.python_name = python_name
        self.gql_name = gql_name
        self.default = default
        self.required = required
        self.description = description

    @property
    def argument(self) -> StrawberryArgument:
        annotation = (
            self.argument_annotation
            if self.required
            else Optional[self.argument_annotation]
        )
        return StrawberryArgument(
            default=self.default,
            description=self.description,
            graphql_name=self.gql_name,
            python_name=self.python_name,
            type_annotation=StrawberryAnnotation(annotation),
        )

    def normalize_input(self, value: Any) -> Any:
        return value

    def cache_key(self, value: Any) -> Any:
        if value is None:
            return None
        return _freeze_value(self.normalize_input(value))

    @abstractmethod
    def order_query(
        self,
        query: Select,
        order: Any,
    ) -> Select:
        raise NotImplemented


@strawberry.enum
class SortDirection(enum.Enum):
    ASC = "asc"
    DESC = "desc"


@strawberry.enum
class NullsOrder(enum.Enum):
    FIRST = "first"
    LAST = "last"


OrderContext = QueryBuildContext


@dataclass
class OrderFieldDefinition:
    path: Optional[str] = None
    resolve: Optional[Callable[[Select, OrderContext], tuple[Select, Any]]] = None
    graphql_name: Optional[str] = None


def order_field(
    *,
    path: Optional[str] = None,
    resolve: Optional[Callable[[Select, OrderContext], tuple[Select, Any]]] = None,
    name: Optional[str] = None,
) -> OrderFieldDefinition:
    return OrderFieldDefinition(path=path, resolve=resolve, graphql_name=name)


class ManualOrderDefinition(OrderDefinition):
    def __init__(
        self,
        *,
        input_annotation: Any,
        apply: Callable[[Select, Any, OrderContext], Select],
        gql_name: str = "orderBy",
        python_name: Optional[str] = None,
        required: bool = False,
        default: Any = UNSET,
        validate: Optional[Callable[[Any], Any]] = None,
        cache_key: Optional[Callable[[Any], Any]] = None,
        description: Optional[str] = None,
        model: Optional[type] = None,
    ):
        self.apply_callback = apply
        self.validate_callback = validate
        self.cache_key_callback = cache_key
        self.model = model
        super().__init__(
            argument_annotation=input_annotation,
            python_name=python_name or _pythonize_name(gql_name),
            gql_name=gql_name,
            default=default,
            required=required,
            description=description,
        )

    def normalize_input(self, value: Any) -> Any:
        if self.validate_callback is None or value is None:
            return value
        return self.validate_callback(value)

    def cache_key(self, value: Any) -> Any:
        value = self.normalize_input(value)
        if value is None:
            return None
        if self.cache_key_callback is not None:
            return self.cache_key_callback(value)
        return super().cache_key(value)

    def order_query(
        self,
        query: Select,
        order: Any,
    ) -> Select:
        order = self.normalize_input(order)
        if order is None:
            return query
        ctx = QueryBuildContext(model=self.model or infer_model_from_query(query))
        return self.apply_callback(query, order, ctx)


class PublicOrderingDefinition(OrderDefinition):
    def __init__(
        self,
        item_type: Any,
        model: type,
        fields: Dict[str, OrderFieldDefinition],
        python_name: str = "order_by",
        gql_name: str = "orderBy",
    ):
        self.item_type = item_type
        self.model = model
        self.fields = fields
        super().__init__(
            argument_annotation=list[item_type],
            python_name=python_name,
            gql_name=gql_name,
            required=False,
        )

    def cache_key(self, ordering: Any) -> Any:
        if ordering is None:
            return None
        return tuple(
            (
                item.field.value,
                item.direction.value,
                item.nulls.value if item.nulls is not None else None,
            )
            for item in ordering
        )

    def order_query(
        self,
        query: Select,
        order: Any,
    ) -> Select:
        if not order:
            return query

        ctx = QueryBuildContext(model=self.model)
        for item in order:
            field_definition = self.fields[item.field.value]
            if field_definition.resolve is not None:
                query, order_column = field_definition.resolve(query, ctx)
            else:
                query, order_column = resolve_model_path(
                    query,
                    self.model,
                    field_definition.path or item.field.value,
                    joins=ctx.joins,
                )

            if item.direction == SortDirection.DESC:
                order_expression = desc(order_column)
            else:
                order_expression = asc(order_column)

            if item.nulls == NullsOrder.FIRST:
                order_expression = nullsfirst(order_expression)
            elif item.nulls == NullsOrder.LAST:
                order_expression = nullslast(order_expression)

            query = query.order_by(order_expression)

        return query


def order(model, *, name: Optional[str] = None):
    def wrapper(cls):
        field_definitions = {
            field_name: definition
            for field_name, definition in cls.__dict__.items()
            if isinstance(definition, OrderFieldDefinition)
        }

        enum_values = {}
        for field_name, definition in field_definitions.items():
            enum_name = _graphql_enum_name(definition.graphql_name or field_name)
            if enum_name in enum_values and enum_values[enum_name] != field_name:
                raise ValueError(
                    f"Duplicate order field GraphQL name '{enum_name}' on {cls.__name__}"
                )
            enum_values[enum_name] = field_name
        field_enum = strawberry.enum(enum.Enum(f"{cls.__name__}Field", enum_values))

        item_type = type(
            f"{cls.__name__}Item",
            (),
            {
                "__annotations__": {
                    "field": field_enum,
                    "direction": SortDirection,
                    "nulls": Optional[NullsOrder],
                },
                "nulls": strawberry.field(default=None),
            },
        )
        item_type.__module__ = cls.__module__
        item_type = strawberry.input(item_type, name=name or f"{cls.__name__}Item")
        cls.__sc_order_definition__ = PublicOrderingDefinition(
            item_type=item_type,
            model=model,
            fields=field_definitions,
        )
        cls.__sc_order_item_type__ = item_type
        return cls

    return wrapper


def manual_order(
    *,
    input: Any,
    apply: Callable[[Select, Any, OrderContext], Select],
    name: str = "orderBy",
    python_name: Optional[str] = None,
    required: bool = False,
    default: Any = UNSET,
    validate: Optional[Callable[[Any], Any]] = None,
    cache_key: Optional[Callable[[Any], Any]] = None,
    description: Optional[str] = None,
    model: Optional[type] = None,
) -> ManualOrderDefinition:
    return ManualOrderDefinition(
        input_annotation=input,
        apply=apply,
        gql_name=name,
        python_name=python_name,
        required=required,
        default=default,
        validate=validate,
        cache_key=cache_key,
        description=description,
        model=model,
    )


__all__ = [
    "ManualOrderDefinition",
    "NullsOrder",
    "OrderContext",
    "OrderDefinition",
    "OrderFieldDefinition",
    "PublicOrderingDefinition",
    "SortDirection",
    "manual_order",
    "order",
    "order_field",
]
