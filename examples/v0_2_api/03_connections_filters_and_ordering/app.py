from __future__ import annotations

from contextlib import asynccontextmanager

import strawberry
import strawberry_chemist as sc
from sqlalchemy import Boolean, ForeignKey, Integer, String
from sqlalchemy.ext.asyncio import (
    AsyncAttrs,
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(AsyncAttrs, DeclarativeBase):
    pass


class AuthorModel(Base):
    __tablename__ = "authors"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    books: Mapped[list["BookModel"]] = relationship(back_populates="author")


class BookModel(Base):
    __tablename__ = "books"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    author_id: Mapped[int] = mapped_column(ForeignKey("authors.id"))
    title: Mapped[str] = mapped_column(String(200))
    year: Mapped[int] = mapped_column(Integer)
    ranking: Mapped[int | None] = mapped_column(Integer, nullable=True)
    visible: Mapped[bool] = mapped_column(Boolean, default=True)
    author: Mapped[AuthorModel] = relationship(back_populates="books")


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
        tolkien = AuthorModel(name="J.R.R. Tolkien")
        le_guin = AuthorModel(name="Ursula K. Le Guin")
        calvino = AuthorModel(name="Italo Calvino")
        session.add_all(
            [
                tolkien,
                le_guin,
                calvino,
                BookModel(
                    author=tolkien,
                    title="The Hobbit",
                    year=1937,
                    ranking=8,
                    visible=True,
                ),
                BookModel(
                    author=tolkien,
                    title="The Lord of the Rings",
                    year=1954,
                    ranking=10,
                    visible=True,
                ),
                BookModel(
                    author=le_guin,
                    title="The Left Hand of Darkness",
                    year=1969,
                    ranking=None,
                    visible=True,
                ),
                BookModel(
                    author=calvino,
                    title="Invisible Cities",
                    year=1972,
                    ranking=9,
                    visible=False,
                ),
            ]
        )
        await session.commit()


def build_schema() -> strawberry.Schema:
    return strawberry.Schema(query=Query, extensions=sc.extensions())
