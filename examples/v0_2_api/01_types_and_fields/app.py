from __future__ import annotations

from contextlib import asynccontextmanager

import strawberry
import strawberry_chemist as sc
from sqlalchemy import Integer, String, select
from sqlalchemy.ext.asyncio import (
    AsyncAttrs,
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

REFERENCE_YEAR = 2026


class Base(AsyncAttrs, DeclarativeBase):
    pass


class BookModel(Base):
    __tablename__ = "books"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(200))
    isbn: Mapped[str] = mapped_column(String(32), unique=True)
    year: Mapped[int] = mapped_column(Integer)
    tagline: Mapped[str] = mapped_column(String(200))


class AppContext:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]):
        self._session_factory = session_factory

    @asynccontextmanager
    async def get_session(self):
        async with self._session_factory() as session:
            yield session


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
                BookModel(
                    title="The Hobbit",
                    isbn="9780261103344",
                    year=1937,
                    tagline="There and back again.",
                ),
                BookModel(
                    title="The Left Hand of Darkness",
                    isbn="9780441478125",
                    year=1969,
                    tagline="Winter, politics, and estrangement.",
                ),
            ]
        )
        await session.commit()


def build_schema() -> strawberry.Schema:
    return strawberry.Schema(query=Query, extensions=sc.extensions())
