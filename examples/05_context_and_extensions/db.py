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
