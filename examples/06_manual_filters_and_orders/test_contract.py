from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass

import pytest_asyncio
import strawberry
from app import (
    AppContext,
    build_schema,
    build_context,
    create_engine_and_sessionmaker,
    prepare_database,
    seed_data,
)


@dataclass
class ExampleEnv:
    schema: strawberry.Schema
    context: AppContext
    ids: dict[str, int]


@pytest_asyncio.fixture
async def env() -> AsyncIterator[ExampleEnv]:
    engine, session_factory = create_engine_and_sessionmaker()
    await prepare_database(engine)
    ids = await seed_data(session_factory)
    try:
        yield ExampleEnv(
            schema=build_schema(),
            context=build_context(session_factory),
            ids=ids,
        )
    finally:
        await engine.dispose()


async def execute_ok(
    env: ExampleEnv,
    query: str,
    *,
    variable_values: dict[str, str] | None = None,
) -> dict[str, object]:
    result = await env.schema.execute(
        query,
        variable_values=variable_values,
        context_value=env.context,
    )
    assert result.errors is None
    assert result.data is not None
    return result.data


def test_manual_filter_and_order_preserve_legacy_schema_shape() -> None:
    schema = build_schema()
    sdl = schema.as_str()

    assert "input LegacyReviewFilter" in sdl
    assert "authorId: ID!" in sdl
    assert "input LegacyReviewOrder" in sdl
    assert "order: LegacyOrderDirection!" in sdl
    assert "filter: LegacyReviewFilter!" in sdl
    assert "order: LegacyReviewOrder" in sdl
    assert "orderBy:" not in sdl


async def test_manual_filter_input_can_preserve_existing_query_arguments(
    env: ExampleEnv,
) -> None:
    data = await execute_ok(
        env,
        """
        query($authorId: ID!) {
          reviews(first: 10, filter: {authorId: $authorId, query: "The"}) {
            edges {
              node {
                title
              }
            }
          }
        }
        """,
        variable_values={"authorId": str(env.ids["alice"])},
    )

    titles = {
        edge["node"]["title"]
        for edge in data["reviews"]["edges"]  # type: ignore[index]
    }
    assert titles == {
        "The Hobbit review",
        "The Silmarillion review",
    }


async def test_manual_order_input_can_preserve_existing_order_argument(
    env: ExampleEnv,
) -> None:
    data = await execute_ok(
        env,
        """
        query($authorId: ID!) {
          reviews(
            first: 10
            filter: {authorId: $authorId}
            order: {field: VOTES, order: DESC}
          ) {
            edges {
              node {
                title
              }
            }
          }
        }
        """,
        variable_values={"authorId": str(env.ids["alice"])},
    )

    assert data == {
        "reviews": {
            "edges": [
                {"node": {"title": "The Hobbit review"}},
                {"node": {"title": "A Wizard of Earthsea review"}},
                {"node": {"title": "The Silmarillion review"}},
            ]
        }
    }
