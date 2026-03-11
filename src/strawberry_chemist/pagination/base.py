from __future__ import annotations

from typing import Any, Hashable, Protocol, TypeGuard, TypeVar, runtime_checkable

from sqlalchemy.sql import Select
from strawberry.arguments import StrawberryArgument
from strawberry.types.nodes import SelectedField


PageInputType = TypeVar("PageInputType")
GenericPaginationReturnType = TypeVar("GenericPaginationReturnType")
PaginationResultType = TypeVar("PaginationResultType")


@runtime_checkable
class PaginationPolicy(
    Protocol[PageInputType, GenericPaginationReturnType, PaginationResultType]
):
    def get_fields_from_typed_request(
        self,
        selected_fields: list[SelectedField],
    ) -> list[SelectedField]: ...

    def cache_key(self, page: PageInputType) -> Hashable: ...

    def paginate_query(self, query: Select, page: PageInputType) -> Select: ...

    def paginate_result(
        self,
        result: list[GenericPaginationReturnType],
        **kwargs: Any,
    ) -> PaginationResultType: ...


@runtime_checkable
class FlatPaginationPolicy(
    PaginationPolicy[PageInputType, GenericPaginationReturnType, PaginationResultType],
    Protocol[PageInputType, GenericPaginationReturnType, PaginationResultType],
):
    @property
    def arguments(self) -> list[StrawberryArgument]: ...

    def extract_pagination_kwargs(self, kwargs: dict[str, Any]) -> PageInputType: ...


@runtime_checkable
class NestedPaginationPolicy(
    PaginationPolicy[PageInputType, GenericPaginationReturnType, PaginationResultType],
    Protocol[PageInputType, GenericPaginationReturnType, PaginationResultType],
):
    python_name: str

    @property
    def argument(self) -> StrawberryArgument: ...


@runtime_checkable
class CountedPaginationPolicy(
    PaginationPolicy[PageInputType, GenericPaginationReturnType, PaginationResultType],
    Protocol[PageInputType, GenericPaginationReturnType, PaginationResultType],
):
    include_total_count: bool

    def count_query(self, query: Select) -> Select: ...


def is_flat_pagination_policy(
    pagination: object,
) -> TypeGuard[FlatPaginationPolicy[Any, Any, Any]]:
    return hasattr(pagination, "arguments")
