from __future__ import annotations

import pytest

from app import (
    AppContext,
    build_schema,
    create_engine_and_sessionmaker,
    prepare_database,
    seed_data,
)


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


@pytest.mark.asyncio
async def test_manual_filter_and_order_can_preserve_existing_query_contracts() -> None:
    engine, session_factory = create_engine_and_sessionmaker()
    await prepare_database(engine)
    ids = await seed_data(session_factory)
    schema = build_schema()

    result = await schema.execute(
        """
        query($authorId: ID!) {
          reviews(
            first: 10
            filter: {authorId: $authorId, query: "The"}
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
        variable_values={"authorId": str(ids["alice"])},
        context_value=AppContext(session_factory),
    )

    assert result.errors is None
    assert result.data == {
        "reviews": {
            "edges": [
                {"node": {"title": "The Hobbit review"}},
                {"node": {"title": "The Silmarillion review"}},
            ]
        }
    }

    await engine.dispose()
