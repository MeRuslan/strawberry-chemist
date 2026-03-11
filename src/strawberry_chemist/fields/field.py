from functools import cached_property
from re import sub
from typing import Any, Callable, Dict, Iterable, List, Optional, Sequence

from graphql.pyutils import is_awaitable
from sqlalchemy import inspect
from sqlalchemy.orm import DeclarativeMeta
from strawberry import UNSET, LazyType
from strawberry.annotation import StrawberryAnnotation
from strawberry.types.base import StrawberryList, StrawberryOptional
from strawberry.types.field import StrawberryField
from strawberry.types import Info

from strawberry_chemist import utils
from strawberry_chemist.fields.utils import drill_for_field_names
from strawberry_chemist.gql_context import SQLAlchemyContext, context_var


def camel_case(s: str):
    s = sub(r"(_|-)+", " ", s).title().replace(" ", "")
    return "".join([s[0].lower(), s[1:]])


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


class StrawberrySQLAlchemyField(StrawberryField):
    """
    Basic field, inherits StrawberryField.

    In a nutshell, handles resolving SQLAlchemy fields,
        such as: generating itself out of a strawberry field,
        and resolving sqlalchemy model fields.
    And has a bunch of common methods for all SQLAlchemy field types.
    """

    def __init__(
        self,
        sqlalchemy_name=None,
        select: Iterable[str] = None,
        graphql_name=None,
        python_name=None,
        **kwargs,
    ):
        self.sqlalchemy_name = sqlalchemy_name
        self.origin_container_type = None
        self.select_fields = tuple(select or ())
        super().__init__(graphql_name=graphql_name, python_name=python_name, **kwargs)

    @cached_property
    def needs_parent_fields(self) -> List[str]:
        if self.select_fields:
            return list(self.select_fields)
        return [field_name for field_name in [self.sqlalchemy_name] if field_name]

    @property
    def is_optional(self):
        return isinstance(self.type, StrawberryOptional)

    @property
    def is_list(self):
        return isinstance(self.type, StrawberryList) or (
            self.is_optional and isinstance(self.type.of_type, StrawberryList)
        )

    @property
    def arguments(self):
        gql_arguments = list(super().arguments)
        if not self.base_resolver:
            return gql_arguments
        if not self.select_fields:
            return gql_arguments
        hidden = {argument.python_name for argument in self.base_resolver.arguments}
        return [
            argument for argument in gql_arguments if argument.python_name not in hidden
        ]

    @classmethod
    def from_field(cls, field, sqlalchemy_type):
        if isinstance(field, cls):
            return field

        default = getattr(field, "default", getattr(field, "default", UNSET))
        new_field = cls(
            base_resolver=getattr(field, "base_resolver", None),
            default_factory=field.default_factory,
            default=default,
            sqlalchemy_name=getattr(field, "sqlalchemy_name", field.name),
            graphql_name=getattr(field, "graphql_name", None),
            python_name=field.name,
            type_annotation=field.type_annotation
            if hasattr(field, "type_annotation")
            else StrawberryAnnotation(field.type),
            select=getattr(field, "select_fields", None),
        )
        new_field.is_auto = getattr(field, "is_auto", False)
        new_field.origin_container_type = getattr(field, "origin_container_type", None)
        new_field._field_type = getattr(field, "_field_type", new_field._field_type)
        return new_field

    @cached_property
    def selected_field_value_map(self) -> Dict[str, str]:
        return {path.rsplit(".", 1)[-1]: path for path in self.select_fields}

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
        if not self.base_resolver:
            return kwargs

        kwargs = dict(kwargs or {})
        missing_arguments = []
        unresolved_arguments = [
            argument
            for argument in self.base_resolver.arguments
            if argument.python_name not in kwargs
        ]

        if relationship_value is not UNSET:
            if len(unresolved_arguments) > 1:
                raise TypeError(
                    f"Relationship field '{self.python_name}' can only inject one "
                    f"relationship argument, got {[arg.python_name for arg in unresolved_arguments]}"
                )
            if unresolved_arguments:
                kwargs[unresolved_arguments[0].python_name] = relationship_value
            return kwargs

        selected_values = {
            param_name: self._resolve_selected_value(source, path)
            for param_name, path in self.selected_field_value_map.items()
        }
        for argument in unresolved_arguments:
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
        self, source: Any, info: Info, args: List[Any], kwargs: Dict[str, Any]
    ):
        # TODO: fix the passing of info, it's not passed at all
        # TODO: come up with a way to both pass parent and the current field (e.g. anime, and genres for genresGrouped)
        if self.base_resolver:
            kwargs = self.inject_resolver_kwargs(source, kwargs)
            return super().get_result(source, info, args, kwargs)
        result = self.resolver(source, info, *args, **kwargs)
        return result

    def resolver(self, source, info: Info[SQLAlchemyContext, Any], *args, **kwargs):
        assert source is not None, (
            f"Raw StrawberrySQLAlchemyField should not be a root."
            f"You can use some sort of a connection for that."
        )
        return getattr(source, self.sqlalchemy_name)


