from __future__ import annotations

from typing import Iterable, Optional

from strawberry import UNSET

from strawberry_chemist.connection.base import SQLAlchemyBaseConnectionField
from strawberry_chemist.fields.field import _reject_legacy_kwargs
from strawberry_chemist.pagination import CursorPagination


def _normalize_where_clause(where):
    if where is None:
        return ()
    filters = where if isinstance(where, list) else [where]
    return tuple(filters)


def _resolve_filter(filter_definition):
    if filter_definition is None:
        return None
    return getattr(filter_definition, "__sc_filter_definition__", filter_definition)


def _resolve_order(order_definition):
    if order_definition is None:
        return None
    return getattr(order_definition, "__sc_order_definition__", order_definition)


class SQLAlchemyConnectionField(SQLAlchemyBaseConnectionField):
    def __init__(
        self,
        *,
        pagination=None,
        filter=None,
        order=None,
        default_order_by=None,
        **kwargs,
    ):
        self.pagination = pagination or CursorPagination()
        super().__init__(
            order=_resolve_order(order),
            filter=_resolve_filter(filter),
            default_order_by=default_order_by,
            **kwargs,
        )


def connection(
    *,
    source: Optional[str] = None,
    where=None,
    filter=None,
    order=None,
    default_order_by=None,
    parent_select: Optional[Iterable[str]] = None,
    pagination=None,
    name=None,
    default=UNSET,
    **kwargs,
):
    _reject_legacy_kwargs(
        "connection",
        kwargs,
        unsupported=(
            "sqlalchemy_name",
            "pre_filter",
            "needs_fields",
            "ignore_field_selections",
            "post_processor",
            "additional_parent_fields",
            "load",
        ),
    )
    return SQLAlchemyConnectionField(
        python_name=None,
        graphql_name=name,
        type_annotation=None,
        sqlalchemy_name=source,
        where=_normalize_where_clause(where),
        default_order_by=default_order_by,
        parent_select=parent_select,
        pagination=pagination,
        filter=filter,
        order=order,
        default=default,
        **kwargs,
    )


__all__ = ["SQLAlchemyConnectionField", "connection"]
