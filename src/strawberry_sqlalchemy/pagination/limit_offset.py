from typing import List, Generic, Tuple

import strawberry
from sqlalchemy.sql import Select
from strawberry.types.nodes import SelectedField

from strawberry_sqlalchemy.pagination.base import (
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
