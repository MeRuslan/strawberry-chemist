from __future__ import annotations

from contextlib import asynccontextmanager

import strawberry
import strawberry_chemist as sc
from sqlalchemy import ForeignKey, Integer, String, select
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


class PublisherModel(Base):
    __tablename__ = "publishers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    books: Mapped[list["BookModel"]] = relationship(back_populates="publisher")


class BookModel(Base):
    __tablename__ = "books"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    publisher_id: Mapped[int] = mapped_column(ForeignKey("publishers.id"))
    slug: Mapped[str] = mapped_column(String(80), unique=True)
    title: Mapped[str] = mapped_column(String(200))
    publisher: Mapped[PublisherModel] = relationship(back_populates="books")


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


@sc.node(model=BookModel, ids=("slug",))
class Book:
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
        orbit = PublisherModel(name="Orbit")
        ace = PublisherModel(name="Ace")
        session.add_all(
            [
                orbit,
                ace,
                BookModel(publisher=orbit, slug="hobbit", title="The Hobbit"),
                BookModel(
                    publisher=ace,
                    slug="left-hand-of-darkness",
                    title="The Left Hand of Darkness",
                ),
            ]
        )
        await session.commit()


def build_schema() -> strawberry.Schema:
    return strawberry.Schema(query=Query, extensions=sc.extensions())
