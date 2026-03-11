from dataclasses import astuple
from functools import cached_property
from typing import Any, List

from sqlalchemy.orm import DeclarativeMeta
from strawberry.types.arguments import StrawberryArgument
from strawberry.types import Info

from strawberry_chemist import utils
from strawberry_chemist.fields.field import StrawberrySQLAlchemyRelationField
from strawberry_chemist.fields.utils import drill_for_field_names
from strawberry_chemist.filters import FilterDefinition
from strawberry_chemist.gql_context import SQLAlchemyContext
from strawberry_chemist.order import OrderDefinition
from strawberry_chemist.pagination.base import (
    GenericPaginationReturnType,
    PaginationPolicy,
    is_flat_pagination_policy,
)


class SQLAlchemyBaseConnectionField(StrawberrySQLAlchemyRelationField):
    pagination: PaginationPolicy[Any, Any, Any]
    order: OrderDefinition = None
    filter: FilterDefinition = None

    def __init__(self, order=None, filter=None, default_order_by=None, **kwargs):
        self.order = order
        self.filter = filter
        self.default_order_by = default_order_by
        self.relationship_property = None
        super().__init__(**kwargs)

    @cached_property
    def sqlalchemy_model(self) -> DeclarativeMeta:
        type_ = self.primary_type
        type_ = utils.unwrap_type(type_)
        type_ = utils.get_sqlalchemy_model(type_)
        if not type_:
            type_ = self.relationship_property.mapper.class_
        return type_

    @cached_property
    def primary_type(self):
        unwrapped_type = utils.unwrap_type(self.type)
        type_var = unwrapped_type.__strawberry_definition__.type_var_map
        return type_var[GenericPaginationReturnType.__name__]

    async def resolver(
        self, source, info: Info[SQLAlchemyContext, Any], *args, **kwargs
    ):
        selections = self.pagination.get_fields_from_typed_request(info.selected_fields)
        # filter selections to those which has name attribute
        #  (e.g. not InlineFragment)
        # names = [s.name for s in selections if hasattr(s, 'name')]
        names = list(drill_for_field_names(selections))
        info.context.field_sub_selections[self].update(names)

        order, filters = None, None
        if is_flat_pagination_policy(self.pagination):
            pagination = self.pagination.extract_pagination_kwargs(kwargs)
        else:
            pagination = kwargs.get(self.pagination.python_name)
        loader_pagination = pagination
        if self.order:
            order = kwargs.get(self.order.python_name)
        if self.filter:
            filters = kwargs.get(self.filter.python_name)

        p_tuple = self.pagination.cache_key(pagination)
        if self.order and hasattr(self.order, "cache_key"):
            o_tuple = self.order.cache_key(order)
            loader_order = order
        else:
            o_tuple = astuple(order) if order else None
            loader_order = o_tuple
        if self.filter and hasattr(self.filter, "cache_key"):
            f_tuple = self.filter.cache_key(filters)
            loader_filters = filters
        else:
            f_tuple = tuple(filters.__dict__.items()) if filters else None
            loader_filters = f_tuple
        # if source is not None:
        result = await info.context.dataloader_container.get_dataloader(
            field=self,
            options=(o_tuple, p_tuple, f_tuple),
            loader_options=(loader_order, loader_pagination, loader_filters),
        ).load(source)
        # else:
        #     result = await info.context.dataloader_container.get_dataloader(
        #         field=self, options=(o_tuple, p_tuple, f_tuple)
        #     ).load()
        return result

    @property
    def arguments(self) -> List[StrawberryArgument]:
        gql_arguments = []
        # if self.filters:
        #     gql_arguments.append(self.filters.argument)
        if self.pagination:
            if is_flat_pagination_policy(self.pagination):
                gql_arguments.extend(self.pagination.arguments)
            else:
                gql_arguments.append(self.pagination.argument)
        if self.order:
            gql_arguments.append(self.order.argument)
        if self.filter:
            gql_arguments.append(self.filter.argument)
        return gql_arguments
