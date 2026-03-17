from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass

import pytest_asyncio
import strawberry
import strawberry_chemist as sc
from strawberry_chemist.relay import clear_node_registry


clear_node_registry()

from app import (  # noqa: E402
    Book,
    build_context,
    build_schema,
    create_engine_and_sessionmaker,
    prepare_database,
    seed_data,
)


@dataclass
class ExampleEnv:
    schema: strawberry.Schema
    session_factory: object
    ids: dict[str, int]


@pytest_asyncio.fixture
async def env() -> AsyncIterator[ExampleEnv]:
    engine, session_factory = create_engine_and_sessionmaker()
    await prepare_database(engine)
    ids = await seed_data(session_factory)
    try:
        yield ExampleEnv(
            schema=build_schema(),
            session_factory=session_factory,
            ids=ids,
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
        context_value=build_context(env.session_factory),
    )
    assert result.errors is None
    assert result.data is not None
    return result.data


def test_schema_exposes_only_public_resolver_params() -> None:
    sdl = build_schema().as_str()

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


async def test_resolver_argument_contract_executes_as_documented(
    env: ExampleEnv,
) -> None:
    book_id = sc.relay.encode_node_id(env.schema, Book, values=[env.ids["hobbit"]])
    data = await execute_ok(
        env,
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
    )

    assert data == {
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


async def test_connection_custom_arg_marks_loaded_cursor_page(
    env: ExampleEnv,
) -> None:
    data = await execute_ok(
        env,
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
    )

    assert data == {
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
