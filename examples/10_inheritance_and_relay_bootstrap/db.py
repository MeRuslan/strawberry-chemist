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


class BookModel(Base):
    __tablename__ = "books"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(200))
    year: Mapped[int] = mapped_column(Integer)
    isbn: Mapped[str] = mapped_column(String(32))
    translations: Mapped[list["TranslationModel"]] = relationship(
        back_populates="book",
        order_by="TranslationModel.id",
    )


class TranslationModel(Base):
    __tablename__ = "translations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    book_id: Mapped[int] = mapped_column(ForeignKey("books.id"))
    locale: Mapped[str] = mapped_column(String(32))
    title: Mapped[str] = mapped_column(String(200))
    book: Mapped[BookModel] = relationship(back_populates="translations")


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
        hobbit = BookModel(
            title="The Hobbit",
            year=1937,
            isbn="9780261103344",
        )
        earthsea = BookModel(
            title="A Wizard of Earthsea",
            year=1968,
            isbn="9780547773742",
        )
        session.add_all([hobbit, earthsea])
        await session.flush()

        session.add_all(
            [
                TranslationModel(
                    book=hobbit,
                    locale="fr",
                    title="Bilbo le Hobbit",
                ),
                TranslationModel(
                    book=hobbit,
                    locale="es",
                    title="El Hobbit",
                ),
                TranslationModel(
                    book=earthsea,
                    locale="de",
                    title="Ein Magier von Earthsea",
                ),
            ]
        )
        await session.commit()

        return {
            "hobbit": hobbit.id,
            "earthsea": earthsea.id,
        }
