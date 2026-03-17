from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Any, Optional

import strawberry
import strawberry_chemist as sc
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from strawberry import BasePermission
from strawberry.types import Info

from db import PostModel, UserModel


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


def build_context(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    request_id: str = "dev-request",
    current_user_id: int | None = None,
) -> AppContext:
    del request_id
    return AppContext(session_factory, current_user_id=current_user_id)


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


@sc.type(model=UserModel)
class User(sc.Node):
    username: str


@sc.type(model=PostModel)
class Post(sc.Node):
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


def build_schema() -> strawberry.Schema:
    return strawberry.Schema(
        query=Query,
        mutation=Mutation,
        types=(User, Post),
        extensions=sc.extensions(),
    )
