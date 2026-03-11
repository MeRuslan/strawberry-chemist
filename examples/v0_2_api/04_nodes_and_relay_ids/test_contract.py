from __future__ import annotations

import pytest

from app import (
    AppContext,
    LEGACY_CODEC,
    build_schema,
    create_engine_and_sessionmaker,
    prepare_database,
    seed_data,
)


@pytest.mark.asyncio
async def test_readable_and_custom_relay_ids_resolve_through_node_field() -> None:
    engine, session_factory = create_engine_and_sessionmaker()
    await prepare_database(engine)
    await seed_data(session_factory)
    schema = build_schema()
    legacy_id = LEGACY_CODEC.encode("LegacyBookmark", ("5",))

    result = await schema.execute(
        """
        query Lookup($bookId: ID!, $shelfId: ID!, $membershipId: ID!, $legacyId: ID!) {
          book(id: $bookId) {
            __typename
            ... on Book {
              title
            }
          }
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
          legacy: node(id: $legacyId) {
            __typename
            ... on LegacyBookmark {
              label
            }
          }
        }
        """,
        variable_values={
            "bookId": "Book_1",
            "shelfId": "Shelf_favorites",
            "membershipId": "Membership_10,20",
            "legacyId": legacy_id,
        },
        context_value=AppContext(session_factory),
    )

    assert result.errors is None
    assert result.data == {
        "book": {"__typename": "Book", "title": "The Hobbit"},
        "shelf": {"__typename": "Shelf", "label": "Favorites"},
        "membership": {"__typename": "Membership", "role": "owner"},
        "legacy": {"__typename": "LegacyBookmark", "label": "Pinned entry"},
    }

    await engine.dispose()
