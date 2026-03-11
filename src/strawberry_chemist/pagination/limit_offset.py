from __future__ import annotations

from typing import Any, Generic, TypeAlias

import strawberry
from sqlalchemy import func, select
from sqlalchemy.sql import Select
from strawberry.annotation import StrawberryAnnotation
from strawberry.types.arguments import StrawberryArgument
from strawberry.types.nodes import SelectedField

from strawberry_chemist.pagination.base import GenericPaginationReturnType

DEFAULT_MAX_LIMIT = 20


@strawberry.input
class LimitOffsetPaginationInput:
    offset: int = 0
    limit: int = -1


@strawberry.type
class OffsetConnection(Generic[GenericPaginationReturnType]):
    items: list[GenericPaginationReturnType]
    totalCount: int = 0


OffsetPageInput: TypeAlias = tuple[int, int] | LimitOffsetPaginationInput | None


class OffsetPagination:
    def __init__(
        self,
        default_limit: int = DEFAULT_MAX_LIMIT,
        max_limit: int = DEFAULT_MAX_LIMIT,
        *,
        nested: bool = False,
        name: str = "pagination",
        python_name: str | None = None,
    ):
        self.default_limit = default_limit
        self.max_limit = max_limit
        self.nested = nested
        self.graphql_name = name
        self.python_name = python_name or name
        self.include_total_count = True

    @property
    def arguments(self) -> list[StrawberryArgument]:
        if self.nested:
            raise AttributeError(
                "Nested offset pagination exposes a single `argument`."
            )
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

    @property
    def argument(self) -> StrawberryArgument:
        if not self.nested:
            raise AttributeError(
                "Flat offset pagination exposes top-level `arguments`."
            )
        return StrawberryArgument(
            python_name=self.python_name,
            graphql_name=self.graphql_name,
            type_annotation=StrawberryAnnotation(LimitOffsetPaginationInput | None),
            default=strawberry.UNSET,
        )

    @staticmethod
    def get_fields_from_typed_request(
        selected_fields: list[SelectedField],
    ) -> list[SelectedField]:
        items = [
            field for field in selected_fields[0].selections if field.name == "items"
        ]
        if not items:
            return []
        return items[0].selections

    def extract_pagination_kwargs(self, kwargs: dict[str, int]) -> tuple[int, int]:
        return kwargs.get("limit", self.default_limit), kwargs.get("offset", 0)

    def normalize_page(self, page: OffsetPageInput) -> tuple[int, int]:
        if page is None:
            return self.default_limit, 0
        if isinstance(page, tuple):
            return page
        return page.limit, page.offset

    def cache_key(self, page: OffsetPageInput) -> tuple[int, int]:
        return self.normalize_page(page)

    def paginate_query(self, query: Select, page: OffsetPageInput) -> Select:
        limit, offset = self.normalize_page(page)
        limit = min(limit, self.max_limit)
        limit = max(limit, 1)
        offset = max(offset, 0)
        return query.limit(limit).offset(offset)

    @staticmethod
    def count_query(query: Select) -> Select:
        return select(func.count()).select_from(query.order_by(None).subquery())

    def paginate_result(
        self,
        result: list[GenericPaginationReturnType],
        *,
        total_count: int = 0,
        **_: Any,
    ) -> OffsetConnection[GenericPaginationReturnType]:
        return OffsetConnection(items=result, totalCount=total_count)
