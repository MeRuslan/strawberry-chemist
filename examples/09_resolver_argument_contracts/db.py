from __future__ import annotations

from sqlalchemy import ForeignKey, Integer, String
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
    country: Mapped[str] = mapped_column(String(120))
    books: Mapped[list["BookModel"]] = relationship(back_populates="author")


class BookModel(Base):
    __tablename__ = "books"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    author_id: Mapped[int] = mapped_column(ForeignKey("authors.id"))
    title: Mapped[str] = mapped_column(String(200))
    year: Mapped[int] = mapped_column(Integer)
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


async def seed_data(
    session_factory: async_sessionmaker[AsyncSession],
) -> dict[str, int]:
    async with session_factory() as session:
        tolkien = AuthorModel(name="J.R.R. Tolkien", country="United Kingdom")
        le_guin = AuthorModel(name="Ursula K. Le Guin", country="United States")
        session.add_all([tolkien, le_guin])
        await session.flush()

        hobbit = BookModel(author=tolkien, title="The Hobbit", year=1937)
        lord = BookModel(author=tolkien, title="The Lord of the Rings", year=1954)
        earthsea = BookModel(author=le_guin, title="A Wizard of Earthsea", year=1968)
        session.add_all([hobbit, lord, earthsea])
        await session.commit()

        return {
            "tolkien": tolkien.id,
            "le_guin": le_guin.id,
            "hobbit": hobbit.id,
            "lord": lord.id,
            "earthsea": earthsea.id,
        }
