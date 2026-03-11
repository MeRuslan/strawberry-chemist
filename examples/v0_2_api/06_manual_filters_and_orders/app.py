from __future__ import annotations

import datetime as dt
import enum
from contextlib import asynccontextmanager

import strawberry
import strawberry_chemist as sc
from sqlalchemy import DateTime, ForeignKey, Integer, String, func
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


class AppContext:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]):
        self._session_factory = session_factory

    @asynccontextmanager
    async def get_session(self):
        async with self._session_factory() as session:
            yield session


@sc.type(model=ReviewModel)
class Review:
    title: str
    created_at: dt.datetime


@strawberry.input
class LegacyReviewFilter:
    author_id: strawberry.ID
    query: str | None = None


@strawberry.enum
class LegacyReviewOrderField(enum.Enum):
    CREATED_AT = "created_at"
    VOTES = "votes"


@strawberry.enum
class LegacyOrderDirection(enum.Enum):
    ASC = "asc"
    DESC = "desc"


@strawberry.input
class LegacyReviewOrder:
    field: LegacyReviewOrderField
    order: LegacyOrderDirection


def apply_legacy_review_filter(stmt, value: LegacyReviewFilter, ctx):
    stmt = stmt.where(ReviewModel.author_id == int(value.author_id))
    if value.query:
        stmt = stmt.where(ReviewModel.title.ilike(f"%{value.query}%"))
    return stmt


def apply_legacy_review_order(stmt, value: LegacyReviewOrder, ctx):
    if value.field == LegacyReviewOrderField.CREATED_AT:
        order_column = ReviewModel.created_at
    elif value.field == LegacyReviewOrderField.VOTES:
        stmt = stmt.outerjoin(
            VoteModel, VoteModel.review_id == ReviewModel.id
        ).group_by(ReviewModel.id)
        order_column = func.coalesce(func.sum(VoteModel.value), 0)
    else:
        raise AssertionError("Unhandled review order field")

    if value.order == LegacyOrderDirection.DESC:
        return stmt.order_by(order_column.desc())
    return stmt.order_by(order_column.asc())


legacy_review_filter = sc.manual_filter(
    input=LegacyReviewFilter,
    required=True,
    apply=apply_legacy_review_filter,
)

legacy_review_order = sc.manual_order(
    input=LegacyReviewOrder,
    name="order",
    python_name="order",
    apply=apply_legacy_review_order,
)


@strawberry.type
class Query:
    reviews: sc.Connection[Review] = sc.connection(
        filter=legacy_review_filter,
        order=legacy_review_order,
        pagination=sc.CursorPagination(max_limit=20),
    )


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


def build_schema() -> strawberry.Schema:
    return strawberry.Schema(query=Query, extensions=sc.extensions())
