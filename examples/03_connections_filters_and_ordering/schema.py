from __future__ import annotations

from contextlib import asynccontextmanager

import strawberry
import strawberry_chemist as sc
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from db import BookModel


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


@sc.node(model=BookModel)
class Book:
    title: str
    year: int
    ranking: int | None


@sc.filter(model=BookModel)
class BookFilter(sc.FilterSet):
    title: sc.StringFilter = sc.filter_field()
    year: sc.IntFilter = sc.filter_field()
    author_name: sc.StringFilter = sc.filter_field(path="author.name")
    published_after: int | None = sc.filter_field(
        apply=lambda stmt, value, ctx: stmt.where(BookModel.year >= value)
    )


@sc.order(model=BookModel)
class BookOrder:
    year = sc.order_field()
    title = sc.order_field()
    ranking = sc.order_field()
    author_name = sc.order_field(path="author.name")


@strawberry.type
class Query:
    books: sc.Connection[Book] = sc.connection(
        where=lambda: BookModel.visible.is_(True),
        filter=BookFilter,
        order=BookOrder,
        pagination=sc.CursorPagination(max_limit=20),
    )
    books_page: sc.OffsetConnection[Book] = sc.connection(
        where=lambda: BookModel.visible.is_(True),
        filter=BookFilter,
        order=BookOrder,
        pagination=sc.OffsetPagination(default_limit=2, max_limit=10),
    )


def build_schema() -> strawberry.Schema:
    return strawberry.Schema(query=Query, extensions=sc.extensions())
