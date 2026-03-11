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
async def test_cursor_connection_applies_filtering_and_multi_clause_ordering() -> None:
    engine, session_factory = create_engine_and_sessionmaker()
    await prepare_database(engine)
    await seed_data(session_factory)
    schema = build_schema()

    result = await schema.execute(
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
        context_value=AppContext(session_factory),
    )

    assert result.errors is None
    assert result.data == {
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

    await engine.dispose()


@pytest.mark.asyncio
async def test_offset_connection_supports_null_ordering_and_total_count() -> None:
    engine, session_factory = create_engine_and_sessionmaker()
    await prepare_database(engine)
    await seed_data(session_factory)
    schema = build_schema()

    result = await schema.execute(
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
        context_value=AppContext(session_factory),
    )

    assert result.errors is None
    assert result.data == {
        "booksPage": {
            "items": [
                {"title": "The Hobbit", "ranking": 8},
                {"title": "The Lord of the Rings", "ranking": 10},
            ],
            "totalCount": 3,
        }
    }

    await engine.dispose()


@pytest.mark.asyncio
async def test_filters_support_boolean_composition() -> None:
    engine, session_factory = create_engine_and_sessionmaker()
    await prepare_database(engine)
    await seed_data(session_factory)
    schema = build_schema()

    result = await schema.execute(
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
        context_value=AppContext(session_factory),
    )

    assert result.errors is None
    assert result.data == {
        "books": {
            "edges": [
                {"node": {"title": "The Hobbit", "year": 1937}},
                {"node": {"title": "The Left Hand of Darkness", "year": 1969}},
            ]
        }
    }

    await engine.dispose()
