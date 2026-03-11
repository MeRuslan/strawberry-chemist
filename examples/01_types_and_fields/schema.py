from __future__ import annotations

from contextlib import asynccontextmanager

import strawberry
import strawberry_chemist as sc
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from db import BookModel

REFERENCE_YEAR = 2026


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


@sc.type(model=BookModel)
class Book:
    title: str
    published_year: int = sc.attr("year")
    marketing_line: str = sc.attr("tagline")

    @sc.field(select=["title", "isbn"])
    def title_with_isbn(self, title: str, isbn: str) -> str:
        return f"{title} ({isbn})"

    @sc.field(select=["year"])
    def years_since_published(self, year: int) -> int:
        return REFERENCE_YEAR - year


@strawberry.type
class Query:
    @strawberry.field
    async def books(
        self,
        info: strawberry.Info[AppContext, None],
    ) -> list[Book]:
        async with info.context.get_session() as session:
            result = await session.scalars(
                select(BookModel).order_by(BookModel.year.asc(), BookModel.title.asc())
            )
            return list(result)


def build_schema() -> strawberry.Schema:
    return strawberry.Schema(query=Query, extensions=sc.extensions())
