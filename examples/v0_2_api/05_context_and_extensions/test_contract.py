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
async def test_manual_root_resolvers_and_chemist_fields_share_the_same_context_contract() -> (
    None
):
    engine, session_factory = create_engine_and_sessionmaker()
    await prepare_database(engine)
    await seed_data(session_factory)
    schema = build_schema()

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
        context_value=AppContext(session_factory, request_id="req-001"),
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
