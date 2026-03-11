from __future__ import annotations

import pytest

from app import (
    AppContext,
    build_schema,
    create_engine_and_sessionmaker,
    prepare_database,
    seed_data,
)


@pytest.mark.asyncio
async def test_node_lookup_decorator_contract() -> None:
    engine, session_factory = create_engine_and_sessionmaker()
    await prepare_database(engine)
    ids = await seed_data(session_factory)
    schema = build_schema()
    sdl = schema.as_str()

    assert "postById(postId: ID!): Post" in sdl
    assert "renamePost(postId: ID!, title: String!): Post" in sdl
    assert " post:" not in sdl

    post_result = await schema.execute(
        """
        query($postId: ID!, $userId: ID!) {
          postById(postId: $postId) {
            title
          }
          mismatch: postById(postId: $userId) {
            title
          }
        }
        """,
        variable_values={
            "postId": f"Post_{ids['first_post']}",
            "userId": f"User_{ids['alice']}",
        },
        context_value=AppContext(session_factory, current_user_id=None),
    )

    assert post_result.errors is None
    assert post_result.data == {
        "postById": {"title": "Draft one"},
        "mismatch": None,
    }

    rename_result = await schema.execute(
        """
        mutation($postId: ID!) {
          renamePost(postId: $postId, title: "Renamed draft") {
            title
          }
        }
        """,
        variable_values={"postId": f"Post_{ids['first_post']}"},
        context_value=AppContext(session_factory, current_user_id=ids["alice"]),
    )

    assert rename_result.errors is None
    assert rename_result.data == {
        "renamePost": {"title": "Renamed draft"},
    }

    denied_result = await schema.execute(
        """
        mutation($postId: ID!) {
          renamePost(postId: $postId, title: "Nope") {
            title
          }
        }
        """,
        variable_values={"postId": f"Post_{ids['first_post']}"},
        context_value=AppContext(session_factory, current_user_id=ids["bob"]),
    )

    assert denied_result.data is None or denied_result.data["renamePost"] is None
    assert denied_result.errors is not None

    unauthenticated_result = await schema.execute(
        """
        mutation($postId: ID!) {
          renamePost(postId: $postId, title: "Nope") {
            title
          }
        }
        """,
        variable_values={"postId": f"Post_{ids['first_post']}"},
        context_value=AppContext(session_factory, current_user_id=None),
    )

    assert (
        unauthenticated_result.data is None
        or unauthenticated_result.data["renamePost"] is None
    )
    assert unauthenticated_result.errors is not None

    await engine.dispose()
