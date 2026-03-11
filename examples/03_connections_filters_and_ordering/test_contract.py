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


def test_schema_exposes_filter_and_order_arguments() -> None:
    sdl = build_schema().as_str()

    assert "books(" in sdl
    assert "filter: BookFilter" in sdl
    assert "orderBy: [BookOrderItem!]" in sdl
    assert "rankedBooks(" in sdl
    assert "booksPage(" in sdl


async def test_cursor_connection_applies_filtering_and_multi_clause_ordering(
    env: ExampleEnv,
) -> None:
    data = await execute_ok(
        env,
        """
        query {
          books(
            first: 2
            filter: {
              authorName: {eq: "J.R.R. Tolkien"}
              publishedAfter: 1930
            }
            orderBy: [
              {field: YEAR, direction: DESC}
              {field: TITLE, direction: ASC}
            ]
          ) {
            edges {
              node {
                title
                year
                ranking
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
                {
                    "node": {
                        "title": "The Lord of the Rings",
                        "year": 1954,
                        "ranking": 10,
                    }
                },
                {"node": {"title": "The Hobbit", "year": 1937, "ranking": 8}},
            ],
            "pageInfo": {"hasNextPage": False, "hasPreviousPage": False},
        }
    }


async def test_offset_connection_supports_null_ordering_and_total_count(
    env: ExampleEnv,
) -> None:
    data = await execute_ok(
        env,
        """
        query {
          booksPage(
            limit: 2
            offset: 0
            filter: {title: {contains: "The"}}
            orderBy: [{field: RANKING, direction: ASC, nulls: LAST}]
          ) {
            items {
              title
              ranking
            }
            totalCount
          }
        }
        """,
    )

    assert data == {
        "booksPage": {
            "items": [
                {"title": "The Hobbit", "ranking": 8},
                {"title": "The Lord of the Rings", "ranking": 10},
            ],
            "totalCount": 3,
        }
    }


async def test_connection_where_and_default_order_by_can_define_server_owned_order(
    env: ExampleEnv,
) -> None:
    data = await execute_ok(
        env,
        """
        query {
          rankedBooks(first: 10) {
            edges {
              node {
                title
                ranking
              }
            }
          }
        }
        """,
    )

    assert data == {
        "rankedBooks": {
            "edges": [
                {"node": {"title": "The Lord of the Rings", "ranking": 10}},
                {"node": {"title": "The Hobbit", "ranking": 8}},
            ]
        }
    }


async def test_filters_support_boolean_composition(env: ExampleEnv) -> None:
    data = await execute_ok(
        env,
        """
        query {
          books(
            first: 10
            filter: {
              or: [
                {title: {contains: "Hobbit"}}
                {year: {eq: 1969}}
              ]
            }
            orderBy: [{field: YEAR, direction: ASC}]
          ) {
            edges {
              node {
                title
                year
              }
            }
          }
        }
        """,
    )

    assert data == {
        "books": {
            "edges": [
                {"node": {"title": "The Hobbit", "year": 1937}},
                {"node": {"title": "The Left Hand of Darkness", "year": 1969}},
            ]
        }
    }
