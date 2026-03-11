from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass

import pytest_asyncio
import strawberry
from app import (
    AppContext,
    build_schema,
    create_engine_and_sessionmaker,
    prepare_database,
    seed_data,
)


@dataclass
class ExampleEnv:
    schema: strawberry.Schema
    session_factory: object
    ids: dict[str, int]


@pytest_asyncio.fixture
async def env() -> AsyncIterator[ExampleEnv]:
    engine, session_factory = create_engine_and_sessionmaker()
    await prepare_database(engine)
    ids = await seed_data(session_factory)
    try:
        yield ExampleEnv(
            schema=build_schema(),
            session_factory=session_factory,
            ids=ids,
        )
    finally:
        await engine.dispose()


def build_context(env: ExampleEnv, *, current_user_id: int | None) -> AppContext:
    return AppContext(env.session_factory, current_user_id=current_user_id)


async def execute(
    env: ExampleEnv,
    query: str,
    *,
    variable_values: dict[str, str] | None = None,
    current_user_id: int | None,
):
    return await env.schema.execute(
        query,
        variable_values=variable_values,
        context_value=build_context(env, current_user_id=current_user_id),
    )


def test_schema_uses_custom_id_argument_names() -> None:
    sdl = build_schema().as_str()

    assert "postById(postId: ID!): Post" in sdl
    assert "renamePost(postId: ID!, title: String!): Post" in sdl
    assert " post:" not in sdl


async def test_node_lookup_resolves_matching_node_ids(env: ExampleEnv) -> None:
    result = await execute(
        env,
        """
        query($postId: ID!) {
          postById(postId: $postId) {
            title
          }
        }
        """,
        variable_values={"postId": f"Post_{env.ids['first_post']}"},
        current_user_id=None,
    )

    assert result.errors is None
    assert result.data == {
        "postById": {"title": "Draft one"},
    }


async def test_node_lookup_rejects_mismatched_node_ids(env: ExampleEnv) -> None:
    result = await execute(
        env,
        """
        query($userId: ID!) {
          postById(postId: $userId) {
            title
          }
        }
        """,
        variable_values={"userId": f"User_{env.ids['alice']}"},
        current_user_id=None,
    )

    assert result.errors is None
    assert result.data == {"postById": None}


async def test_post_author_can_rename_a_loaded_node(env: ExampleEnv) -> None:
    result = await execute(
        env,
        """
        mutation($postId: ID!) {
          renamePost(postId: $postId, title: "Renamed draft") {
            title
          }
        }
        """,
        variable_values={"postId": f"Post_{env.ids['first_post']}"},
        current_user_id=env.ids["alice"],
    )

    assert result.errors is None
    assert result.data == {
        "renamePost": {"title": "Renamed draft"},
    }


async def test_non_author_cannot_rename_post(env: ExampleEnv) -> None:
    result = await execute(
        env,
        """
        mutation($postId: ID!) {
          renamePost(postId: $postId, title: "Nope") {
            title
          }
        }
        """,
        variable_values={"postId": f"Post_{env.ids['first_post']}"},
        current_user_id=env.ids["bob"],
    )

    assert result.data is None or result.data["renamePost"] is None
    assert result.errors is not None
    assert result.errors[0].message == "Actor cannot modify this post"


async def test_unauthenticated_actor_cannot_rename_post(env: ExampleEnv) -> None:
    result = await execute(
        env,
        """
        mutation($postId: ID!) {
          renamePost(postId: $postId, title: "Nope") {
            title
          }
        }
        """,
        variable_values={"postId": f"Post_{env.ids['first_post']}"},
        current_user_id=None,
    )

    assert result.data is None or result.data["renamePost"] is None
    assert result.errors is not None
    assert result.errors[0].message == "Authentication required"
