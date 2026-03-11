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
    author: Mapped[AuthorModel] = relationship(back_populates="books")


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
    year: int


@sc.type(model=AuthorModel)
class Author:
    name: str
    published_books: list[Book] = sc.relationship("books")
    classic_books: list[Book] = sc.relationship(
        "books",
        where=lambda: BookModel.year < 1955,
    )

    @sc.relationship("books", select=["title"])
    def book_titles(self, books: list[BookModel]) -> list[str]:
        return [book.title for book in books]

    @sc.relationship("books", load="full")
    def publication_labels(self, books: list[BookModel]) -> list[str]:
        return [f"{book.title} ({book.year})" for book in books]


@strawberry.type
class Query:
    @strawberry.field
    async def authors(
        self,
        info: strawberry.Info[AppContext, None],
    ) -> list[Author]:
        async with info.context.get_session() as session:
            result = await session.scalars(
                select(AuthorModel).order_by(AuthorModel.name.asc())
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
        tolkien = AuthorModel(name="J.R.R. Tolkien")
        le_guin = AuthorModel(name="Ursula K. Le Guin")
        session.add_all(
            [
                tolkien,
                le_guin,
                BookModel(author=tolkien, title="The Hobbit", year=1937),
                BookModel(author=tolkien, title="The Lord of the Rings", year=1954),
                BookModel(author=tolkien, title="The Silmarillion", year=1977),
                BookModel(author=le_guin, title="A Wizard of Earthsea", year=1968),
            ]
        )
        await session.commit()


def build_schema() -> strawberry.Schema:
    return strawberry.Schema(query=Query, extensions=sc.extensions())
