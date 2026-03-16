from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest
import strawberry_chemist as sc

from strawberry_chemist.relay.public import clear_node_registry


ROOT = Path(__file__).resolve().parents[2]
EXAMPLES_ROOT = ROOT / "examples"


def load_example_app(example_name: str):
    clear_node_registry()
    module_name = f"tests._example_{example_name}"
    example_dir = EXAMPLES_ROOT / example_name
    module_path = example_dir / "app.py"
    sys.modules.pop(module_name, None)
    sys.modules.pop("db", None)
    sys.modules.pop("schema", None)
    sys.path.insert(0, str(example_dir))
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    sys.modules[module_name] = module
    try:
        spec.loader.exec_module(module)
    finally:
        if sys.path and sys.path[0] == str(example_dir):
            sys.path.pop(0)
    return module


@pytest.mark.asyncio
async def test_public_types_and_fields_contract() -> None:
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
        context_value=app.build_context(session_factory),
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
async def test_public_relationships_contract() -> None:
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
        context_value=app.build_context(session_factory),
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
async def test_public_connections_filters_and_ordering_contract() -> None:
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
        context_value=app.build_context(session_factory),
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
        context_value=app.build_context(session_factory),
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
async def test_public_nodes_and_relay_ids_contract() -> None:
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
        context_value=app.build_context(session_factory),
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
async def test_public_context_and_extensions_contract() -> None:
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
        context_value=app.build_context(session_factory, request_id="req-001"),
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
async def test_public_manual_filters_and_orders_contract() -> None:
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
        context_value=app.build_context(session_factory),
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


@pytest.mark.asyncio
async def test_public_node_lookup_and_permissions_contract() -> None:
    app = load_example_app("07_node_lookup_and_permissions")
    schema = app.build_schema()
    sdl = schema.as_str()

    assert "postById(postId: ID!): Post" in sdl
    assert "renamePost(postId: ID!, title: String!): Post" in sdl
    assert " post:" not in sdl

    engine, session_factory = app.create_engine_and_sessionmaker()
    await app.prepare_database(engine)
    ids = await app.seed_data(session_factory)

    post_result = await schema.execute(
        """
        query($postId: ID!, $userId: ID!) {
          postById(postId: $postId) {
            title
          }
          mismatch: postById(postId: $userId) {
            title
          }
        }
        """,
        variable_values={
            "postId": f"Post_{ids['first_post']}",
            "userId": f"User_{ids['alice']}",
        },
        context_value=app.build_context(session_factory, current_user_id=None),
    )

    assert post_result.errors is None
    assert post_result.data == {
        "postById": {"title": "Draft one"},
        "mismatch": None,
    }

    rename_result = await schema.execute(
        """
        mutation($postId: ID!) {
          renamePost(postId: $postId, title: "Renamed draft") {
            title
          }
        }
        """,
        variable_values={"postId": f"Post_{ids['first_post']}"},
        context_value=app.build_context(
            session_factory,
            current_user_id=ids["alice"],
        ),
    )

    assert rename_result.errors is None
    assert rename_result.data == {
        "renamePost": {"title": "Renamed draft"},
    }

    denied_result = await schema.execute(
        """
        mutation($postId: ID!) {
          renamePost(postId: $postId, title: "Nope") {
            title
          }
        }
        """,
        variable_values={"postId": f"Post_{ids['first_post']}"},
        context_value=app.build_context(
            session_factory,
            current_user_id=ids["bob"],
        ),
    )

    assert denied_result.data is None or denied_result.data["renamePost"] is None
    assert denied_result.errors is not None

    unauthenticated_result = await schema.execute(
        """
        mutation($postId: ID!) {
          renamePost(postId: $postId, title: "Nope") {
            title
          }
        }
        """,
        variable_values={"postId": f"Post_{ids['first_post']}"},
        context_value=app.build_context(session_factory, current_user_id=None),
    )

    assert (
        unauthenticated_result.data is None
        or unauthenticated_result.data["renamePost"] is None
    )
    assert unauthenticated_result.errors is not None

    await engine.dispose()


@pytest.mark.asyncio
async def test_public_nested_pagination_arguments_contract() -> None:
    app = load_example_app("08_nested_pagination_arguments")
    engine, session_factory = app.create_engine_and_sessionmaker()
    await app.prepare_database(engine)
    await app.seed_data(session_factory)
    schema = app.build_schema()

    result = await schema.execute(
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
        context_value=app.build_context(session_factory),
    )

    assert result.errors is None
    assert result.data == {
        "books": {
            "edges": [
                {"node": {"title": "The Hobbit", "year": 1937}},
                {"node": {"title": "The Lord of the Rings", "year": 1954}},
            ],
            "pageInfo": {"hasNextPage": True, "hasPreviousPage": False},
        }
    }

    result = await schema.execute(
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
        context_value=app.build_context(session_factory),
    )

    assert result.errors is None
    assert result.data == {
        "booksPage": {
            "items": [
                {"title": "The Lord of the Rings", "year": 1954},
                {"title": "The Left Hand of Darkness", "year": 1969},
            ],
            "totalCount": 3,
        }
    }

    await engine.dispose()


