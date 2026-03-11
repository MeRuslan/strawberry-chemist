from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass

import pytest_asyncio
import strawberry
from app import (
    AppContext,
    LEGACY_CODEC,
    build_schema,
    create_engine_and_sessionmaker,
    prepare_database,
    seed_data,
)


@dataclass
class ExampleEnv:
    schema: strawberry.Schema
    context: AppContext
    legacy_id: str


@pytest_asyncio.fixture
async def env() -> AsyncIterator[ExampleEnv]:
    engine, session_factory = create_engine_and_sessionmaker()
    await prepare_database(engine)
    await seed_data(session_factory)
    try:
        yield ExampleEnv(
            schema=build_schema(),
            context=AppContext(session_factory),
            legacy_id=LEGACY_CODEC.encode("LegacyBookmark", ("5",)),
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


def test_schema_exposes_root_node_fields() -> None:
    sdl = build_schema().as_str()

    assert "node(id: ID!): " in sdl
    assert "book(id: ID!): Book" in sdl


async def test_root_book_field_resolves_default_relay_ids(env: ExampleEnv) -> None:
    data = await execute_ok(
        env,
        """
        query($bookId: ID!) {
          book(id: $bookId) {
            __typename
            ... on Book {
              title
            }
          }
        }
        """,
        variable_values={"bookId": "Book_1"},
    )

    assert data == {
        "book": {"__typename": "Book", "title": "The Hobbit"},
    }


async def test_node_field_resolves_custom_and_composite_ids(env: ExampleEnv) -> None:
    data = await execute_ok(
        env,
        """
        query($shelfId: ID!, $membershipId: ID!) {
          shelf: node(id: $shelfId) {
            __typename
            ... on Shelf {
              label
            }
          }
          membership: node(id: $membershipId) {
            __typename
            ... on Membership {
              role
            }
          }
        }
        """,
        variable_values={
            "shelfId": "Shelf_favorites",
            "membershipId": "Membership_10,20",
        },
    )

    assert data == {
        "shelf": {"__typename": "Shelf", "label": "Favorites"},
        "membership": {"__typename": "Membership", "role": "owner"},
    }


async def test_node_field_resolves_legacy_codec_ids(env: ExampleEnv) -> None:
    data = await execute_ok(
        env,
        """
        query($legacyId: ID!) {
          legacy: node(id: $legacyId) {
            __typename
            ... on LegacyBookmark {
              label
            }
          }
        }
        """,
        variable_values={"legacyId": env.legacy_id},
    )

    assert data == {
        "legacy": {"__typename": "LegacyBookmark", "label": "Pinned entry"},
    }
