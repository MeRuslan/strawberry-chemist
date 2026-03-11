from dataclasses import asdict, astuple
from functools import cached_property
from typing import Any, List

from sqlalchemy.orm import DeclarativeMeta
from strawberry.arguments import StrawberryArgument
from strawberry.types import Info

from strawberry_chemist import utils
from strawberry_chemist.fields.field import StrawberrySQLAlchemyRelationField
from strawberry_chemist.fields.utils import drill_for_field_names
from strawberry_chemist.filters import StrawberrySQLAlchemyFilterBase
from strawberry_chemist.gql_context import SQLAlchemyContext
from strawberry_chemist.order import StrawberrySQLAlchemyOrderingBase
from strawberry_chemist.pagination import StrawberrySQLAlchemyPaginationBase
from strawberry_chemist.pagination.base import GenericPaginationReturnType


class SQLAlchemyBaseConnectionField(StrawberrySQLAlchemyRelationField):
    pagination: StrawberrySQLAlchemyPaginationBase
    order: StrawberrySQLAlchemyOrderingBase = None
    filter: StrawberrySQLAlchemyFilterBase = None

    def __init__(self, order=None, filter=None, **kwargs):
        self.order = order
        self.filter = filter
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
        pagination = kwargs.get(self.pagination.python_name)
        if self.order:
            order = kwargs.get(self.order.python_name)
        if self.filter:
            filters = kwargs.get(self.filter.python_name)

        p_tuple = astuple(pagination)
        o_tuple = astuple(order) if order else None
        f_tuple = tuple(asdict(filters).items()) if filters else None
        # if source is not None:
        result = await info.context.dataloader_container.get_dataloader(
            field=self, options=(o_tuple, p_tuple, f_tuple)
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
            gql_arguments.append(self.pagination.argument)
        if self.order:
            gql_arguments.append(self.order.argument)
        if self.filter:
            gql_arguments.append(self.filter.argument)
        return gql_arguments
