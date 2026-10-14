import time

import pytest

import strawberry_chemist as sc
from strawberry_chemist.pagination import CursorPaginationInput
from tests.test_query_cost.schema import schema


def estimate(query, variables=None, **kwargs):
    return sc.estimate_query_cost(schema, query, variables=variables, **kwargs)


def test_connection_page_defaults_to_the_policy_default_limit():
    cost = estimate("{ authors { edges { node { name } } } }", {})

    # the connection, then 5 edges with a node each
    assert cost == sc.QueryCost(objects=1 + 5 * 2, fields=12)


def test_nested_pages_multiply_and_are_capped_by_max_limit():
    cost = estimate(
        """{ authors(pagination: {first: 15}) { edges { node {
            name
            books(pagination: {first: 100}) { edges { node { title } } }
        } } } }""",
        {},
    )

    books = 1 + 10 * 2
    assert cost.objects == 1 + 15 * (2 + books)


def test_nested_cursor_input_is_capped_at_its_absolute_limit():
    policy = sc.CursorPagination(max_limit=100, nested=True)

    assert policy.page_size({"pagination": {"first": 1000}}) == 40
    assert policy.page_size({"pagination": {}}) == CursorPaginationInput.first
    assert policy.page_size({"pagination": None}) == 5
    assert policy.page_size({}) == 5


def test_flat_and_offset_policies_size_pages_like_they_paginate():
    flat = sc.CursorPagination(max_limit=10)
    offset = sc.OffsetPagination(default_limit=2, max_limit=20, nested=True)

    assert flat.page_size({}) == 5
    assert flat.page_size({"first": 0}) == 1
    assert flat.page_size({"first": 7}) == 7
    assert offset.page_size({}) == 2
    assert offset.page_size({"pagination": {"limit": 50}}) == 20
    # the input's own default (-1) pages one row, as paginate_query does
    assert offset.page_size({"pagination": {"offset": 3}}) == 1


def test_variables_size_pages_and_missing_ones_count_as_absent():
    query = """query($p: CursorPaginationInput, $first: Int!) { authors(pagination: $p) {
        edges { node { flatBooks(first: $first) { edges { node { title } } } } }
    } }"""

    small = estimate(query, {"p": {"first": 2}, "first": 3})
    default = estimate(query, {"first": 3})

    assert small.objects == 1 + 2 * (2 + 1 + 3 * 2)
    assert default.objects == 1 + 5 * (2 + 1 + 3 * 2)


def test_operation_variable_defaults_apply():
    query = """query($first: Int = 3) { authors { edges { node {
        flatBooks(first: $first) { edges { node { title } } }
    } } } }"""

    assert estimate(query, {}).objects == 1 + 5 * (2 + 1 + 3 * 2)
    assert estimate(query, {"first": 8}).objects == 1 + 5 * (2 + 1 + 8 * 2)


def test_without_variables_every_variable_is_at_its_worst():
    query = """query($p: CursorPaginationInput, $first: Int!) { authors(pagination: $p) {
        edges { node { flatBooks(first: $first) { edges { node { title } } } } }
    } }"""

    assert estimate(query).objects == 1 + 20 * (2 + 1 + 10 * 2)


def test_skip_and_include_follow_their_condition():
    query = """query($with: Boolean!) { authors { edges { node {
        books @include(if: $with) { edges { node { title } } }
        name @skip(if: true)
    } } } }"""

    without = estimate(query, {"with": False})
    with_books = estimate(query, {"with": True})

    assert without == sc.QueryCost(objects=1 + 5 * 2, fields=1 + 1 + 5 * 1)
    assert with_books.objects == 1 + 5 * (2 + 1 + 5 * 2)
    assert estimate(query) == with_books


def test_same_response_key_is_resolved_once_and_aliases_add_up():
    one = estimate("{ authors { edges { node { name } } } }", {})
    merged = estimate(
        """{ authors { edges { node { name } } }
             authors { edges { node { name ...N } } } }
           fragment N on AuthorNode { name }""",
        {},
    )
    aliased = estimate(
        "{ a: authors { edges { node { name } } } b: authors { edges { node { name } } } }",
        {},
    )

    assert merged == one
    assert aliased == sc.QueryCost(objects=2 * one.objects, fields=2 * one.fields)


def test_hints_size_plain_lists_and_resolver_connections():
    cost = estimate(
        """{
            featured { edges { node { title } } }
            recent(limit: 10) { title }
            authors(pagination: {first: 1}) { edges { node { tags { name } labels { name } } } }
        }""",
        {},
    )

    featured = 1 + 5 * 2
    recent = 4
    authors = 1 + 1 * (2 + 3 + 1)
    assert cost.objects == featured + recent + authors


def test_default_list_size_applies_to_lists_without_hints():
    query = "{ authors(pagination: {first: 1}) { edges { node { labels { name } } } } }"

    assert estimate(query, {}).objects == 1 + 2 + 1
    assert estimate(query, {}, default_list_size=10).objects == 1 + 2 + 10


def test_union_costs_as_its_most_expensive_member():
    cost = estimate(
        """{ search {
            ... on AuthorNode { name tags { name } }
            ... on BookNode { title }
        } }""",
        {},
    )

    assert cost == sc.QueryCost(objects=2 * (1 + 3), fields=1 + 2 * (1 + 1 + 3))


def test_typename_and_introspection_fields_are_free():
    assert estimate("{ __typename authors { __typename } }", {}) == sc.QueryCost(
        objects=1, fields=1
    )


def test_operation_is_picked_by_name():
    document = """
        query Small { authors(pagination: {first: 1}) { edges { node { name } } } }
        query Big { authors(pagination: {first: 20}) { edges { node { name } } } }
    """

    assert estimate(document, {}, operation_name="Small").objects == 3
    assert estimate(document, {}, operation_name="Big").objects == 41
    with pytest.raises(ValueError):
        estimate(document, {})


def test_fragment_chains_are_estimated_without_blowing_up():
    depth = 40
    fragments = "\n".join(
        f"fragment F{i} on AuthorNode {{ a: books {{ edges {{ node {{ author {{ ...F{i + 1} }} }} }} }} "
        f"b: books {{ edges {{ node {{ author {{ ...F{i + 1} }} }} }} }} }}"
        for i in range(depth)
    )
    query = (
        "{ authors { edges { node { ...F0 } } } }\n"
        f"{fragments}\nfragment F{depth} on AuthorNode {{ name }}"
    )

    started = time.monotonic()
    cost = estimate(query, {})

    assert time.monotonic() - started < 1
    assert cost.objects > 10**40


def test_cost_hint_takes_exactly_one_of_its_arguments():
    with pytest.raises(ValueError):
        sc.cost()
    with pytest.raises(ValueError):
        sc.cost(list_size=1, pagination=sc.CursorPagination())
    with pytest.raises(ValueError):
        sc.cost(list_size=-1)
