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
    context: AppContext


@pytest_asyncio.fixture
async def env() -> AsyncIterator[ExampleEnv]:
    engine, session_factory = create_engine_and_sessionmaker()
    await prepare_database(engine)
    await seed_data(session_factory)
    try:
        yield ExampleEnv(
            schema=build_schema(),
            context=AppContext(session_factory, request_id="req-001"),
        )
    finally:
        await engine.dispose()


async def execute_ok(env: ExampleEnv, query: str) -> dict[str, object]:
    result = await env.schema.execute(query, context_value=env.context)
    assert result.errors is None
    assert result.data is not None
    return result.data


async def test_root_resolver_objects_share_context_with_chemist_fields(
    env: ExampleEnv,
) -> None:
    data = await execute_ok(
        env,
        """
        query {
          featuredBook(slug: "hobbit") {
            title
            requestLabel
          }
        }
        """,
    )

    assert data == {
        "featuredBook": {
            "title": "The Hobbit",
            "requestLabel": "req-001:The Hobbit",
        },
    }


async def test_relationship_fields_can_read_application_specific_context(
    env: ExampleEnv,
) -> None:
    data = await execute_ok(
        env,
        """
        query {
          publishers {
            name
            books {
              title
              requestLabel
            }
          }
        }
        """,
    )

    assert data == {
        "publishers": [
            {
                "name": "Ace",
                "books": [
                    {
                        "title": "The Left Hand of Darkness",
                        "requestLabel": "req-001:The Left Hand of Darkness",
                    }
                ],
            },
            {
                "name": "Orbit",
                "books": [
                    {
                        "title": "The Hobbit",
                        "requestLabel": "req-001:The Hobbit",
                    }
                ],
            },
        ],
    }
