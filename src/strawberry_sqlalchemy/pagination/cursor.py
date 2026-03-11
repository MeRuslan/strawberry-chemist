import base64
from contextvars import ContextVar
from typing import Any, List, Generic, Tuple, Optional

import strawberry
from sqlalchemy.sql import Select
from strawberry import UNSET
from strawberry.types.nodes import SelectedField

from strawberry_sqlalchemy.pagination.base import (
    StrawberrySQLAlchemyPaginationBase,
    GenericPaginationReturnType,
)

ABSOLUTE_MAX_LIMIT = 40
DEFAULT_MAX_LIMIT = 20
context_first: ContextVar[int] = ContextVar("context_first")
context_after: ContextVar[Any] = ContextVar("context_after")


@strawberry.input
class CursorPaginationInput:
    first: int = 5
    after: Optional[str] = None

    def __init__(self, *args, **kwargs):
        assert not args, "CursorPaginationInput does not accept positional arguments"
        self.first = kwargs.get("first", 5)
        self.after = kwargs.get("after", None)
        if self.first > ABSOLUTE_MAX_LIMIT:
            self.first = ABSOLUTE_MAX_LIMIT


@strawberry.type
class PageInfo:
    startCursor: Optional[str]
    endCursor: Optional[str]
    hasNextPage: bool = False


@strawberry.type
class Edge(Generic[GenericPaginationReturnType]):
    node: GenericPaginationReturnType
    cursor: str


@strawberry.type
class RelayConnection(Generic[GenericPaginationReturnType]):
    edges: List[Edge[GenericPaginationReturnType]] = tuple()
    pageInfo: PageInfo


empty_relay_connection = RelayConnection(
    edges=[], pageInfo=PageInfo(startCursor="", endCursor="", hasNextPage=False)
)


class StrawberrySQLAlchemyCursorPagination(StrawberrySQLAlchemyPaginationBase):
    """
    Cursor pagination class.
    Is the typical limit-offset under the hood.
    TODO: use the real cursor when applicable
    """

    max_limit: int
    argument_type = CursorPaginationInput

    def __init__(
        self,
        max_limit: int = DEFAULT_MAX_LIMIT,
        python_name: str = "pagination",
        gql_name: str = "pagination",
    ):
        self.max_limit = max_limit
        super().__init__(python_name=python_name, gql_name=gql_name, default=UNSET)

    def get_fields_from_typed_request(self, selected_fields: List[SelectedField]):
        # filter to field named edges
        edges = [
            field for field in selected_fields[0].selections if field.name == "edges"
        ]
        if not edges:
            return []
        # filter to field named node
        nodes = [field for field in edges[0].selections if field.name == "node"]
        if not nodes:
            return []
        return nodes[0].selections

    @staticmethod
    def cursor_from_offset(offset: int) -> str:
        return base64.b64encode(str(offset).encode("UTF-8")).decode("UTF-8")

    @staticmethod
    def offset_from_cursor(cursor: Optional[str]) -> Optional[int]:
        if cursor is None:
            return 0
        try:
            return int(base64.decodebytes(cursor.encode("UTF-8")))
        except ValueError:
            return None

    def paginate_query(self, query: Select, page: Tuple) -> Select:
        first, after = page
        first = min(first, self.max_limit)
        first = max(first, 1)
        context_first.set(first)
        after = self.offset_from_cursor(after)
        context_after.set(after)
        if after is None:
            stmt = query.where(False)
        else:
            stmt = query.limit(first + 1).offset(after)
        return stmt

    def paginate_result(
        self, result: List[GenericPaginationReturnType]
    ) -> RelayConnection[GenericPaginationReturnType]:
        edges = []
        num_to_return = min(len(result), context_first.get())
        skipped = context_after.get()
        # can't do math on None
        if skipped is None:
            skipped = 0

        for i, offset in zip(
            range(num_to_return), range(skipped, skipped + num_to_return)
        ):
            edges.append(
                Edge(node=result[i], cursor=self.cursor_from_offset(offset + 1))
            )

        return RelayConnection(
            edges=edges,
            pageInfo=PageInfo(
                startCursor=edges[0].cursor if edges else None,
                endCursor=edges[-1].cursor if edges else None,
                hasNextPage=len(result) > num_to_return,
            ),
        )

    # async def paginate(
    #     self,
    #     connection: Any,
    #     select_query: Select,
    #     page: Tuple[int, int],
    #     info: Info[SQLAlchemyContext, Any],
    # ) -> RelayConnection[GenericPaginationReturnType]:
    #     stmt = self.paginate_query(select_query, page)
    #
    #     async with info.context.get_session() as session:
    #         objects = (await session.execute(stmt)).scalars().all()
    #         res = self.paginate_result(objects)
    #     return res
