from __future__ import annotations

from typing import Any, Hashable, Protocol, TypeVar, runtime_checkable

from sqlalchemy.sql import Select
from strawberry.types.arguments import StrawberryArgument
from strawberry.types.nodes import SelectedField
from typing_extensions import TypeIs


PageInputType = TypeVar("PageInputType")
PageInputContraType = TypeVar("PageInputContraType", contravariant=True)
GenericPaginationReturnType = TypeVar("GenericPaginationReturnType")
PaginationResultType = TypeVar("PaginationResultType", covariant=True)


@runtime_checkable
class PaginationPolicy(
    Protocol[
        PageInputContraType,
        GenericPaginationReturnType,
        PaginationResultType,
    ]
):
    def get_fields_from_typed_request(
        self,
        selected_fields: list[SelectedField],
    ) -> list[SelectedField]: ...

    def cache_key(self, page: PageInputContraType) -> Hashable: ...

    def paginate_query(self, query: Select, page: PageInputContraType) -> Select: ...

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
    PaginationPolicy[
        PageInputContraType,
        GenericPaginationReturnType,
        PaginationResultType,
    ],
    Protocol[
        PageInputContraType,
        GenericPaginationReturnType,
        PaginationResultType,
    ],
):
    python_name: str

    @property
    def argument(self) -> StrawberryArgument: ...


@runtime_checkable
class CountedPaginationPolicy(
    PaginationPolicy[
        PageInputContraType,
        GenericPaginationReturnType,
        PaginationResultType,
    ],
    Protocol[
        PageInputContraType,
        GenericPaginationReturnType,
        PaginationResultType,
    ],
):
    include_total_count: bool

    def count_query(self, query: Select) -> Select: ...


def is_flat_pagination_policy(
    pagination: PaginationPolicy[Any, Any, Any],
) -> TypeIs[FlatPaginationPolicy[Any, Any, Any]]:
    return hasattr(pagination, "arguments")


def is_nested_pagination_policy(
    pagination: PaginationPolicy[Any, Any, Any],
) -> TypeIs[NestedPaginationPolicy[Any, Any, Any]]:
    return hasattr(pagination, "argument") and hasattr(pagination, "python_name")
