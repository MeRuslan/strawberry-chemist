from functools import cached_property
from re import sub
from typing import (
    Any,
    Dict,
    Iterable,
    List,
    Literal,
    Mapping,
    Optional,
    Sequence,
    Self,
    TypeAlias,
)

from graphql.pyutils import is_awaitable
from sqlalchemy import inspect
from sqlalchemy.orm import DeclarativeMeta, RelationshipProperty
from strawberry import UNSET, LazyType
from strawberry.annotation import StrawberryAnnotation
from strawberry.types.arguments import StrawberryArgument
from strawberry.types.base import StrawberryList, StrawberryOptional
from strawberry.types.field import StrawberryField
from strawberry.types import Info

from strawberry_chemist import utils
from strawberry_chemist.fields.utils import drill_for_field_names
from strawberry_chemist.gql_context import SQLAlchemyContext, context_var


def camel_case(s: str):
    s = sub(r"(_|-)+", " ", s).title().replace(" ", "")
    return "".join([s[0].lower(), s[1:]])


RelationshipLoad: TypeAlias = Literal["selected", "full"]
SelectBindingInput: TypeAlias = Iterable[str] | Mapping[str, str]


def _dedupe_field_names(*groups: Iterable[str]) -> List[str]:
    result: List[str] = []
    seen: set[str] = set()
    for group in groups:
        for name in group:
            if name in seen:
                continue
            seen.add(name)
            result.append(name)
    return result


def _reject_legacy_kwargs(
    public_name: str,
    kwargs: Dict[str, Any],
    *,
    unsupported: Sequence[str],
) -> None:
    rejected = [name for name in unsupported if name in kwargs]
    if not rejected:
        return
    if len(rejected) == 1:
        raise TypeError(
            f"{public_name}() got an unexpected keyword argument '{rejected[0]}'"
        )
    joined = ", ".join(sorted(rejected))
    raise TypeError(f"{public_name}() got unexpected keyword arguments: {joined}")


def _normalize_select_bindings(
    select: Optional[SelectBindingInput],
) -> tuple[tuple[str, ...], tuple[tuple[str, str], ...]]:
    if select is None:
        return (), ()

    items: list[tuple[str, str]] = []
    seen_paths: set[str] = set()
    seen_params: set[str] = set()

    raw_items: Iterable[tuple[str, str]]
    if isinstance(select, Mapping):
        raw_items = select.items()
    else:
        raw_items = ((path, path.rsplit(".", 1)[-1]) for path in select)

    for path, param_name in raw_items:
        if path in seen_paths:
            continue
        if param_name in seen_params:
            raise ValueError(
                f"select= cannot bind multiple source fields to resolver parameter '{param_name}'"
            )
        seen_paths.add(path)
        seen_params.add(param_name)
        items.append((param_name, path))

    return tuple(path for _, path in items), tuple(items)


