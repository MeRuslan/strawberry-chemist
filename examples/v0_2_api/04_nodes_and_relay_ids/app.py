from __future__ import annotations

from contextlib import asynccontextmanager

import strawberry
import strawberry_chemist as sc
from sqlalchemy import Integer, String
from sqlalchemy.ext.asyncio import (
    AsyncAttrs,
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(AsyncAttrs, DeclarativeBase):
    pass


class BookModel(Base):
    __tablename__ = "books"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(200))


class ShelfModel(Base):
    __tablename__ = "shelves"

    slug: Mapped[str] = mapped_column(String(80), primary_key=True)
    label: Mapped[str] = mapped_column(String(200))


class MembershipModel(Base):
    __tablename__ = "memberships"

    user_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    organization_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    role: Mapped[str] = mapped_column(String(80))


class LegacyBookmarkModel(Base):
    __tablename__ = "legacy_bookmarks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    label: Mapped[str] = mapped_column(String(200))


class AppContext:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]):
        self._session_factory = session_factory

    @asynccontextmanager
    async def get_session(self):
        async with self._session_factory() as session:
            yield session


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


def create_engine_and_sessionmaker(
    database_url: str = "sqlite+aiosqlite:///:memory:",
) -> tuple[AsyncEngine, async_sessionmaker[AsyncSession]]:
    engine = create_async_engine(database_url, echo=False)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    return engine, session_factory


async def prepare_database(engine: AsyncEngine) -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def seed_data(session_factory: async_sessionmaker[AsyncSession]) -> None:
    async with session_factory() as session:
        session.add_all(
            [
                BookModel(id=1, title="The Hobbit"),
                ShelfModel(slug="favorites", label="Favorites"),
                MembershipModel(user_id=10, organization_id=20, role="owner"),
                LegacyBookmarkModel(id=5, label="Pinned entry"),
            ]
        )
        await session.commit()


def build_schema() -> strawberry.Schema:
    return strawberry.Schema(query=Query, extensions=sc.extensions())
