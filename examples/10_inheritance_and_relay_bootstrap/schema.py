from __future__ import annotations

from contextlib import asynccontextmanager

import strawberry
import strawberry_chemist as sc
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from db import BookModel, TranslationModel


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


@sc.type(model=TranslationModel)
class Translation:
    locale: str
    title: str


@strawberry.interface
class TranslationPreview:
    locale: str


@sc.type(model=TranslationModel)
class DetachedTranslationPreview(TranslationPreview):
    locale: str
    title: str


@sc.type(model=BookModel)
class BookBase:
    title: str
    isbn_value: str = sc.attr("isbn")

    @sc.field(select=["title", "isbn"])
    def label(self, title: str, isbn: str) -> str:
        return f"{title} ({isbn})"


@sc.type(model=BookModel)
class Book(BookBase):
    year: int


class PlainBookMixin:
    @sc.field(select=["title"])
    def mixin_label(self, title: str) -> str:
        return title.upper()

    @sc.relationship("translations", select=["locale"])
    def mixin_translation_locales(
        self,
        translations: list[TranslationModel],
    ) -> list[str]:
        return [translation.locale for translation in translations]


@sc.type(model=BookModel)
class MixedInBook(PlainBookMixin):
    title: str
    year: int
    direct_isbn: str = sc.attr("isbn")


@sc.node(model=BookModel)
class CatalogNode:
    title: str
    isbn_value: str = sc.attr("isbn")
    translations: list[Translation] = sc.relationship("translations")

    @sc.field(select=["title", "isbn"])
    def label(self, title: str, isbn: str) -> str:
        return f"{title} ({isbn})"


@sc.node(model=BookModel)
class BookNode(CatalogNode):
    year: int


async def _load_books(info: strawberry.Info[AppContext, None]) -> list[BookModel]:
    async with info.context.get_session() as session:
        result = await session.scalars(select(BookModel).order_by(BookModel.id.asc()))
        return list(result)


@strawberry.type
class Query:
    node = sc.node_field(allowed_types=(BookNode,))
    book = sc.node_field(allowed_types=(BookNode,), name="book")

    @strawberry.field
    def preview(self) -> TranslationPreview:
        return DetachedTranslationPreview(
            locale="fr",
            title="Bilbo le Hobbit",
        )

    @strawberry.field
    async def books(
        self,
        info: strawberry.Info[AppContext, None],
    ) -> list[Book]:
        return await _load_books(info)

    @strawberry.field
    async def mixed_in_books(
        self,
        info: strawberry.Info[AppContext, None],
    ) -> list[MixedInBook]:
        return await _load_books(info)

    @strawberry.field
    async def book_nodes(
        self,
        info: strawberry.Info[AppContext, None],
    ) -> list[BookNode]:
        return await _load_books(info)


def build_unconfigured_schema() -> strawberry.Schema:
    return strawberry.Schema(
        query=Query,
        types=(DetachedTranslationPreview,),
        extensions=sc.extensions(),
    )


def build_schema() -> strawberry.Schema:
    schema = build_unconfigured_schema()
    return sc.relay.configure(schema, node_types=(BookNode,))
