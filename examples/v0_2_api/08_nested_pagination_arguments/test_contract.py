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
async def test_nested_pagination_arguments_contract() -> None:
    engine, session_factory = create_engine_and_sessionmaker()
    await prepare_database(engine)
    await seed_data(session_factory)
    schema = build_schema()
    sdl = schema.as_str()

    assert "books(pagination: CursorPaginationInput)" in sdl
    assert "booksPage(pagination: LimitOffsetPaginationInput)" in sdl
    assert "books(first:" not in sdl
    assert "booksPage(limit:" not in sdl

    cursor_result = await schema.execute(
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
        context_value=AppContext(session_factory),
    )

    assert cursor_result.errors is None
    assert cursor_result.data == {
        "books": {
            "edges": [
                {"node": {"title": "The Hobbit", "year": 1937}},
                {"node": {"title": "The Lord of the Rings", "year": 1954}},
            ],
            "pageInfo": {"hasNextPage": True, "hasPreviousPage": False},
        }
    }

    offset_result = await schema.execute(
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
        context_value=AppContext(session_factory),
    )

    assert offset_result.errors is None
    assert offset_result.data == {
        "booksPage": {
            "items": [
                {"title": "The Lord of the Rings", "year": 1954},
                {"title": "The Left Hand of Darkness", "year": 1969},
            ],
            "totalCount": 3,
        }
    }

    await engine.dispose()
