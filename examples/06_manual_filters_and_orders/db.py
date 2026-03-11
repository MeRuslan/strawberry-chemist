from __future__ import annotations

import datetime as dt

from sqlalchemy import DateTime, ForeignKey, Integer, String
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


class UserModel(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(100))
    reviews: Mapped[list["ReviewModel"]] = relationship(back_populates="author")


class ReviewModel(Base):
    __tablename__ = "reviews"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    author_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    title: Mapped[str] = mapped_column(String(200))
    created_at: Mapped[dt.datetime] = mapped_column(DateTime)
    author: Mapped[UserModel] = relationship(back_populates="reviews")
    votes: Mapped[list["VoteModel"]] = relationship(back_populates="review")


class VoteModel(Base):
    __tablename__ = "votes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    review_id: Mapped[int] = mapped_column(ForeignKey("reviews.id"))
    value: Mapped[int] = mapped_column(Integer)
    review: Mapped[ReviewModel] = relationship(back_populates="votes")


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
        alice = UserModel(username="alice")
        bob = UserModel(username="bob")
        review_hobbit = ReviewModel(
            author=alice,
            title="The Hobbit review",
            created_at=dt.datetime(2024, 1, 1, 12, 0, 0),
        )
        review_silmarillion = ReviewModel(
            author=alice,
            title="The Silmarillion review",
            created_at=dt.datetime(2024, 1, 2, 12, 0, 0),
        )
        review_earthsea = ReviewModel(
            author=alice,
            title="A Wizard of Earthsea review",
            created_at=dt.datetime(2024, 1, 3, 12, 0, 0),
        )
        review_atuan = ReviewModel(
            author=bob,
            title="The Tombs of Atuan review",
            created_at=dt.datetime(2024, 1, 4, 12, 0, 0),
        )
        session.add_all(
            [
                alice,
                bob,
                review_hobbit,
                review_silmarillion,
                review_earthsea,
                review_atuan,
                VoteModel(review=review_hobbit, value=1),
                VoteModel(review=review_hobbit, value=1),
                VoteModel(review=review_hobbit, value=1),
                VoteModel(review=review_silmarillion, value=1),
                VoteModel(review=review_earthsea, value=1),
                VoteModel(review=review_earthsea, value=1),
                VoteModel(review=review_atuan, value=1),
                VoteModel(review=review_atuan, value=1),
                VoteModel(review=review_atuan, value=1),
                VoteModel(review=review_atuan, value=1),
            ]
        )
        await session.commit()
        return {"alice": alice.id, "bob": bob.id}