class StrawberrySQLAlchemyField(StrawberryField):
    """
    Basic field, inherits StrawberryField.

    In a nutshell, handles resolving SQLAlchemy fields,
        such as: generating itself out of a strawberry field,
        and resolving sqlalchemy model fields.
    And has a bunch of common methods for all SQLAlchemy field types.
    """

    sqlalchemy_name: str | None
    origin_container_type: Any | None
    select_fields: tuple[str, ...]
    select_bindings: tuple[tuple[str, str], ...]
    _field_type: Any
    is_auto: bool

    def __init__(
        self,
        sqlalchemy_name: str | None = None,
        select: Optional[SelectBindingInput] = None,
        graphql_name: str | None = None,
        python_name: str | None = None,
        **kwargs,
    ):
        select_fields, select_bindings = _normalize_select_bindings(select)
        self.sqlalchemy_name = sqlalchemy_name
        self.origin_container_type = None
        self.select_fields = select_fields
        self.select_bindings = select_bindings
        self.is_auto = False
        super().__init__(graphql_name=graphql_name, python_name=python_name, **kwargs)

    @cached_property
    def needs_parent_fields(self) -> List[str]:
        if self.select_fields:
            return list(self.select_fields)
        return [field_name for field_name in [self.sqlalchemy_name] if field_name]

    @property
    def is_optional(self) -> bool:
        return isinstance(self.type, StrawberryOptional)

    @property
    def is_list(self) -> bool:
        if isinstance(self.type, StrawberryList):
            return True
        if isinstance(self.type, StrawberryOptional):
            return isinstance(self.type.of_type, StrawberryList)
        return False

    @property
    def arguments(self) -> List[StrawberryArgument]:
        gql_arguments = list(super().arguments)
        if not self.base_resolver:
            return gql_arguments
        hidden = self.hidden_resolver_argument_names
        if not hidden:
            return gql_arguments
        return [
            argument for argument in gql_arguments if argument.python_name not in hidden
        ]

    @arguments.setter
    def arguments(self, value: List[StrawberryArgument]) -> None:
        self._arguments = value

    @classmethod
    def from_field(
        cls,
        field: StrawberryField,
        sqlalchemy_type: Any,
    ) -> Self:
        del sqlalchemy_type
        if isinstance(field, cls):
            return field

        metadata = field if isinstance(field, StrawberrySQLAlchemyField) else None
        new_field = cls(
            base_resolver=field.base_resolver,
            default_factory=field.default_factory,
            default=field.default,
            sqlalchemy_name=(
                metadata.sqlalchemy_name
                if metadata is not None and metadata.sqlalchemy_name
                else field.name
            ),
            graphql_name=field.graphql_name,
            python_name=field.name,
            type_annotation=field.type_annotation or StrawberryAnnotation(field.type),
            select=metadata.select_fields if metadata is not None else None,
        )
        if metadata is None:
            return new_field
        new_field.is_auto = metadata.is_auto
        new_field.origin_container_type = metadata.origin_container_type
        new_field._field_type = metadata._field_type
        return new_field

    @cached_property
    def selected_field_value_map(self) -> Dict[str, str]:
        return dict(self.select_bindings)

    @cached_property
    def hidden_resolver_argument_names(self) -> set[str]:
        if not self.base_resolver or not self.select_fields:
            return set()
        return set(self.selected_field_value_map)

    @staticmethod
    def _resolve_selected_value(source: Any, path: str) -> Any:
        value = source
        for chunk in path.split("."):
            value = getattr(value, chunk)
        return value

    def inject_resolver_kwargs(
        self,
        source: Any,
        kwargs: Dict[str, Any],
        relationship_value: Any = UNSET,
    ) -> Dict[str, Any]:
        del relationship_value
        if not self.base_resolver:
            return kwargs

        kwargs = dict(kwargs or {})
        missing_arguments = []
        selected_values = {
            param_name: self._resolve_selected_value(source, path)
            for param_name, path in self.selected_field_value_map.items()
        }
        for argument in self.base_resolver.arguments:
            if argument.python_name in kwargs:
                continue
            if argument.python_name not in self.hidden_resolver_argument_names:
                continue
            if argument.python_name not in selected_values:
                missing_arguments.append(argument.python_name)
                continue
            kwargs[argument.python_name] = selected_values[argument.python_name]

        if missing_arguments:
            raise TypeError(
                f"Field '{self.python_name}' requires resolver parameters {missing_arguments}, "
                f"but select={list(self.select_fields)!r} does not provide them."
            )

        return kwargs

    def get_result(
        self,
        source: Any,
        info: Info | None,
        args: List[Any],
        kwargs: Dict[str, Any],
    ):
        # TODO: fix the passing of info, it's not passed at all
        # TODO: come up with a way to both pass parent and the current field (e.g. anime, and genres for genresGrouped)
        if self.base_resolver:
            kwargs = self.inject_resolver_kwargs(source, kwargs)
            return super().get_result(source, info, args, kwargs)
        result = self.resolver(source, info, *args, **kwargs)
        return result

    def resolver(
        self,
        source: Any,
        info: Info[SQLAlchemyContext, Any] | None,
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        assert source is not None, (
            "Raw StrawberrySQLAlchemyField should not be a root."
            "You can use some sort of a connection for that."
        )
        assert self.sqlalchemy_name is not None
        return getattr(source, self.sqlalchemy_name)


class StrawberrySQLAlchemyRelationField(StrawberrySQLAlchemyField):
    """
    A field that resolves to a SQLAlchemy model.
    Useful for relationship-backed fields that need dataloader-backed loading.
    """

    load_simple_fields_from_sqlalchemy = True
    relationship_property: RelationshipProperty[Any] | None
    parent_select_fields: tuple[str, ...]
    source_param_name: str | None

    # need to state it clearly, strawberry might handle as a sync one
    #   and fail on complex scenarios with async permissions
    is_async = True

    def __init__(
        self,
        where: Optional[Sequence[Any]] = None,
        relationship_select: Optional[Iterable[str]] = None,
        parent_select: Optional[Iterable[str]] = None,
        load_full: bool = False,
        source_param_name: str | None = None,
        **kwargs,
    ):
        self.where = tuple(where or ())
        # very important field, it's set in type generation
        self.relationship_property = None
        self.relationship_select = tuple(relationship_select or ())
        self.parent_select_fields = tuple(parent_select or ())
        self.load_full = load_full
        self.source_param_name = source_param_name
        super().__init__(**kwargs)

    def require_relationship_property(self) -> RelationshipProperty[Any]:
        relationship_property = self.relationship_property
        assert relationship_property is not None, (
            f"Field '{self.python_name}' is missing SQLAlchemy relationship metadata."
        )
        return relationship_property

    @cached_property
    def needs_parent_fields(self) -> List[str]:
        # traverse relationship property and get all local columns
        relationship_key_names = [
            key.name for key in self.require_relationship_property().local_columns
        ]
        return _dedupe_field_names(relationship_key_names, self.parent_select_fields)

    @cached_property
    def sqlalchemy_model(self) -> DeclarativeMeta:
        type_ = utils.unwrap_type(self.type)
        type_ = utils.get_sqlalchemy_model(type_)
        # not specified explicitly in the type itself
        #   (e.g. is defined as a field in a strawberry type
        #   with scalar type, not a model type),
        #   have to find out through the relationship property
        if not type_:
            type_ = self.require_relationship_property().mapper.class_
        return type_

    @cached_property
    def sqlalchemy_column_names(self) -> set[str]:
        return {attr.key for attr in inspect(self.sqlalchemy_model).column_attrs}

    @cached_property
    def primary_type(self):
        type_ = utils.unwrap_type(self.type)
        if isinstance(type_, LazyType):
            type_ = type_.resolve_type()

        return type_

    @cached_property
    def type_field_map(self) -> Dict[str, StrawberryField]:
        assert hasattr(self.primary_type, "__strawberry_definition__"), (
            f"Type {self.primary_type} has no __strawberry_definition__ attribute."
            f"Make sure it's a StrawberrySQLAlchemy type. Or use load='full'."
        )

        fields: List[StrawberryField] = (
            self.primary_type.__strawberry_definition__.fields
        )
        sqla_field_map: Dict[str, StrawberryField] = {
            f.graphql_name if f.graphql_name else camel_case(f.name): f
            for f in fields
            if isinstance(f, StrawberrySQLAlchemyField)
        }
        if self.load_simple_fields_from_sqlalchemy:
            simple_fields = {
                f.graphql_name if f.graphql_name else camel_case(f.name): f
                for f in fields
                if (
                    f.is_basic_field
                    and f.python_name is not None
                    and f.python_name in self.sqlalchemy_column_names
                )
            }
            sqla_field_map.update(simple_fields)
        return sqla_field_map

    def get_select_fields(self, **kwargs) -> List[Any]:
        if self.load_full:
            return list(inspect(self.sqlalchemy_model).c)

        # restrict fields to load
        ctx = context_var.get()
        fields = ctx.field_sub_selections[self]

        fields_requested = set()
        # ask what they need only StrawberrySQLAlchemyFields
        # filter fields that are in type_field_map
        filtered = [f for f in fields if f in self.type_field_map]
        for field in filtered:
            mapped_field = self.type_field_map[field]
            if isinstance(mapped_field, StrawberrySQLAlchemyField):
                fields_requested.update(mapped_field.needs_parent_fields)
            elif mapped_field.is_basic_field and mapped_field.python_name is not None:
                fields_requested.add(mapped_field.python_name)
        fields_requested.update(self.relationship_select)
        selections = [
            getattr(self.sqlalchemy_model, field_iter)
            for field_iter in fields_requested
            if field_iter
        ]
        return selections

    @property
    def is_basic_field(self) -> bool:
        return False

    @property
    def arguments(self) -> List[StrawberryArgument]:
        gql_arguments = list(super().arguments)
        if not self.base_resolver:
            return gql_arguments
        hidden = self.hidden_resolver_argument_names
        return [
            argument for argument in gql_arguments if argument.python_name not in hidden
        ]

    @arguments.setter
    def arguments(self, value: List[StrawberryArgument]) -> None:
        self._arguments = value

    @cached_property
    def hidden_resolver_argument_names(self) -> set[str]:
        hidden = set(super().hidden_resolver_argument_names)
        if not self.base_resolver:
            return hidden
        hidden.add(self.required_source_param_name)
        return hidden

    @cached_property
    def required_source_param_name(self) -> str:
        param_name = self.source_param_name or self.sqlalchemy_name or self.python_name
        if param_name is None:
            raise TypeError(
                "Relationship-backed resolver fields need a source_param_name when the source name cannot be inferred."
            )
        if not self.base_resolver:
            return param_name
        resolver_param_names = {
            argument.python_name for argument in self.base_resolver.arguments
        }
        if param_name not in resolver_param_names:
            raise TypeError(
                f"Field '{self.python_name}' resolver must declare a '{param_name}' parameter "
                f"or set source_param_name= to the injected runtime parameter name."
            )
        return param_name

    def inject_resolver_kwargs(
        self,
        source: Any,
        kwargs: Dict[str, Any],
        relationship_value: Any = UNSET,
    ) -> Dict[str, Any]:
        kwargs = dict(kwargs or {})
        if relationship_value is not UNSET and self.base_resolver:
            kwargs.setdefault(self.required_source_param_name, relationship_value)
        return super().inject_resolver_kwargs(source, kwargs)

    async def get_result(
        self,
        source: Any,
        info: Info | None,
        args: List[Any],
        kwargs: Dict[str, Any],
    ):
        # always load the related model through dataloader
        # make sure info is not duplicated
        kwargs = dict(kwargs or {})
        kwargs.pop("info", None)
        result = await self.resolver(source, info, *args, **kwargs)
        # if there was a base resolver, use it
        if self.base_resolver:
            base_argument_names = {
                argument.python_name for argument in self.base_resolver.arguments
            }
            resolver_kwargs = {
                key: value
                for key, value in (kwargs or {}).items()
                if key in base_argument_names
            }
            if self.base_resolver.info_parameter is not None and info is not None:
                resolver_kwargs["info"] = info
            kwargs = self.inject_resolver_kwargs(
                source,
                resolver_kwargs,
                relationship_value=result,
            )
            res = StrawberryField.get_result(self, source, info, args, kwargs)
            if is_awaitable(res):
                return await res
            return res
        return result

    async def resolver(
        self,
        source: Any,
        info: Info[SQLAlchemyContext, Any] | None,
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        assert source is not None, (
            f"Raw StrawberrySQLAlchemyRelationField for model {self.sqlalchemy_model} should not be a root."
            f"You can use some sort of a connection for that."
        )
        assert info is not None
        # filter selections to those which has name attribute
        #  (e.g. not InlineFragment)
        # names = [s.name for s in selections if hasattr(s, 'name')]
        names = list(drill_for_field_names(info.selected_fields[0].selections))
        info.context.field_sub_selections[self].update(names)

        result = await info.context.dataloader_container.get_dataloader(
            field=self
        ).load(source)
        return result


def field(
    resolver=None,
    select=None,
    *,
    name=None,
    default=UNSET,
    **kwargs,
):
    _reject_legacy_kwargs(
        "field",
        kwargs,
        unsupported=("post_processor", "additional_parent_fields", "sqlalchemy_name"),
    )
    # TODO: fix default, it doesn't work
    field_ = StrawberrySQLAlchemyField(
        python_name=None,
        graphql_name=name,
        type_annotation=None,
        select=select,
        default=default,
        **kwargs,
    )
    if resolver:
        return field_(resolver)
    return field_


def attr(
    sqlalchemy_name=None,
    *,
    name=None,
    default=UNSET,
    **kwargs,
):
    return StrawberrySQLAlchemyField(
        python_name=None,
        graphql_name=name,
        type_annotation=None,
        sqlalchemy_name=sqlalchemy_name,
        default=default,
        **kwargs,
    )


def _normalize_where_clause(where):
    if where is None:
        return ()
    filters = where if isinstance(where, list) else [where]
    return tuple(filters)


def relationship(
    resolver=None,
    /,
    source: Optional[str] = None,
    *,
    source_param_name: str | None = None,
    where=None,
    select=None,
    parent_select: Optional[Iterable[str]] = None,
    load: RelationshipLoad = "selected",
    name=None,
    default=UNSET,
    **kwargs,
):
    _reject_legacy_kwargs(
        "relationship",
        kwargs,
        unsupported=(
            "post_processor",
            "pre_filter",
            "needs_fields",
            "ignore_field_selections",
            "sqlalchemy_name",
            "default_order_by",
        ),
    )
    if isinstance(resolver, str):
        source = resolver
        resolver = None
    if load not in {"selected", "full"}:
        raise ValueError("relationship() load must be either 'selected' or 'full'")

    field_ = StrawberrySQLAlchemyRelationField(
        where=_normalize_where_clause(where),
        python_name=None,
        graphql_name=name,
        type_annotation=None,
        sqlalchemy_name=source,
        default=default,
        relationship_select=select,
        parent_select=parent_select,
        load_full=load == "full",
        source_param_name=source_param_name,
        **kwargs,
    )
    if resolver:
        return field_(resolver)
    return field_
