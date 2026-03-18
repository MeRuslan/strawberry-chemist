import dataclasses
import datetime
import enum
import re
import types
from abc import ABC, abstractmethod
from typing import (
    Any,
    Callable,
    Dict,
    Optional,
    TypeVar,
    Union,
    cast,
    get_args,
    get_origin,
)

import strawberry
from sqlalchemy import and_, not_, or_
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


class FilterDefinition(ABC):
    python_name: str
    gql_name: str
    argument_annotation: Any

    def __init__(
        self,
        *,
        argument_annotation: Any,
        python_name: str = "filter",
        gql_name: str = "filter",
        description: Optional[str] = None,
        required: bool = False,
        default: Any = UNSET,
    ):
        self.argument_annotation = argument_annotation
        self.python_name = python_name
        self.gql_name = gql_name
        self.required = required
        self.description = description
        self.default = default

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
    def filter_query(
        self,
        query: Select,
        filters: Any,
    ) -> Select:
        raise NotImplementedError


def _is_optional(annotation: Any) -> bool:
    origin = get_origin(annotation)
    return origin in (Union, types.UnionType) and type(None) in get_args(annotation)


@strawberry.input
class StringFilter:
    eq: str | None = None
    ne: str | None = None
    in_: list[str] | None = strawberry.field(default=None, name="in")
    contains: str | None = None
    startswith: str | None = None
    endswith: str | None = None
    ilike: str | None = None
    is_null: bool | None = None


@strawberry.input
class IntFilter:
    eq: int | None = None
    ne: int | None = None
    lt: int | None = None
    lte: int | None = None
    gt: int | None = None
    gte: int | None = None
    between: list[int] | None = None
    in_: list[int] | None = strawberry.field(default=None, name="in")
    is_null: bool | None = None


@strawberry.input
class FloatFilter:
    eq: float | None = None
    ne: float | None = None
    lt: float | None = None
    lte: float | None = None
    gt: float | None = None
    gte: float | None = None
    between: list[float] | None = None
    in_: list[float] | None = strawberry.field(default=None, name="in")
    is_null: bool | None = None


@strawberry.input
class BooleanFilter:
    eq: bool | None = None
    ne: bool | None = None
    is_null: bool | None = None


@strawberry.input
class IDFilter:
    eq: strawberry.ID | None = None
    ne: strawberry.ID | None = None
    in_: list[strawberry.ID] | None = strawberry.field(default=None, name="in")
    is_null: bool | None = None


@strawberry.input
class DateFilter:
    eq: datetime.date | None = None
    ne: datetime.date | None = None
    lt: datetime.date | None = None
    lte: datetime.date | None = None
    gt: datetime.date | None = None
    gte: datetime.date | None = None
    between: list[datetime.date] | None = None
    is_null: bool | None = None


@strawberry.input
class DateTimeFilter:
    eq: datetime.datetime | None = None
    ne: datetime.datetime | None = None
    lt: datetime.datetime | None = None
    lte: datetime.datetime | None = None
    gt: datetime.datetime | None = None
    gte: datetime.datetime | None = None
    between: list[datetime.datetime] | None = None
    is_null: bool | None = None


FilterContext = QueryBuildContext
TFilterClass = TypeVar("TFilterClass", bound=type[Any])


@dataclasses.dataclass
class FilterFieldDefinition:
    path: Optional[str] = None
    apply: Optional[Callable[[Select, Any, FilterContext], Select]] = None
    graphql_name: Optional[str] = None


def filter_field(
    *,
    path: Optional[str] = None,
    apply: Optional[Callable[[Select, Any, FilterContext], Select]] = None,
    name: Optional[str] = None,
) -> FilterFieldDefinition:
    return FilterFieldDefinition(path=path, apply=apply, graphql_name=name)


class FilterSet:
    pass


def _build_operator_expression(column, value: Any):
    conditions = []
    for operator_name, operator_value in dataclasses.asdict(value).items():
        if operator_value is None:
            continue
        if operator_name == "eq":
            conditions.append(column == operator_value)
        elif operator_name == "ne":
            conditions.append(column != operator_value)
        elif operator_name == "lt":
            conditions.append(column < operator_value)
        elif operator_name == "lte":
            conditions.append(column <= operator_value)
        elif operator_name == "gt":
            conditions.append(column > operator_value)
        elif operator_name == "gte":
            conditions.append(column >= operator_value)
        elif operator_name == "between":
            if len(operator_value) != 2:
                raise ValueError("'between' expects exactly two values")
            conditions.append(column.between(operator_value[0], operator_value[1]))
        elif operator_name == "in_":
            conditions.append(column.in_(operator_value))
        elif operator_name == "contains":
            conditions.append(column.contains(operator_value))
        elif operator_name == "startswith":
            conditions.append(column.startswith(operator_value))
        elif operator_name == "endswith":
            conditions.append(column.endswith(operator_value))
        elif operator_name == "ilike":
            conditions.append(column.ilike(operator_value))
        elif operator_name == "is_null":
            conditions.append(
                column.is_(None) if operator_value else column.is_not(None)
            )

    if not conditions:
        return None
    return and_(*conditions)


