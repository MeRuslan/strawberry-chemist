from __future__ import annotations

from contextlib import asynccontextmanager

import strawberry
import strawberry_chemist as sc
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from db import AuthorModel, BookModel


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

    @sc.relationship("books", select=["title"], parent_select=["name"])
    def labeled_books(self, books: list[BookModel]) -> list[str]:
        return [f"{self.name}: {book.title}" for book in books]

    @sc.relationship("books", load="full")
    def publication_labels(
        self,
        books: list[BookModel],
    ) -> list[str]:
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


def build_schema() -> strawberry.Schema:
    return strawberry.Schema(query=Query, extensions=sc.extensions())
