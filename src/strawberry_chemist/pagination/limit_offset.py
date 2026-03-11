from typing import List, Generic, Tuple

import strawberry
from sqlalchemy import func, select
from sqlalchemy.sql import Select
from strawberry.annotation import StrawberryAnnotation
from strawberry.arguments import StrawberryArgument
from strawberry.types.nodes import SelectedField

from strawberry_chemist.pagination.base import (
    StrawberrySQLAlchemyPaginationBase,
    GenericPaginationReturnType,
)

DEFAULT_MAX_LIMIT = 20


@strawberry.input
class LimitOffsetPaginationInput:
    offset: int = 0
    limit: int = -1


@strawberry.type
class LimitOffsetPaginationOutput(Generic[GenericPaginationReturnType]):
    objects: List[GenericPaginationReturnType]
    count: int = 0


@strawberry.type
class OffsetConnection(Generic[GenericPaginationReturnType]):
    items: List[GenericPaginationReturnType]
    totalCount: int = 0


class StrawberrySQLAlchemyLimitOffsetPagination(StrawberrySQLAlchemyPaginationBase):
    def get_fields_from_typed_request(self, selected_fields: List[SelectedField]):
        raise NotImplementedError

    max_limit: int
    argument_type = LimitOffsetPaginationInput

    def __init__(
        self,
        max_limit: int = DEFAULT_MAX_LIMIT,
        python_name: str = "pagination",
        gql_name: str = "pagination",
        default: LimitOffsetPaginationInput = LimitOffsetPaginationInput(
            offset=0, limit=DEFAULT_MAX_LIMIT
        ),
    ):
        self.max_limit = max_limit
        super(StrawberrySQLAlchemyLimitOffsetPagination, self).__init__(
            python_name=python_name, gql_name=gql_name, default=default
        )

    def paginate_query(self, query: Select, page: Tuple) -> Select:
        offset, limit = page
        limit = min(limit, self.max_limit)
        limit = max(limit, 1)
        offset = max(offset, 0)

        stmt = query.limit(limit).offset(offset)
        return stmt

    def paginate_result(
        self, result: List[GenericPaginationReturnType], count: int = -1
    ) -> LimitOffsetPaginationOutput[GenericPaginationReturnType]:
        return LimitOffsetPaginationOutput(objects=result, count=count)


class OffsetPagination:
    def __init__(
        self,
        default_limit: int = DEFAULT_MAX_LIMIT,
        max_limit: int = DEFAULT_MAX_LIMIT,
    ):
        self.default_limit = default_limit
        self.max_limit = max_limit
        self.include_total_count = True

    @property
    def arguments(self) -> list[StrawberryArgument]:
        return [
            StrawberryArgument(
                python_name="limit",
                graphql_name="limit",
                type_annotation=StrawberryAnnotation(int),
                default=self.default_limit,
            ),
            StrawberryArgument(
                python_name="offset",
                graphql_name="offset",
                type_annotation=StrawberryAnnotation(int),
                default=0,
            ),
        ]

    @staticmethod
    def get_fields_from_typed_request(selected_fields: List[SelectedField]):
        items = [
            field for field in selected_fields[0].selections if field.name == "items"
        ]
        if not items:
            return []
        return items[0].selections

    def extract_pagination_kwargs(self, kwargs: dict[str, int]) -> Tuple[int, int]:
        return kwargs.get("limit", self.default_limit), kwargs.get("offset", 0)

    @staticmethod
    def cache_key(page: Tuple[int, int]) -> Tuple[int, int]:
        return page

    def paginate_query(self, query: Select, page: Tuple[int, int]) -> Select:
        limit, offset = page
        limit = min(limit, self.max_limit)
        limit = max(limit, 1)
        offset = max(offset, 0)
        return query.limit(limit).offset(offset)

    @staticmethod
    def count_query(query: Select) -> Select:
        return select(func.count()).select_from(query.order_by(None).subquery())

    def paginate_result(
        self,
        result: List[GenericPaginationReturnType],
        *,
        total_count: int = 0,
        **_: int,
    ) -> OffsetConnection[GenericPaginationReturnType]:
        return OffsetConnection(items=result, totalCount=total_count)