@pytest.mark.asyncio
async def test_public_resolver_argument_contracts() -> None:
    app = load_example_app("09_resolver_argument_contracts")
    schema = app.build_schema()
    sdl = schema.as_str()

    assert "titledWith(prefix: String!): String!" in sdl
    assert "catalogLabel(suffix: String!): String!" in sdl
    assert "catalogLabel(title:" not in sdl
    assert "catalogLabel(year:" not in sdl
    assert "joinedTitles(separator: String!): String!" in sdl
    assert "joinedTitles(books:" not in sdl
    assert "booksMatching(" in sdl
    assert "titlePrefix: String!" in sdl
    assert "first: Int!" in sdl
    assert "after: String" in sdl
    assert "loadedConnection" not in sdl
    assert "bookLabel(bookId: ID!, prefix: String!): String" in sdl
    assert "bookLabel(book:" not in sdl
    assert "plainSummary: String!" in sdl
    assert "titleMatchesPrefix: Boolean!" in sdl
    assert "manualBadge: String!" in sdl
    assert "contractVersion: String!" in sdl

    engine, session_factory = app.create_engine_and_sessionmaker()
    await app.prepare_database(engine)
    ids = await app.seed_data(session_factory)
    book_id = sc.relay.encode_node_id(schema, app.Book, values=[ids["hobbit"]])

    result = await schema.execute(
        """
        query ResolverContracts($bookId: ID!) {
          contractVersion
          books {
            title
            titledWith(prefix: "Read: ")
            catalogLabel(suffix: ".")
            plainSummary
          }
          authors {
            name
            joinedTitles(separator: " / ")
            manualBadge
            booksMatching(first: 10, titlePrefix: "The") {
              edges {
                node {
                  title
                  titleMatchesPrefix
                }
              }
              pageInfo {
                hasNextPage
                hasPreviousPage
              }
            }
          }
          bookLabel(bookId: $bookId, prefix: "NODE: ")
        }
        """,
        variable_values={"bookId": str(book_id)},
        context_value=app.build_context(session_factory),
    )

    assert result.errors is None
    assert result.data == {
        "contractVersion": "resolver-args-v1",
        "books": [
            {
                "title": "The Hobbit",
                "titledWith": "Read: The Hobbit",
                "catalogLabel": "The Hobbit (1937).",
                "plainSummary": "The Hobbit [1937]",
            },
            {
                "title": "The Lord of the Rings",
                "titledWith": "Read: The Lord of the Rings",
                "catalogLabel": "The Lord of the Rings (1954).",
                "plainSummary": "The Lord of the Rings [1954]",
            },
            {
                "title": "A Wizard of Earthsea",
                "titledWith": "Read: A Wizard of Earthsea",
                "catalogLabel": "A Wizard of Earthsea (1968).",
                "plainSummary": "A Wizard of Earthsea [1968]",
            },
        ],
        "authors": [
            {
                "name": "J.R.R. Tolkien",
                "joinedTitles": "The Hobbit / The Lord of the Rings",
                "manualBadge": "manual:United Kingdom",
                "booksMatching": {
                    "edges": [
                        {
                            "node": {
                                "title": "The Hobbit",
                                "titleMatchesPrefix": True,
                            }
                        },
                        {
                            "node": {
                                "title": "The Lord of the Rings",
                                "titleMatchesPrefix": True,
                            }
                        },
                    ],
                    "pageInfo": {
                        "hasNextPage": False,
                        "hasPreviousPage": False,
                    },
                },
            },
            {
                "name": "Ursula K. Le Guin",
                "joinedTitles": "A Wizard of Earthsea",
                "manualBadge": "manual:United States",
                "booksMatching": {
                    "edges": [
                        {
                            "node": {
                                "title": "A Wizard of Earthsea",
                                "titleMatchesPrefix": False,
                            }
                        }
                    ],
                    "pageInfo": {
                        "hasNextPage": False,
                        "hasPreviousPage": False,
                    },
                },
            },
        ],
        "bookLabel": "NODE: The Hobbit",
    }

    paginated_result = await schema.execute(
        """
        query {
          authors {
            name
            booksMatching(first: 1, titlePrefix: "The") {
              edges {
                node {
                  titleMatchesPrefix
                }
              }
              pageInfo {
                hasNextPage
                hasPreviousPage
              }
            }
          }
        }
        """,
        context_value=app.build_context(session_factory),
    )

    assert paginated_result.errors is None
    assert paginated_result.data == {
        "authors": [
            {
                "name": "J.R.R. Tolkien",
                "booksMatching": {
                    "edges": [
                        {
                            "node": {
                                "titleMatchesPrefix": True,
                            }
                        }
                    ],
                    "pageInfo": {
                        "hasNextPage": True,
                        "hasPreviousPage": False,
                    },
                },
            },
            {
                "name": "Ursula K. Le Guin",
                "booksMatching": {
                    "edges": [
                        {
                            "node": {
                                "titleMatchesPrefix": False,
                            }
                        }
                    ],
                    "pageInfo": {
                        "hasNextPage": False,
                        "hasPreviousPage": False,
                    },
                },
            },
        ]
    }

    await engine.dispose()
