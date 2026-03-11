from __future__ import annotations

import base64
from contextvars import ContextVar
from typing import Any, Generic, Optional, TypeAlias

import strawberry
from sqlalchemy import false
from sqlalchemy.sql import Select
from strawberry.annotation import StrawberryAnnotation
from strawberry.types.arguments import StrawberryArgument
from strawberry.types.nodes import SelectedField

from strawberry_chemist.fields.utils import find_selected_field, iter_selected_fields
from strawberry_chemist.pagination.base import GenericPaginationReturnType

ABSOLUTE_MAX_LIMIT = 40
DEFAULT_MAX_LIMIT = 20
context_first: ContextVar[int] = ContextVar("context_first")
context_after: ContextVar[int | None] = ContextVar("context_after")


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
    hasPreviousPage: bool = False


@strawberry.type
class Edge(Generic[GenericPaginationReturnType]):
    node: GenericPaginationReturnType
    cursor: str


@strawberry.type
class RelayConnection(Generic[GenericPaginationReturnType]):
    edges: list[Edge[GenericPaginationReturnType]] = strawberry.field(
        default_factory=list
    )
    pageInfo: PageInfo


Connection = RelayConnection


CursorPageInput: TypeAlias = tuple[int, Optional[str]] | CursorPaginationInput | None


class CursorPagination:
    def __init__(
        self,
        max_limit: int = DEFAULT_MAX_LIMIT,
        default_limit: int = 5,
        *,
        nested: bool = False,
        name: str = "pagination",
        python_name: str | None = None,
    ):
        self.max_limit = max_limit
        self.default_limit = default_limit
        self.nested = nested
        self.graphql_name = name
        self.python_name = python_name or name

    @property
    def arguments(self) -> list[StrawberryArgument]:
        if self.nested:
            raise AttributeError(
                "Nested cursor pagination exposes a single `argument`."
            )
        return [
            StrawberryArgument(
                python_name="first",
                graphql_name="first",
                type_annotation=StrawberryAnnotation(int),
                default=self.default_limit,
            ),
            StrawberryArgument(
                python_name="after",
                graphql_name="after",
                type_annotation=StrawberryAnnotation(Optional[str]),
                default=None,
            ),
        ]

    @property
    def argument(self) -> StrawberryArgument:
        if not self.nested:
            raise AttributeError(
                "Flat cursor pagination exposes top-level `arguments`."
            )
        return StrawberryArgument(
            python_name=self.python_name,
            graphql_name=self.graphql_name,
            type_annotation=StrawberryAnnotation(Optional[CursorPaginationInput]),
            default=strawberry.UNSET,
        )

    @staticmethod
    def get_fields_from_typed_request(
        selected_fields: list[SelectedField],
    ) -> list[SelectedField]:
        edges = find_selected_field(selected_fields[0].selections, "edges")
        if edges is None:
            return []
        node = find_selected_field(edges.selections, "node")
        if node is None:
            return []
        return list(iter_selected_fields(node.selections))

    def extract_pagination_kwargs(
        self, kwargs: dict[str, Any]
    ) -> tuple[int, Optional[str]]:
        return kwargs.get("first", self.default_limit), kwargs.get("after")

    def cache_key(self, page: CursorPageInput) -> tuple[int, Optional[str]]:
        return self.normalize_page(page)

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

    def normalize_page(self, page: CursorPageInput) -> tuple[int, Optional[str]]:
        if page is None:
            return self.default_limit, None
        if isinstance(page, tuple):
            return page
        return page.first, page.after

    def paginate_query(self, query: Select, page: CursorPageInput) -> Select:
        first, after = self.normalize_page(page)
        first = min(first, self.max_limit)
        first = max(first, 1)
        context_first.set(first)
        after_offset = self.offset_from_cursor(after)
        context_after.set(after_offset)
        if after_offset is None:
            return query.where(false())
        return query.limit(first + 1).offset(after_offset)

    def paginate_result(
        self,
        result: list[GenericPaginationReturnType],
        **_: Any,
    ) -> RelayConnection[GenericPaginationReturnType]:
        edges: list[Edge[GenericPaginationReturnType]] = []
        num_to_return = min(len(result), context_first.get())
        skipped = context_after.get()
        if skipped is None:
            skipped = 0

        for index, offset in zip(
            range(num_to_return),
            range(skipped, skipped + num_to_return),
        ):
            edges.append(
                Edge(node=result[index], cursor=self.cursor_from_offset(offset + 1))
            )

        return RelayConnection(
            edges=edges,
            pageInfo=PageInfo(
                startCursor=edges[0].cursor if edges else None,
                endCursor=edges[-1].cursor if edges else None,
                hasNextPage=len(result) > num_to_return,
                hasPreviousPage=skipped > 0,
            ),
        )
