import enum
from abc import ABC, abstractmethod
from typing import Tuple, List, TypeVar, Generic, Dict, Any, Optional, Callable

import strawberry
from sqlalchemy import desc, asc
from sqlalchemy.sql import Select, nullslast
from strawberry import UNSET
from strawberry.annotation import StrawberryAnnotation
from strawberry.arguments import StrawberryArgument
from strawberry.type import StrawberryType


class StrawberrySQLAlchemyOrderingBase(ABC):
    python_name: str
    gql_name: str
    default: StrawberryType
    argument_type: type(StrawberryType)

    def __init__(
        self, python_name="order", gql_name="order", default=UNSET, required=False
    ):
        self.python_name = python_name
        self.gql_name = gql_name
        self.default = default
        self.required = required

    @property
    def argument(self) -> StrawberryArgument:
        ann = self.argument_type if self.required else Optional[self.argument_type]
        return StrawberryArgument(
            default=self.default,
            description=None,
            graphql_name=self.gql_name,
            python_name=self.python_name,
            type_annotation=StrawberryAnnotation(ann),
        )

    @abstractmethod
    def order_query(
        self,
        query: Select,
        order: Tuple,
    ) -> Select:
        raise NotImplemented


@strawberry.enum
class OrderAD(enum.Enum):
    ASC = "asc"
    DESC = "desc"


FieldName = TypeVar("FieldName")


@strawberry.input
class Order(Generic[FieldName]):
    field: FieldName
    order: OrderAD


# class FieldOrder(StrawberrySQLAlchemyOrderingBase):
#     field_map: Dict[str, InstrumentedAttribute] = {}
#
#     def __init__(
#         self,
#         fields: List[Any],
#         enum_name=None,
#         python_name="order",
#         gql_name="order",
#         default=UNSET,
#     ):
#         """
#
#         :param fields: Fields allowed to order by
#         :param enum_name: The to-be-generated enum's name (the field enum)
#         :param python_name: Argument name in python
#         :param gql_name: Argument name in gql
#         :param default: The default value, probably not worth
#         """
#         d = {}
#         for field in fields:
#             f = field.key
#             d[f.upper()] = f.lower()
#             self.field_map[f.lower()] = field
#
#         if not enum_name:
#             enum_name = f"{fields[0].class_.__name__}Enum"
#         e = enum.Enum(enum_name, d)
#         e = strawberry.enum(e)
#         self.argument_type = Order[e]
#
#         super().__init__(python_name, gql_name, default)
#
#     def order_query(self, query: Select, order: Tuple) -> Select:
#         field, order = order
#         field = self.field_map[field.value]
#
#         to_ord = field.asc()
#         if order == OrderAD.DESC:
#             to_ord = field.desc()
#
#         return query.order_by(to_ord)


class StrawberrySQLAlchemyOrdering(StrawberrySQLAlchemyOrderingBase):
    input_values: List[str]

    def __init__(
        self,
        input_type: type(StrawberryType),
        resolve_ordering_map: Dict[Any, Callable],
        input_validator: Callable[[Any], Any] = None,
        python_name="order",
        gql_name="order",
        required=False,
        **kwargs,
    ):
        self.argument_type = input_type
        self.resolve_ordering_map: Dict[Any, Callable] = resolve_ordering_map
        self.input_values = [k.value for k in resolve_ordering_map.keys()]
        self.input_validator = input_validator
        self.sanity_check()
        super().__init__(python_name, gql_name, required=required, **kwargs)

    def order_query(self, query: Select, order: Tuple) -> Select:
        k, v = order
        query, field = self.resolve_ordering_map[k](query=query)
        if v == OrderAD.DESC:
            query = query.order_by(nullslast(desc(field)))
        elif v == OrderAD.ASC:
            query = query.order_by(nullslast(asc(field)))
        return query

    def sanity_check(self):
        # get field named "field" from input's fields array
        field = next(
            (field for field in self.argument_type.__strawberry_definition__.fields if field.name == "field"),
            None,
        )
        if not field:
            raise ValueError(
                "Input type must have a field named 'field' to order by"
            )
        # iterate over input field possible values and check if they are in the map
        for value in field.type.values:
            if value.value not in self.input_values:
                raise ValueError(
                    f"Input type's field 'field' has a value '{value.value}' that is not in the map"
                )
