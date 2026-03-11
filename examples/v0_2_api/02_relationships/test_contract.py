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
async def test_relationship_fields_support_scoping_and_transforms() -> None:
    engine, session_factory = create_engine_and_sessionmaker()
    await prepare_database(engine)
    await seed_data(session_factory)
    schema = build_schema()

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
        context_value=AppContext(session_factory),
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
