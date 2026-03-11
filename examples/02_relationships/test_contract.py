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


async def test_relationship_field_returns_all_related_rows(env: ExampleEnv) -> None:
    data = await execute_ok(
        env,
        """
        query {
          authors {
            name
            publishedBooks {
              title
            }
          }
        }
        """,
    )

    assert data == {
        "authors": [
            {
                "name": "J.R.R. Tolkien",
                "publishedBooks": [
                    {"title": "The Hobbit"},
                    {"title": "The Lord of the Rings"},
                    {"title": "The Silmarillion"},
                ],
            },
            {
                "name": "Ursula K. Le Guin",
                "publishedBooks": [{"title": "A Wizard of Earthsea"}],
            },
        ]
    }


async def test_scoped_relationship_field_applies_where_clause(env: ExampleEnv) -> None:
    data = await execute_ok(
        env,
        """
        query {
          authors {
            name
            classicBooks {
              title
            }
          }
        }
        """,
    )

    assert data == {
        "authors": [
            {
                "name": "J.R.R. Tolkien",
                "classicBooks": [
                    {"title": "The Hobbit"},
                    {"title": "The Lord of the Rings"},
                ],
            },
            {
                "name": "Ursula K. Le Guin",
                "classicBooks": [],
            },
        ]
    }


async def test_relationship_transform_can_project_selected_fields(
    env: ExampleEnv,
) -> None:
    data = await execute_ok(
        env,
        """
        query {
          authors {
            name
            bookTitles
          }
        }
        """,
    )

    assert data == {
        "authors": [
            {
                "name": "J.R.R. Tolkien",
                "bookTitles": [
                    "The Hobbit",
                    "The Lord of the Rings",
                    "The Silmarillion",
                ],
            },
            {
                "name": "Ursula K. Le Guin",
                "bookTitles": ["A Wizard of Earthsea"],
            },
        ]
    }


async def test_full_load_relationship_transform_can_use_unselected_columns(
    env: ExampleEnv,
) -> None:
    data = await execute_ok(
        env,
        """
        query {
          authors {
            name
            publicationLabels
          }
        }
        """,
    )

    assert data == {
        "authors": [
            {
                "name": "J.R.R. Tolkien",
                "publicationLabels": [
                    "The Hobbit (1937)",
                    "The Lord of the Rings (1954)",
                    "The Silmarillion (1977)",
                ],
            },
            {
                "name": "Ursula K. Le Guin",
                "publicationLabels": ["A Wizard of Earthsea (1968)"],
            },
        ]
    }
