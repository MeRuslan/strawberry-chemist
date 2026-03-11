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
async def test_scalar_aliases_and_computed_fields_are_exposed() -> None:
    engine, session_factory = create_engine_and_sessionmaker()
    await prepare_database(engine)
    await seed_data(session_factory)
    schema = build_schema()

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
        context_value=AppContext(session_factory),
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
