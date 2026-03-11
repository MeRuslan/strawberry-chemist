from __future__ import annotations

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