class StrawberrySQLAlchemyRelationField(StrawberrySQLAlchemyField):
    """
    A field that resolves to a SQLAlchemy model.
    Useful for relationship-backed fields that need dataloader-backed loading.
    """

    load_simple_fields_from_sqlalchemy = True

    def __init__(
        self,
        where: Optional[Sequence[Callable[[], Any]]] = None,
        relationship_select: Optional[Iterable[str]] = None,
        load_full: bool = False,
        **kwargs,
    ):
        self.where = tuple(where or ())
        # very important field, it's set in type generation
        self.relationship_property = None
        self.relationship_select = tuple(relationship_select or ())
        self.load_full = load_full
        super().__init__(**kwargs)

    @cached_property
    def needs_parent_fields(self) -> List[str]:
        # traverse relationship property and get all local columns
        result = []
        for key in self.relationship_property.local_columns:
            result.append(key.name)
        return result

    @cached_property
    def sqlalchemy_model(self) -> DeclarativeMeta:
        type_ = utils.unwrap_type(self.type)
        type_ = utils.get_sqlalchemy_model(type_)
        # not specified explicitly in the type itself
        #   (e.g. is defined as a field in a strawberry type
        #   with scalar type, not a model type),
        #   have to find out through the relationship property
        if not type_:
            type_ = self.relationship_property.mapper.class_
        return type_

    @cached_property
    def primary_type(self):
        type_ = utils.unwrap_type(self.type)
        if isinstance(type_, LazyType):
            type_ = type_.resolve_type()

        return type_

    @cached_property
    def type_field_map(self) -> Dict[str, StrawberrySQLAlchemyField]:
        assert hasattr(self.primary_type, "__strawberry_definition__"), (
            f"Type {self.primary_type} has no __strawberry_definition__ attribute."
            f"Make sure it's a StrawberrySQLAlchemy type. Or use load='full'."
        )

        fields: List[StrawberryField] = (
            self.primary_type.__strawberry_definition__.fields
        )
        sqla_field_map = {
            f.graphql_name if f.graphql_name else camel_case(f.name): f
            for f in fields
            if isinstance(f, StrawberrySQLAlchemyField)
        }
        if self.load_simple_fields_from_sqlalchemy:
            simple_fields = {
                f.graphql_name if f.graphql_name else camel_case(f.name): f
                for f in fields
                if f.is_basic_field
            }
            sqla_field_map.update(simple_fields)
        return sqla_field_map

    def get_select_fields(self, **kwargs) -> List:
        if self.load_full:
            return inspect(self.sqlalchemy_model).c

        # restrict fields to load
        ctx = context_var.get()
        fields = ctx.field_sub_selections[self]

        fields_requested = set()
        # ask what they need only StrawberrySQLAlchemyFields
        # filter fields that are in type_field_map
        filtered = [f for f in fields if f in self.type_field_map]
        for field in filtered:
            if isinstance(self.type_field_map[field], StrawberrySQLAlchemyField):
                fields_requested.update(self.type_field_map[field].needs_parent_fields)
            elif self.type_field_map[field].is_basic_field:
                fields_requested.add(self.type_field_map[field].python_name)
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
    def arguments(self):
        gql_arguments = list(super().arguments)
        if not self.base_resolver:
            return gql_arguments
        hidden = {argument.python_name for argument in self.base_resolver.arguments}
        return [
            argument for argument in gql_arguments if argument.python_name not in hidden
        ]

    async def get_result(
        self, source: Any, info: Info, args: List[Any], kwargs: Dict[str, Any]
    ):
        # always load the related model through dataloader
        # make sure info is not duplicated
        kwargs = kwargs or {}
        result = await self.resolver(source, info, *args, **kwargs)
        # if there was a base resolver, use it
        if self.base_resolver:
            kwargs = self.inject_resolver_kwargs(
                source,
                kwargs,
                relationship_value=result,
            )
            res = StrawberryField.get_result(self, source, info, args, kwargs)
            if is_awaitable(res):
                return await res
            return res
        return result

    async def resolver(
        self, source, info: Info[SQLAlchemyContext, Any], *args, **kwargs
    ):
        assert source is not None, (
            f"Raw StrawberrySQLAlchemyRelationField for model {self.sqlalchemy_model} should not be a root."
            f"You can use some sort of a connection for that."
        )
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
    where=None,
    select=None,
    load: str = "selected",
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
        load_full=load == "full",
        **kwargs,
    )
    if resolver:
        return field_(resolver)
    return field_
