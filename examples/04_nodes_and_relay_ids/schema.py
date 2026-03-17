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
DEFAULT_CODEC = sc.relay.IntRegistryCodec(
    registry={
        BookModel: 1,
        ShelfModel: 2,
        MembershipModel: 3,
    }
)


@sc.type(model=BookModel)
class Book(sc.Node):
    title: str


@sc.type(model=ShelfModel)
class Shelf(sc.Node):
    id = sc.node_id(ids=("slug",))
    label: str


@sc.type(model=MembershipModel)
class Membership(sc.Node):
    role: str


@sc.type(model=LegacyBookmarkModel)
class LegacyBookmark(sc.Node):
    id = sc.node_id(codec=LEGACY_CODEC)
    label: str


@strawberry.type
class Query:
    node = sc.node_field()
    book = sc.node_field(allowed_types=(Book,))
    books: sc.Connection[Book] = sc.connection()


def build_schema() -> strawberry.Schema:
    sc.configure(
        default_pagination=sc.CursorPagination(default_limit=10, max_limit=20),
        default_relay_id_codec=DEFAULT_CODEC,
    )
    return strawberry.Schema(
        query=Query,
        types=(Book, Shelf, Membership, LegacyBookmark),
        extensions=sc.extensions(),
    )
