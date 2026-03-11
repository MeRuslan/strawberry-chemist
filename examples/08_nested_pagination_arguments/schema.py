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


@strawberry.type
class Query:
    books: sc.Connection[Book] = sc.connection(
        where=lambda: BookModel.visible.is_(True),
        pagination=sc.CursorPagination(max_limit=20, nested=True),
    )
    books_page: sc.OffsetConnection[Book] = sc.connection(
        where=lambda: BookModel.visible.is_(True),
        pagination=sc.OffsetPagination(default_limit=2, max_limit=10, nested=True),
    )


def build_schema() -> strawberry.Schema:
    return strawberry.Schema(query=Query, extensions=sc.extensions())
