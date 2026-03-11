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


def test_schema_exposes_alias_and_computed_fields() -> None:
    sdl = build_schema().as_str()

    assert "publishedYear: Int!" in sdl
    assert "marketingLine: String!" in sdl
    assert "titleWithIsbn: String!" in sdl
    assert "yearsSincePublished: Int!" in sdl


async def test_scalar_aliases_are_loaded_from_model_columns(env: ExampleEnv) -> None:
    data = await execute_ok(
        env,
        """
        query {
          books {
            title
            publishedYear
            marketingLine
          }
        }
        """,
    )

    assert data == {
        "books": [
            {
                "title": "The Hobbit",
                "publishedYear": 1937,
                "marketingLine": "There and back again.",
            },
            {
                "title": "The Left Hand of Darkness",
                "publishedYear": 1969,
                "marketingLine": "Winter, politics, and estrangement.",
            },
        ]
    }


async def test_computed_fields_can_project_their_selected_columns(
    env: ExampleEnv,
) -> None:
    data = await execute_ok(
        env,
        """
        query {
          books {
            title
            titleWithIsbn
            yearsSincePublished
          }
        }
        """,
    )

    assert data == {
        "books": [
            {
                "title": "The Hobbit",
                "titleWithIsbn": "The Hobbit (9780261103344)",
                "yearsSincePublished": 89,
            },
            {
                "title": "The Left Hand of Darkness",
                "titleWithIsbn": "The Left Hand of Darkness (9780441478125)",
                "yearsSincePublished": 57,
            },
        ]
    }
