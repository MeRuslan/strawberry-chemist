import logging
from functools import partial

import pytest
import strawberry

import strawberry_chemist as sc
from strawberry_chemist.gql_context import SQLAlchemyContext
from strawberry_chemist.query_cost import QUERY_COST_EXCEEDED, QueryCostExceeded
from tests.test_query_cost.schema import Author, Base, Book, Query

costs: list[sc.QueryCost] = []

limited = strawberry.Schema(
    query=Query,
    extensions=[
        *sc.extensions(),
        partial(sc.QueryCostLimiter, max_objects=50, max_fields=1000),
    ],
)
dry_run = strawberry.Schema(
    query=Query,
    extensions=[
        *sc.extensions(),
        partial(
            sc.QueryCostLimiter,
            max_objects=50,
            dry_run=True,
            callback=lambda cost, _: costs.append(cost),
        ),
    ],
)

CHEAP = "{ authors(pagination: {first: 2}) { edges { node { name } } } }"
EXPENSIVE = """{ authors(pagination: {first: 20}) { edges { node {
    books(pagination: {first: 10}) { edges { node { title } } }
} } } }"""


@pytest.fixture
async def library(mock_sqlite_sqla_session):
    async with mock_sqlite_sqla_session as session:
        async with session.begin():
            await (await session.connection()).run_sync(Base.metadata.create_all)
    async with mock_sqlite_sqla_session as session:
        tolkien = Author(name="Tolkien")
        session.add_all(
            [tolkien, Author(name="Martin"), Book(title="The Hobbit", author=tolkien)]
        )
        await session.commit()


async def test_cheap_operation_runs(library):
    result = await limited.execute(CHEAP, context_value=SQLAlchemyContext(None))

    assert result.errors is None
    assert [e["node"]["name"] for e in result.data["authors"]["edges"]] == [
        "Tolkien",
        "Martin",
    ]


async def test_expensive_operation_is_rejected_before_it_runs():
    # no database here: the operation must not get as far as resolving
    result = await limited.execute(EXPENSIVE, context_value=SQLAlchemyContext(None))

    assert result.data is None
    [error] = result.errors
    assert isinstance(error.original_error, QueryCostExceeded)
    assert error.message.startswith("Query is too expensive: up to 461 objects")
    assert error.extensions == {
        "code": QUERY_COST_EXCEEDED,
        "objects": 461,
        "fields": 462,
        "maxObjects": 50,
        "maxFields": 1000,
    }


async def test_variables_decide_the_cost(library):
    query = "query($p: CursorPaginationInput) { authors(pagination: $p) { edges { node { books { edges { node { title } } } } } } }"

    rejected = await limited.execute(
        query,
        variable_values={"p": {"first": 20}},
        context_value=SQLAlchemyContext(None),
    )
    allowed = await limited.execute(
        query,
        variable_values={"p": {"first": 1}},
        context_value=SQLAlchemyContext(None),
    )

    assert rejected.errors[0].extensions["code"] == QUERY_COST_EXCEEDED
    assert allowed.errors is None
    assert len(allowed.data["authors"]["edges"]) == 1


async def test_dry_run_logs_and_runs(library, caplog):
    costs.clear()
    with caplog.at_level(logging.WARNING, logger="strawberry_chemist.query_cost"):
        result = await dry_run.execute(EXPENSIVE, context_value=SQLAlchemyContext(None))

    assert result.errors is None
    assert result.data["authors"]["edges"][0]["node"]["books"]["edges"] == [
        {"node": {"title": "The Hobbit"}}
    ]
    assert costs == [sc.QueryCost(objects=461, fields=462)]
    assert "Query is too expensive: up to 461 objects (limit 50)" in caplog.text
