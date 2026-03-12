import importlib
import inspect

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


def test_builder_signatures_match_documented_surface() -> None:
    field_params = inspect.signature(sc.field).parameters
    relationship_params = inspect.signature(sc.relationship).parameters
    connection_params = inspect.signature(sc.connection).parameters

    assert "select" in field_params
    assert "sqlalchemy_name" not in field_params
    assert "post_processor" not in field_params
    assert "additional_parent_fields" not in field_params

    assert "where" in relationship_params
    assert "select" in relationship_params
    assert "parent_select" in relationship_params
    assert "load" in relationship_params
    assert "sqlalchemy_name" not in relationship_params
    assert "pre_filter" not in relationship_params
    assert "needs_fields" not in relationship_params
    assert "ignore_field_selections" not in relationship_params

    assert "where" in connection_params
    assert "default_order_by" in connection_params
    assert "parent_select" in connection_params
    assert "sqlalchemy_name" not in connection_params


def test_builders_reject_removed_legacy_kwargs() -> None:
    with pytest.raises(TypeError, match="post_processor"):
        sc.field(post_processor=lambda source, result: result)

    with pytest.raises(TypeError, match="sqlalchemy_name"):
        sc.field(sqlalchemy_name="title")

    with pytest.raises(TypeError, match="pre_filter"):
        sc.relationship("books", pre_filter=())

    with pytest.raises(TypeError, match="sqlalchemy_name"):
        sc.relationship("books", sqlalchemy_name="books")

    with pytest.raises(TypeError, match="sqlalchemy_name"):
        sc.connection(sqlalchemy_name="books")


def test_connection_accepts_where_and_default_order_by() -> None:
    field = sc.connection(
        where=lambda: True,
        default_order_by=("title",),
    )

    assert field.where
    assert field.default_order_by == ("title",)


def test_relationship_and_connection_parent_select_extend_parent_loading() -> None:
    class ParentRelationship:
        local_columns = [type("Column", (), {"name": "id"})()]

    relationship_field = sc.relationship("books", parent_select=["name", "id"])
    relationship_field.relationship_property = ParentRelationship()

    connection_field = sc.connection(source="books", parent_select=["address", "id"])
    connection_field.relationship_property = ParentRelationship()

    assert relationship_field.needs_parent_fields == ["id", "name"]
    assert connection_field.needs_parent_fields == ["id", "address"]


def test_parent_select_does_not_inject_additional_resolver_kwargs() -> None:
    class BookModel:
        pass

    @sc.relationship("books", parent_select=["name"])
    def labels(
        self,
        books: list[BookModel],
        name: str,
    ):  # pragma: no cover - body is not reached
        return [books, name]

    with pytest.raises(TypeError, match="can only inject one relationship argument"):
        labels.inject_resolver_kwargs(
            source=type("Author", (), {"name": "Tolkien"})(),
            kwargs={},
            relationship_value=[],
        )

    @sc.connection(source="books", parent_select=["name"])
    def paginated_labels(
        self,
        books: sc.Connection[BookModel],
        name: str,
    ):  # pragma: no cover - body is not reached
        return [books, name]

    with pytest.raises(TypeError, match="can only inject one relationship argument"):
        paginated_labels.inject_resolver_kwargs(
            source=type("Author", (), {"name": "Tolkien"})(),
            kwargs={},
            relationship_value=[],
        )
