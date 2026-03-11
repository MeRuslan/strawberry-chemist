from __future__ import annotations

from contextlib import asynccontextmanager

import strawberry
import strawberry_chemist as sc
from sqlalchemy import Boolean, Integer, String
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
    year: Mapped[int] = mapped_column(Integer)
    visible: Mapped[bool] = mapped_column(Boolean, default=True)


class AppContext:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]):
        self._session_factory = session_factory

    @asynccontextmanager
    async def get_session(self):
        async with self._session_factory() as session:
            yield session


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
                BookModel(title="The Hobbit", year=1937, visible=True),
                BookModel(title="The Lord of the Rings", year=1954, visible=True),
                BookModel(
                    title="The Left Hand of Darkness",
                    year=1969,
                    visible=True,
                ),
                BookModel(title="Invisible Cities", year=1972, visible=False),
            ]
        )
        await session.commit()


def build_schema() -> strawberry.Schema:
    return strawberry.Schema(query=Query, extensions=sc.extensions())
