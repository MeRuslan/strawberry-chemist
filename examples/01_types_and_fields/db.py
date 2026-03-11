from __future__ import annotations

from sqlalchemy import Integer, String
from sqlalchemy.ext.asyncio import (
    AsyncAttrs,
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(AsyncAttrs, DeclarativeBase):
    pass


class BookModel(Base):
    __tablename__ = "books"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(200))
    isbn: Mapped[str] = mapped_column(String(32), unique=True)
    year: Mapped[int] = mapped_column(Integer)
    tagline: Mapped[str] = mapped_column(String(200))


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