def _freeze_value(value: Any) -> Any:
    if dataclasses.is_dataclass(value):
        return tuple(
            (field.name, _freeze_value(getattr(value, field.name)))
            for field in dataclasses.fields(value)
        )
    if isinstance(value, enum.Enum):
        return value.value
    if isinstance(value, dict):
        return tuple(sorted((key, _freeze_value(item)) for key, item in value.items()))
    if isinstance(value, (list, tuple)):
        return tuple(_freeze_value(item) for item in value)
    return value


class ManualFilterDefinition(FilterDefinition):
    def __init__(
        self,
        *,
        input_annotation: Any,
        apply: Callable[[Select, Any, FilterContext], Select],
        gql_name: str = "filter",
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
            description=description,
            required=required,
            default=default,
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

    def filter_query(
        self,
        query: Select,
        filters: Any,
    ) -> Select:
        filters = self.normalize_input(filters)
        if filters is None:
            return query
        ctx = QueryBuildContext(model=self.model or infer_model_from_query(query))
        return self.apply_callback(query, filters, ctx)


class PublicFilterDefinition(FilterDefinition):
    def __init__(
        self,
        input_type: Any,
        model: type,
        fields: Dict[str, FilterFieldDefinition],
        python_name: str = "filter",
        gql_name: str = "filter",
    ):
        self.model = model
        self.fields = fields
        super().__init__(
            argument_annotation=input_type,
            python_name=python_name,
            gql_name=gql_name,
            required=False,
        )

    def _build_expression(
        self,
        query: Select,
        filters: Any,
        ctx: FilterContext,
    ) -> tuple[Select, Any]:
        expressions = []
        for field_name, field_def in self.fields.items():
            value = getattr(filters, field_name, None)
            if value is None:
                continue

            if field_def.apply is not None:
                query = field_def.apply(query, value, ctx)
                continue

            query, column = resolve_model_path(
                query,
                self.model,
                field_def.path or field_name,
                joins=ctx.joins,
            )
            expression = _build_operator_expression(column, value)
            if expression is not None:
                expressions.append(expression)

        for item in getattr(filters, "and_", None) or []:
            query, expression = self._build_expression(query, item, ctx)
            if expression is not None:
                expressions.append(expression)

        or_expressions = []
        for item in getattr(filters, "or_", None) or []:
            query, expression = self._build_expression(query, item, ctx)
            if expression is not None:
                or_expressions.append(expression)
        if or_expressions:
            expressions.append(or_(*or_expressions))

        not_value = getattr(filters, "not_", None)
        if not_value is not None:
            query, expression = self._build_expression(query, not_value, ctx)
            if expression is not None:
                expressions.append(not_(expression))

        if not expressions:
            return query, None
        return query, and_(*expressions)

    def filter_query(
        self,
        query: Select,
        filters: Any,
    ) -> Select:
        ctx = QueryBuildContext(model=self.model)
        query, expression = self._build_expression(query, filters, ctx)
        if expression is not None:
            query = query.where(expression)
        return query


def filter(
    model: type[Any],
    *,
    name: Optional[str] = None,
) -> Callable[[TFilterClass], TFilterClass]:
    def wrapper(cls: TFilterClass) -> TFilterClass:
        annotations = dict(cls.__dict__.get("__annotations__", {}))
        field_definitions: Dict[str, FilterFieldDefinition] = {}

        for field_name, annotation in list(annotations.items()):
            if field_name in {"and_", "or_", "not_"}:
                continue
            definition = cls.__dict__.get(field_name)
            if not isinstance(definition, FilterFieldDefinition):
                continue
            field_definitions[field_name] = definition
            if not _is_optional(annotation):
                annotations[field_name] = Optional[annotation]
            setattr(
                cls,
                field_name,
                strawberry.field(default=None, name=definition.graphql_name),
            )

        annotations.setdefault("and_", Optional[list[cls]])  # type: ignore[valid-type]
        annotations.setdefault("or_", Optional[list[cls]])  # type: ignore[valid-type]
        annotations.setdefault("not_", Optional[cls])
        setattr(cls, "and_", strawberry.field(default=None, name="and"))
        setattr(cls, "or_", strawberry.field(default=None, name="or"))
        setattr(cls, "not_", strawberry.field(default=None, name="not"))
        cls.__annotations__ = annotations

        input_type = cast(TFilterClass, strawberry.input(cls, name=name))
        input_type.__sc_filter_definition__ = PublicFilterDefinition(
            input_type=input_type,
            model=model,
            fields=field_definitions,
        )
        return input_type

    return wrapper


def manual_filter(
    *,
    input: Any,
    apply: Callable[[Select, Any, FilterContext], Select],
    name: str = "filter",
    python_name: Optional[str] = None,
    required: bool = False,
    default: Any = UNSET,
    validate: Optional[Callable[[Any], Any]] = None,
    cache_key: Optional[Callable[[Any], Any]] = None,
    description: Optional[str] = None,
    model: Optional[type] = None,
) -> ManualFilterDefinition:
    return ManualFilterDefinition(
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
    "BooleanFilter",
    "DateFilter",
    "DateTimeFilter",
    "FilterContext",
    "FilterDefinition",
    "FilterFieldDefinition",
    "FilterSet",
    "FloatFilter",
    "IDFilter",
    "IntFilter",
    "ManualFilterDefinition",
    "PublicFilterDefinition",
    "StringFilter",
    "filter",
    "filter_field",
    "manual_filter",
]
