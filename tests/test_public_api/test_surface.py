import importlib

import pytest
import strawberry

import strawberry_chemist as sc


def test_top_level_exports_match_public_surface() -> None:
    assert hasattr(sc, "FilterContext")
    assert hasattr(sc, "OrderContext")
    assert hasattr(sc, "PaginationPolicy")
    assert hasattr(sc, "node_lookup")
    assert not hasattr(sc, "relation_field")
    assert not hasattr(sc, "relay_connection_field")
    assert not hasattr(sc, "limit_offset_connection_field")
    assert not hasattr(sc.relay, "NodeEdge")
    assert not hasattr(sc.relay, "object_field")
    assert not hasattr(sc.relay, "object_exists_field")


def test_typo_extensions_module_is_removed() -> None:
    with pytest.raises(ModuleNotFoundError):
        importlib.import_module("strawberry_chemist.extentions")

    with pytest.raises(ModuleNotFoundError):
        importlib.import_module("strawberry_chemist.ordering")


def test_old_pagination_internals_are_not_part_of_public_module() -> None:
    pagination_module = importlib.import_module("strawberry_chemist.pagination")

    assert not hasattr(pagination_module, "StrawberrySQLAlchemyPaginationBase")
    assert not hasattr(pagination_module, "StrawberrySQLAlchemyCursorPagination")
    assert not hasattr(pagination_module, "StrawberrySQLAlchemyLimitOffsetPagination")


def test_order_field_name_controls_graphql_enum_name() -> None:
    class BookModel:
        pass

    @sc.type(model=BookModel)
    class Book:
        title: str

    @sc.order(model=BookModel)
    class BookOrder:
        published = sc.order_field(name="publishedYear")

    @strawberry.type
    class Query:
        books: sc.Connection[Book] = sc.connection(order=BookOrder)

    schema = strawberry.Schema(query=Query, extensions=sc.extensions())
    sdl = schema.as_str()

    assert "enum BookOrderField" in sdl
    assert "PUBLISHED_YEAR" in sdl
    assert "PUBLISHED\n" not in sdl


def test_cursor_pagination_can_expose_nested_argument_shape() -> None:
    class BookModel:
        pass

    @sc.type(model=BookModel)
    class Book:
        title: str

    @strawberry.type
    class Query:
        books: sc.Connection[Book] = sc.connection(
            pagination=sc.CursorPagination(nested=True)
        )

    schema = strawberry.Schema(query=Query, extensions=sc.extensions())
    sdl = schema.as_str()

    assert "books(pagination: CursorPaginationInput)" in sdl
    assert "books(first:" not in sdl
