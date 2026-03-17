from __future__ import annotations

from contextlib import asynccontextmanager

import strawberry
import strawberry_chemist as sc
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from strawberry.types import Info

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
class Book(sc.Node):
    title: str
    year: int

    @sc.field
    def titled_with(self, prefix: str) -> str:
        return f"{prefix}{self.title}"

    @sc.field(select={"title": "book_title", "year": "published_year"})
    def catalog_label(
        self,
        book_title: str,
        published_year: int,
        suffix: str,
    ) -> str:
        return f"{book_title} ({published_year}){suffix}"

    @strawberry.field
    def plain_summary(self) -> str:
        return f"{self.title} [{self.year}]"


@strawberry.type
class BookExtended(Book):
    title_matches_prefix: bool


@sc.type(model=AuthorModel)
class Author:
    name: str
    country: str

    @sc.relationship("books", select=["title"])
    def joined_titles(
        self,
        books: list[BookModel],
        separator: str,
    ) -> str:
        return separator.join(book.title for book in books)

    @sc.connection(
        source="books",
        select=["title"],
        source_param_name="loaded_connection",
        default_order_by=(BookModel.year.asc(),),
        pagination=sc.CursorPagination(default_limit=10, max_limit=10),
    )
    def books_matching(
        self,
        loaded_connection: sc.Connection[BookModel],
        title_prefix: str,
    ) -> sc.Connection[BookExtended]:
        for edge in loaded_connection.edges:
            edge.node.title_matches_prefix = edge.node.title.startswith(title_prefix)
        return loaded_connection

    @strawberry.field
    def manual_badge(self) -> str:
        return f"manual:{self.country}"


@strawberry.type
class Query:
    node = sc.node_field()

    @strawberry.field
    async def books(
        self,
        info: Info[AppContext, None],
    ) -> list[Book]:
        async with info.context.get_session() as session:
            result = await session.scalars(
                select(BookModel).order_by(BookModel.year.asc(), BookModel.title.asc())
            )
            return list(result)

    @strawberry.field
    async def authors(
        self,
        info: Info[AppContext, None],
    ) -> list[Author]:
        async with info.context.get_session() as session:
            result = await session.scalars(
                select(AuthorModel).order_by(AuthorModel.name.asc())
            )
            return list(result)

    @sc.node_lookup(model=BookModel, id_name="book_id", node_param_name="book")
    async def book_label(
        self,
        info: Info[AppContext, None],
        book: BookModel | None,
        prefix: str,
    ) -> str | None:
        del info
        if book is None:
            return None
        return f"{prefix}{book.title}"

    @strawberry.field
    def contract_version(self) -> str:
        return "resolver-args-v1"


def build_schema() -> strawberry.Schema:
    return strawberry.Schema(query=Query, extensions=sc.extensions())
