from __future__ import annotations

import datetime as dt
import enum
from contextlib import asynccontextmanager

import strawberry
import strawberry_chemist as sc
from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from db import ReviewModel, VoteModel


class AppContext:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]):
        self._session_factory = session_factory

    @asynccontextmanager
    async def get_session(self):
        async with self._session_factory() as session:
            yield session


def build_context(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    request_id: str = "dev-request",
    current_user_id: int | None = None,
) -> AppContext:
    del request_id, current_user_id
    return AppContext(session_factory)


@sc.type(model=ReviewModel)
class Review:
    title: str
    created_at: dt.datetime


@strawberry.input
class LegacyReviewFilter:
    author_id: strawberry.ID
    query: str | None = None


@strawberry.enum
class LegacyReviewOrderField(enum.Enum):
    CREATED_AT = "created_at"
    VOTES = "votes"


@strawberry.enum
class LegacyOrderDirection(enum.Enum):
    ASC = "asc"
    DESC = "desc"


@strawberry.input
class LegacyReviewOrder:
    field: LegacyReviewOrderField
    order: LegacyOrderDirection


def apply_legacy_review_filter(stmt, value: LegacyReviewFilter, ctx):
    stmt = stmt.where(ReviewModel.author_id == int(value.author_id))
    if value.query:
        stmt = stmt.where(ReviewModel.title.ilike(f"%{value.query}%"))
    return stmt


def apply_legacy_review_order(stmt, value: LegacyReviewOrder, ctx):
    if value.field == LegacyReviewOrderField.CREATED_AT:
        order_column = ReviewModel.created_at
    elif value.field == LegacyReviewOrderField.VOTES:
        stmt = stmt.outerjoin(
            VoteModel, VoteModel.review_id == ReviewModel.id
        ).group_by(ReviewModel.id)
        order_column = func.coalesce(func.sum(VoteModel.value), 0)
    else:
        raise AssertionError("Unhandled review order field")

    if value.order == LegacyOrderDirection.DESC:
        return stmt.order_by(order_column.desc())
    return stmt.order_by(order_column.asc())


legacy_review_filter = sc.manual_filter(
    input=LegacyReviewFilter,
    required=True,
    apply=apply_legacy_review_filter,
)

legacy_review_order = sc.manual_order(
    input=LegacyReviewOrder,
    name="order",
    python_name="order",
    apply=apply_legacy_review_order,
)


@strawberry.type
class Query:
    reviews: sc.Connection[Review] = sc.connection(
        filter=legacy_review_filter,
        order=legacy_review_order,
        pagination=sc.CursorPagination(max_limit=20),
    )


def build_schema() -> strawberry.Schema:
    return strawberry.Schema(query=Query, extensions=sc.extensions())
