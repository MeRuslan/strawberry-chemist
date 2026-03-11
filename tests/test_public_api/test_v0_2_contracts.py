from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

from strawberry_chemist.relay.public import clear_node_registry


ROOT = Path(__file__).resolve().parents[2]
EXAMPLES_ROOT = ROOT / "examples" / "v0_2_api"


def load_example_app(example_name: str):
    clear_node_registry()
    module_name = f"tests._example_{example_name}"
    module_path = EXAMPLES_ROOT / example_name / "app.py"
    sys.modules.pop(module_name, None)
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


@pytest.mark.asyncio
async def test_v0_2_types_and_fields_contract() -> None:
    app = load_example_app("01_types_and_fields")
    engine, session_factory = app.create_engine_and_sessionmaker()
    await app.prepare_database(engine)
    await app.seed_data(session_factory)
    schema = app.build_schema()

    result = await schema.execute(
        """
        query {
          books {
            title
            publishedYear
            marketingLine
            titleWithIsbn
            yearsSincePublished
          }
        }
        """,
        context_value=app.AppContext(session_factory),
    )

    assert result.errors is None
    assert result.data == {
        "books": [
            {
                "title": "The Hobbit",
                "publishedYear": 1937,
                "marketingLine": "There and back again.",
                "titleWithIsbn": "The Hobbit (9780261103344)",
                "yearsSincePublished": 89,
            },
            {
                "title": "The Left Hand of Darkness",
                "publishedYear": 1969,
                "marketingLine": "Winter, politics, and estrangement.",
                "titleWithIsbn": "The Left Hand of Darkness (9780441478125)",
                "yearsSincePublished": 57,
            },
        ]
    }

    await engine.dispose()


@pytest.mark.asyncio
async def test_v0_2_relationships_contract() -> None:
    app = load_example_app("02_relationships")
    engine, session_factory = app.create_engine_and_sessionmaker()
    await app.prepare_database(engine)
    await app.seed_data(session_factory)
    schema = app.build_schema()

    result = await schema.execute(
        """
        query {
          authors {
            name
            publishedBooks {
              title
            }
            classicBooks {
              title
            }
            bookTitles
            publicationLabels
          }
        }
        """,
        context_value=app.AppContext(session_factory),
    )

    assert result.errors is None
    assert result.data == {
        "authors": [
            {
                "name": "J.R.R. Tolkien",
                "publishedBooks": [
                    {"title": "The Hobbit"},
                    {"title": "The Lord of the Rings"},
                    {"title": "The Silmarillion"},
                ],
                "classicBooks": [
                    {"title": "The Hobbit"},
                    {"title": "The Lord of the Rings"},
                ],
                "bookTitles": [
                    "The Hobbit",
                    "The Lord of the Rings",
                    "The Silmarillion",
                ],
                "publicationLabels": [
                    "The Hobbit (1937)",
                    "The Lord of the Rings (1954)",
                    "The Silmarillion (1977)",
                ],
            },
            {
                "name": "Ursula K. Le Guin",
                "publishedBooks": [{"title": "A Wizard of Earthsea"}],
                "classicBooks": [],
                "bookTitles": ["A Wizard of Earthsea"],
                "publicationLabels": ["A Wizard of Earthsea (1968)"],
            },
        ]
    }

    await engine.dispose()


@pytest.mark.asyncio
async def test_v0_2_connections_filters_and_ordering_contract() -> None:
    app = load_example_app("03_connections_filters_and_ordering")
    engine, session_factory = app.create_engine_and_sessionmaker()
    await app.prepare_database(engine)
    await app.seed_data(session_factory)
    schema = app.build_schema()

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
        context_value=app.AppContext(session_factory),
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
        context_value=app.AppContext(session_factory),
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
async def test_v0_2_nodes_and_relay_ids_contract() -> None:
    app = load_example_app("04_nodes_and_relay_ids")
    engine, session_factory = app.create_engine_and_sessionmaker()
    await app.prepare_database(engine)
    await app.seed_data(session_factory)
    schema = app.build_schema()
    legacy_id = app.LEGACY_CODEC.encode("LegacyBookmark", ("5",))

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
        context_value=app.AppContext(session_factory),
    )

    assert result.errors is None
    assert result.data == {
        "book": {"__typename": "Book", "title": "The Hobbit"},
        "shelf": {"__typename": "Shelf", "label": "Favorites"},
        "membership": {"__typename": "Membership", "role": "owner"},
        "legacy": {"__typename": "LegacyBookmark", "label": "Pinned entry"},
    }

    await engine.dispose()


@pytest.mark.asyncio
async def test_v0_2_context_and_extensions_contract() -> None:
    app = load_example_app("05_context_and_extensions")
    engine, session_factory = app.create_engine_and_sessionmaker()
    await app.prepare_database(engine)
    await app.seed_data(session_factory)
    schema = app.build_schema()

    result = await schema.execute(
        """
        query {
          featuredBook(slug: "hobbit") {
            title
            requestLabel
          }
          publishers {
            name
            books {
              title
              requestLabel
            }
          }
        }
        """,
        context_value=app.AppContext(session_factory, request_id="req-001"),
    )

    assert result.errors is None
    assert result.data == {
        "featuredBook": {
            "title": "The Hobbit",
            "requestLabel": "req-001:The Hobbit",
        },
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

    await engine.dispose()


@pytest.mark.asyncio
async def test_v0_2_manual_filters_and_orders_contract() -> None:
    app = load_example_app("06_manual_filters_and_orders")
    schema = app.build_schema()
    sdl = schema.as_str()

    assert "input LegacyReviewFilter" in sdl
    assert "authorId: ID!" in sdl
    assert "input LegacyReviewOrder" in sdl
    assert "order: LegacyOrderDirection!" in sdl
    assert "filter: LegacyReviewFilter!" in sdl
    assert "order: LegacyReviewOrder" in sdl
    assert "orderBy:" not in sdl

    engine, session_factory = app.create_engine_and_sessionmaker()
    await app.prepare_database(engine)
    ids = await app.seed_data(session_factory)

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
        context_value=app.AppContext(session_factory),
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
