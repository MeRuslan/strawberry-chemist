from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass

import pytest_asyncio
import strawberry
from app import (
    AppContext,
    build_context,
    build_schema,
    build_unconfigured_schema,
    create_engine_and_sessionmaker,
    prepare_database,
    seed_data,
)


@dataclass
class ExampleEnv:
    schema: strawberry.Schema
    context: AppContext
    ids: dict[str, int]


@pytest_asyncio.fixture
async def env() -> AsyncIterator[ExampleEnv]:
    engine, session_factory = create_engine_and_sessionmaker()
    await prepare_database(engine)
    ids = await seed_data(session_factory)
    try:
        yield ExampleEnv(
            schema=build_schema(),
            context=build_context(session_factory),
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
        context_value=env.context,
    )
    assert result.errors is None
    assert result.data is not None
    return result.data


def test_unconfigured_schema_keeps_detached_preview_type() -> None:
    sdl = build_unconfigured_schema().as_str()

    assert "type DetachedTranslationPreview" in sdl
    assert "interface TranslationPreview" in sdl
    assert "preview: TranslationPreview!" in sdl


async def test_unconfigured_schema_supports_fragments_on_detached_preview_type(
    env: ExampleEnv,
) -> None:
    result = await build_unconfigured_schema().execute(
        """
        query {
          preview {
            __typename
            locale
            ... on DetachedTranslationPreview {
              title
            }
          }
        }
        """,
        context_value=env.context,
    )

    assert result.errors is None
    assert result.data == {
        "preview": {
            "__typename": "DetachedTranslationPreview",
            "locale": "fr",
            "title": "Bilbo le Hobbit",
        }
    }


def test_configured_schema_documents_supported_and_unsafe_paths() -> None:
    sdl = build_schema().as_str()

    assert "type Book {" in sdl
    assert "isbnValue: String!" in sdl
    assert "label: String!" in sdl

    assert "type MixedInBook {" in sdl
    assert "directIsbn: String!" in sdl
    assert "mixinLabel" not in sdl
    assert "mixinTranslationLocales" not in sdl

    assert "type BookNode implements Node" in sdl
    assert "translations: [Translation!]!" in sdl
    assert "type Translation {" in sdl
    assert "type DetachedTranslationPreview" in sdl
    assert "interface TranslationPreview" in sdl
    assert "preview: TranslationPreview!" in sdl


async def test_configured_schema_preserves_detached_preview_fragment_target(
    env: ExampleEnv,
) -> None:
    result = await env.schema.execute(
        """
        query {
          preview {
            __typename
            locale
            ... on DetachedTranslationPreview {
              title
            }
          }
        }
        """,
        context_value=env.context,
    )

    assert result.errors is None
    assert result.data == {
        "preview": {
            "__typename": "DetachedTranslationPreview",
            "locale": "fr",
            "title": "Bilbo le Hobbit",
        }
    }


async def test_subclassed_chemist_bases_resolve_inherited_fields(
    env: ExampleEnv,
) -> None:
    data = await execute_ok(
        env,
        """
        query {
          books {
            title
            year
            isbnValue
            label
          }
          mixedInBooks {
            title
            year
            directIsbn
          }
        }
        """,
    )

    assert data == {
        "books": [
            {
                "title": "The Hobbit",
                "year": 1937,
                "isbnValue": "9780261103344",
                "label": "The Hobbit (9780261103344)",
            },
            {
                "title": "A Wizard of Earthsea",
                "year": 1968,
                "isbnValue": "9780547773742",
                "label": "A Wizard of Earthsea (9780547773742)",
            },
        ],
        "mixedInBooks": [
            {
                "title": "The Hobbit",
                "year": 1937,
                "directIsbn": "9780261103344",
            },
            {
                "title": "A Wizard of Earthsea",
                "year": 1968,
                "directIsbn": "9780547773742",
            },
        ],
    }


async def test_complex_node_inheritance_keeps_base_fields_and_relationships(
    env: ExampleEnv,
) -> None:
    book_data = await execute_ok(
        env,
        """
        query($bookId: ID!) {
          book(id: $bookId) {
            __typename
            ... on BookNode {
              id
              title
              year
              isbnValue
              label
              translations {
                locale
                title
              }
            }
          }
        }
        """,
        variable_values={"bookId": f"BookNode_{env.ids['hobbit']}"},
    )

    assert book_data["book"] == {
        "__typename": "BookNode",
        "id": f"BookNode_{env.ids['hobbit']}",
        "title": "The Hobbit",
        "year": 1937,
        "isbnValue": "9780261103344",
        "label": "The Hobbit (9780261103344)",
        "translations": [
            {"locale": "fr", "title": "Bilbo le Hobbit"},
            {"locale": "es", "title": "El Hobbit"},
        ],
    }

    node_list_data = await execute_ok(
        env,
        """
        query {
          bookNodes {
            id
            title
            year
            label
            translations {
              locale
            }
          }
        }
        """,
    )

    assert node_list_data["bookNodes"] == [
        {
            "id": f"BookNode_{env.ids['hobbit']}",
            "title": "The Hobbit",
            "year": 1937,
            "label": "The Hobbit (9780261103344)",
            "translations": [{"locale": "fr"}, {"locale": "es"}],
        },
        {
            "id": f"BookNode_{env.ids['earthsea']}",
            "title": "A Wizard of Earthsea",
            "year": 1968,
            "label": "A Wizard of Earthsea (9780547773742)",
            "translations": [{"locale": "de"}],
        },
    ]
