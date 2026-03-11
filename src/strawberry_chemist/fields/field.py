from functools import cached_property
from re import sub
from typing import Any, List, Dict, Optional, Iterable

from graphql.pyutils import is_awaitable
from sqlalchemy import inspect
from sqlalchemy.orm import DeclarativeMeta
from strawberry import UNSET, LazyType
from strawberry.annotation import StrawberryAnnotation
from strawberry.field import StrawberryField
from strawberry.type import StrawberryOptional, StrawberryList
from strawberry.types import Info

from strawberry_chemist import utils
from strawberry_chemist.fields.utils import drill_for_field_names
from strawberry_chemist.filters.pre_filter import RuntimeFilter
from strawberry_chemist.gql_context import SQLAlchemyContext, context_var


def camel_case(s: str):
    s = sub(r"(_|-)+", " ", s).title().replace(" ", "")
    return "".join([s[0].lower(), s[1:]])


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
        post_processor=None,
        sqlalchemy_name=None,
        additional_parent_fields: Iterable[str] = None,
        graphql_name=None,
        python_name=None,
        **kwargs,
    ):
        self.sqlalchemy_name = sqlalchemy_name
        self.post_processor = post_processor
        self.origin_container_type = None
        self.needs_p_fields = additional_parent_fields
        super().__init__(graphql_name=graphql_name, python_name=python_name, **kwargs)

    @cached_property
    def needs_parent_fields(self) -> List[str]:
        l_f = [self.sqlalchemy_name]
        if self.needs_p_fields:
            l_f = l_f + list(self.needs_p_fields)
        return l_f

    @property
    def is_optional(self):
        return isinstance(self.type, StrawberryOptional)

    @property
    def is_list(self):
        return isinstance(self.type, StrawberryList) or (
            self.is_optional and isinstance(self.type.of_type, StrawberryList)
        )

    @classmethod
    def from_field(cls, field, sqlalchemy_type):
        if isinstance(field, StrawberrySQLAlchemyField):
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
        )
        new_field.is_auto = getattr(field, "is_auto", False)
        new_field.origin_container_type = getattr(field, "origin_container_type", None)
        return new_field

    def get_result(
        self, source: Any, info: Info, args: List[Any], kwargs: Dict[str, Any]
    ):
        # TODO: fix the passing of info, it's not passed at all
        # TODO: come up with a way to both pass parent and the current field (e.g. anime, and genres for genresGrouped)
        if self.base_resolver:
            return super().get_result(source, info, args, kwargs)
        result = self.resolver(source, info, *args, **kwargs)

        if self.post_processor:
            result = self.post_processor(source, result)
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
    Useful for relations, dds pre_filter argument, which will filter the relationship for you.
    """

    load_simple_fields_from_sqlalchemy = True

    def __init__(
        self,
        pre_filter: Optional[RuntimeFilter] = None,
        needs_fields=None,
        ignore_field_selections=False,
        **kwargs,
    ):
        self.pre_filter = pre_filter
        # very important field, it's set in type generation
        self.relationship_property = None
        self.needs_fields = needs_fields or []
        self.load_full = ignore_field_selections
        self.default_order_by = kwargs.pop("default_order_by", None)
        super().__init__(**kwargs)

    @cached_property
    def needs_parent_fields(self) -> List[str]:
        # traverse relationship property and get all local columns
        result = []
        for key in self.relationship_property.local_columns:
            result.append(key.name)
        # result.extend(super().needs_parent_fields)
        if self.needs_p_fields:
            result.extend(self.needs_p_fields)
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
            f"Make sure it's a StrawberrySQLAlchemy type. Or use ignore_field_selections=True."
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
        fields_requested.update(self.needs_fields)
        selections = [
            getattr(self.sqlalchemy_model, field_iter)
            for field_iter in fields_requested
            if field_iter
        ]
        return selections

    @property
    def is_basic_field(self) -> bool:
        return False

    async def get_result(
        self, source: Any, info: Info, args: List[Any], kwargs: Dict[str, Any]
    ):
        # always load the related model through dataloader
        # make sure info is not duplicated
        kwargs = kwargs or {}
        kwargs["info"] = info
        result = await self.resolver(source, *args, **kwargs)
        # if there was a base resolver, use it
        if self.base_resolver:
            kwargs["root"] = result  # put fetched value into kwargs as root
            res = super().get_result(result, info, args, kwargs)
            if is_awaitable(res):
                return await res
            return res
        if self.post_processor:
            result = self.post_processor(source, result)
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
    post_processor=None,
    additional_parent_fields=None,
    *,
    name=None,
    sqlalchemy_name=None,
    default=UNSET,
    **kwargs,
):
    # TODO: fix default, it doesn't work
    field_ = StrawberrySQLAlchemyField(
        post_processor=post_processor,
        python_name=None,
        graphql_name=name,
        type_annotation=None,
        sqlalchemy_name=sqlalchemy_name,
        additional_parent_fields=additional_parent_fields,
        default=default,
        **kwargs,
    )
    if resolver:
        return field_(resolver)
    return field_


def relation_field(
    resolver=None,
    post_processor=None,
    pre_filter=None,
    modifier=None,
    needs_fields=None,
    ignore_field_selections=None,
    *,
    name=None,
    sqlalchemy_name=None,
    default=UNSET,
    **kwargs,
):
    field_ = StrawberrySQLAlchemyRelationField(
        post_processor=post_processor,
        pre_filter=pre_filter,
        python_name=None,
        graphql_name=name,
        type_annotation=None,
        sqlalchemy_name=sqlalchemy_name,
        default=default,
        needs_fields=needs_fields,
        ignore_field_selections=ignore_field_selections,
        **kwargs,
    )
    if resolver:
        return field_(resolver)
    return field_


# ditched as it's unusable, needs refactoring of base class
# def exists_relation_field(
#     resolver=None,
#     post_processor=None,
#     pre_filter=None,
#     *,
#     name=None,
#     sqlalchemy_name=None,
#     default=UNSET,
#     **kwargs,
# ):
#     field_ = StrawberrySQLAlchemyExistsRelationField(
#         post_processor=post_processor,
#         pre_filter=pre_filter,
#         python_name=None,
#         graphql_name=name,
#         type_annotation=None,
#         sqlalchemy_name=sqlalchemy_name,
#         default=default,
#         **kwargs,
#     )
#     if resolver:
#         return field_(resolver)
#     return field_
