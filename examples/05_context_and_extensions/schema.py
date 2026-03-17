from __future__ import annotations

from contextlib import asynccontextmanager

import strawberry
import strawberry_chemist as sc
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from db import BookModel, PublisherModel


class AppContext:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        request_id: str,
    ):
        self._session_factory = session_factory
        self.request_id = request_id

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
    del current_user_id
    return AppContext(session_factory, request_id=request_id)


@sc.type(model=BookModel)
class Book(sc.Node):
    id = sc.node_id(ids=("slug",))
    title: str

    @sc.field(select=["title"])
    def request_label(
        self,
        title: str,
        info: strawberry.Info[AppContext, None],
    ) -> str:
        return f"{info.context.request_id}:{title}"


@sc.type(model=PublisherModel)
class Publisher:
    name: str
    books: list[Book]


@strawberry.type
class Query:
    @strawberry.field
    async def featured_book(
        self,
        info: strawberry.Info[AppContext, None],
        slug: str,
    ) -> Book | None:
        async with info.context.get_session() as session:
            return await session.scalar(select(BookModel).where(BookModel.slug == slug))

    @strawberry.field
    async def publishers(
        self,
        info: strawberry.Info[AppContext, None],
    ) -> list[Publisher]:
        async with info.context.get_session() as session:
            result = await session.scalars(
                select(PublisherModel).order_by(PublisherModel.name.asc())
            )
            return list(result)


def build_schema() -> strawberry.Schema:
    return strawberry.Schema(query=Query, extensions=sc.extensions())
