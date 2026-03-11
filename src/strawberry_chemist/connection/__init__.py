from __future__ import annotations

from typing import Optional

from strawberry import UNSET

from strawberry_chemist.connection.base import SQLAlchemyBaseConnectionField
from strawberry_chemist.filters.pre_filter import RuntimeFilter
from strawberry_chemist.pagination import CursorPagination


def _normalize_where_clause(where):
    if where is None:
        return None
    if isinstance(where, RuntimeFilter):
        return where
    filters = where if isinstance(where, list) else [where]
    return RuntimeFilter(filters)


def _resolve_filter(filter_definition):
    if filter_definition is None:
        return None
    return getattr(filter_definition, "__sc_filter_definition__", filter_definition)


def _resolve_order(order_definition):
    if order_definition is None:
        return None
    return getattr(order_definition, "__sc_order_definition__", order_definition)


class SQLAlchemyConnectionField(SQLAlchemyBaseConnectionField):
    def __init__(self, *, pagination=None, filter=None, order=None, **kwargs):
        self.pagination = pagination or CursorPagination()
        super().__init__(
            order=_resolve_order(order),
            filter=_resolve_filter(filter),
            **kwargs,
        )


def connection(
    *,
    source: Optional[str] = None,
    where=None,
    filter=None,
    order=None,
    pagination=None,
    name=None,
    sqlalchemy_name=None,
    default=UNSET,
    **kwargs,
):
    return SQLAlchemyConnectionField(
        python_name=None,
        graphql_name=name,
        type_annotation=None,
        sqlalchemy_name=sqlalchemy_name or source,
        pre_filter=_normalize_where_clause(where),
        pagination=pagination,
        filter=filter,
        order=order,
        default=default,
        **kwargs,
    )


__all__ = ["SQLAlchemyConnectionField", "connection"]
