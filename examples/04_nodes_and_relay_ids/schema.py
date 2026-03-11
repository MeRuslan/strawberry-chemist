from __future__ import annotations

from contextlib import asynccontextmanager

import strawberry
import strawberry_chemist as sc
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from db import BookModel, LegacyBookmarkModel, MembershipModel, ShelfModel


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


LEGACY_CODEC = sc.relay.IntRegistryCodec(registry={LegacyBookmarkModel: 7})


@sc.node(model=BookModel)
class Book:
    title: str


@sc.node(model=ShelfModel, ids=("slug",))
class Shelf:
    label: str


@sc.node(model=MembershipModel)
class Membership:
    role: str


@sc.node(model=LegacyBookmarkModel, codec=LEGACY_CODEC)
class LegacyBookmark:
    label: str


@strawberry.type
class Query:
    node = sc.node_field()
    book = sc.node_field(allowed_types=(Book,))
    books: sc.Connection[Book] = sc.connection()


def build_schema() -> strawberry.Schema:
    return strawberry.Schema(query=Query, extensions=sc.extensions())
