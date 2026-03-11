from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Any, Optional

import strawberry
import strawberry_chemist as sc
from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.ext.asyncio import (
    AsyncAttrs,
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from strawberry import BasePermission
from strawberry.types import Info


class Base(AsyncAttrs, DeclarativeBase):
    pass


class UserModel(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(120), unique=True)
    posts: Mapped[list["PostModel"]] = relationship(back_populates="author")


class PostModel(Base):
    __tablename__ = "posts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    author_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    title: Mapped[str] = mapped_column(String(200))
    author: Mapped[UserModel] = relationship(back_populates="posts")


class AppContext:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        *,
        current_user_id: int | None,
    ):
        self._session_factory = session_factory
        self.current_user_id = current_user_id

    @asynccontextmanager
    async def get_session(self):
        async with self._session_factory() as session:
            yield session


class IsAuthenticated(BasePermission):
    message = "Authentication required"

    async def has_permission(
        self, source: Any, info: Info[AppContext, None], **kwargs
    ) -> bool:
        return info.context.current_user_id is not None


class IsPostAuthor(BasePermission):
    message = "Actor cannot modify this post"

    async def has_permission(
        self,
        source: PostModel | None,
        info: Info[AppContext, None],
        **kwargs,
    ) -> bool:
        return source is not None and source.author_id == info.context.current_user_id


@sc.node(model=UserModel)
class User:
    username: str


@sc.node(model=PostModel)
class Post:
    title: str


@strawberry.type
class Query:
    node = sc.node_field()

    @sc.node_lookup(model=PostModel, id_name="post_id", node_param_name="post")
    async def post_by_id(
        self,
        info: Info[AppContext, None],
        post: PostModel | None,
    ) -> Optional[Post]:
        return post


@strawberry.type
class Mutation:
    @sc.node_lookup(
        model=PostModel,
        id_name="post_id",
        node_param_name="post",
        permission_classes=[IsAuthenticated],
        node_permission_classes=[IsPostAuthor],
    )
    async def rename_post(
        self,
        info: Info[AppContext, None],
        post: PostModel | None,
        title: str,
    ) -> Optional[Post]:
        if post is None:
            return None
        async with info.context.get_session() as session:
            post.title = title
            session.add(post)
            await session.commit()
            await session.refresh(post)
        return post


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
        first = PostModel(author=alice, title="Draft one")
        second = PostModel(author=bob, title="Draft two")
        session.add_all([alice, bob, first, second])
        await session.commit()
        return {
            "alice": alice.id,
            "bob": bob.id,
            "first_post": first.id,
            "second_post": second.id,
        }


def build_schema() -> strawberry.Schema:
    return strawberry.Schema(query=Query, mutation=Mutation, extensions=sc.extensions())
