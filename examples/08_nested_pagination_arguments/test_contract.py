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


@pytest_asyncio.fixture
async def env() -> AsyncIterator[ExampleEnv]:
    engine, session_factory = create_engine_and_sessionmaker()
    await prepare_database(engine)
    await seed_data(session_factory)
    try:
        yield ExampleEnv(
            schema=build_schema(),
            context=build_context(session_factory),
        )
    finally:
        await engine.dispose()


async def execute_ok(env: ExampleEnv, query: str) -> dict[str, object]:
    result = await env.schema.execute(query, context_value=env.context)
    assert result.errors is None
    assert result.data is not None
    return result.data


def test_schema_uses_nested_pagination_arguments() -> None:
    sdl = build_schema().as_str()

    assert "books(pagination: CursorPaginationInput)" in sdl
    assert "booksPage(pagination: LimitOffsetPaginationInput)" in sdl
    assert "books(first:" not in sdl
    assert "booksPage(limit:" not in sdl


async def test_cursor_connection_accepts_nested_pagination_input(
    env: ExampleEnv,
) -> None:
    data = await execute_ok(
        env,
        """
        query {
          books(pagination: {first: 2}) {
            edges {
              node {
                title
                year
              }
            }
            pageInfo {
              hasNextPage
              hasPreviousPage
            }
          }
        }
        """,
    )

    assert data == {
        "books": {
            "edges": [
                {"node": {"title": "The Hobbit", "year": 1937}},
                {"node": {"title": "The Lord of the Rings", "year": 1954}},
            ],
            "pageInfo": {"hasNextPage": True, "hasPreviousPage": False},
        }
    }


async def test_offset_connection_accepts_nested_pagination_input(
    env: ExampleEnv,
) -> None:
    data = await execute_ok(
        env,
        """
        query {
          booksPage(pagination: {limit: 2, offset: 1}) {
            items {
              title
              year
            }
            totalCount
          }
        }
        """,
    )

    assert data == {
        "booksPage": {
            "items": [
                {"title": "The Lord of the Rings", "year": 1954},
                {"title": "The Left Hand of Darkness", "year": 1969},
            ],
            "totalCount": 3,
        }
    }
