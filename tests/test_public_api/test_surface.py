import importlib
import inspect

import pytest
import strawberry
from sqlalchemy import Integer, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

import strawberry_chemist as sc


def test_top_level_exports_match_public_surface() -> None:
    assert hasattr(sc, "FilterContext")
    assert hasattr(sc, "OrderContext")
    assert hasattr(sc, "PaginationPolicy")
    assert hasattr(sc, "node_lookup")
    assert hasattr(sc.relay, "configure")
    assert hasattr(sc.relay, "encode_node_id")
    assert hasattr(sc.relay, "decode_node_id")
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
    assert "source_param_name" in relationship_params
    assert "select" in relationship_params
    assert "parent_select" in relationship_params
    assert "load" in relationship_params
    assert "sqlalchemy_name" not in relationship_params
    assert "pre_filter" not in relationship_params
    assert "needs_fields" not in relationship_params
    assert "ignore_field_selections" not in relationship_params

    assert "where" in connection_params
    assert "source_param_name" in connection_params
    assert "select" in connection_params
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


def test_connection_select_extends_child_loading() -> None:
    field = sc.connection(source="books", select=["title", "year"])

    assert field.relationship_select == ("title", "year")


def test_relationship_and_connection_parent_select_extend_parent_loading() -> None:
    class ParentRelationship:
        local_columns = [type("Column", (), {"name": "id"})()]

    relationship_field = sc.relationship("books", parent_select=["name", "id"])
    relationship_field.relationship_property = ParentRelationship()

    connection_field = sc.connection(source="books", parent_select=["address", "id"])
    connection_field.relationship_property = ParentRelationship()

    assert relationship_field.needs_parent_fields == ["id", "name"]
    assert connection_field.needs_parent_fields == ["id", "address"]


def test_field_select_hides_only_selected_resolver_params() -> None:
    @sc.field(select=["title", "year"])
    def catalog_label(
        self,
        title: str,
        year: int,
        suffix: str,
    ):
        return f"{title} ({year}) {suffix}"

    assert [argument.python_name for argument in catalog_label.arguments] == ["suffix"]

    kwargs = catalog_label.inject_resolver_kwargs(
        source=type("Book", (), {"title": "The Hobbit", "year": 1937})(),
        kwargs={"suffix": "!"},
    )

    assert kwargs == {
        "title": "The Hobbit",
        "year": 1937,
        "suffix": "!",
    }


def test_field_select_can_map_source_fields_to_custom_param_names() -> None:
    @sc.field(select={"title": "book_title", "year": "published_year"})
    def catalog_label(
        self,
        book_title: str,
        published_year: int,
        suffix: str,
    ):
        return f"{book_title} ({published_year}) {suffix}"

    assert [argument.python_name for argument in catalog_label.arguments] == ["suffix"]

    kwargs = catalog_label.inject_resolver_kwargs(
        source=type("Book", (), {"title": "The Hobbit", "year": 1937})(),
        kwargs={"suffix": "!"},
    )

    assert kwargs == {
        "book_title": "The Hobbit",
        "published_year": 1937,
        "suffix": "!",
    }


def test_relationship_and_connection_keep_custom_resolver_params_public() -> None:
    class BookModel:
        pass

    @sc.relationship("books", parent_select=["name"])
    def labels(
        self,
        books: list[BookModel],
        separator: str,
    ):  # pragma: no cover - body is not reached
        return [book for book in books if separator]

    assert [argument.python_name for argument in labels.arguments] == ["separator"]

    relationship_kwargs = labels.inject_resolver_kwargs(
        source=type("Author", (), {"name": "Tolkien"})(),
        kwargs={"separator": " / "},
        relationship_value=["The Hobbit"],
    )

    assert relationship_kwargs == {
        "books": ["The Hobbit"],
        "separator": " / ",
    }

    @sc.connection(source="books", parent_select=["name"])
    def paginated_labels(
        self,
        books: sc.Connection[BookModel],
        prefix: str,
    ):  # pragma: no cover - body is not reached
        return books

    assert [argument.python_name for argument in paginated_labels.arguments] == [
        "first",
        "after",
        "prefix",
    ]

    connection = object()
    connection_kwargs = paginated_labels.inject_resolver_kwargs(
        source=type("Author", (), {"name": "Tolkien"})(),
        kwargs={"prefix": "The"},
        relationship_value=connection,
    )

    assert connection_kwargs == {
        "books": connection,
        "prefix": "The",
    }


def test_relationship_and_connection_can_customize_source_param_name() -> None:
    class BookModel:
        pass

    @sc.relationship("books", source_param_name="loaded_books")
    def labels(
        self,
        loaded_books: list[BookModel],
        separator: str,
    ):  # pragma: no cover - body is not reached
        return [book for book in loaded_books if separator]

    assert [argument.python_name for argument in labels.arguments] == ["separator"]
    assert labels.inject_resolver_kwargs(
        source=object(),
        kwargs={"separator": " / "},
        relationship_value=["The Hobbit"],
    ) == {
        "loaded_books": ["The Hobbit"],
        "separator": " / ",
    }

    @sc.connection(source="books", source_param_name="loaded_connection")
    def paginated_labels(
        self,
        loaded_connection: sc.Connection[BookModel],
        prefix: str,
    ):  # pragma: no cover - body is not reached
        return loaded_connection

    assert [argument.python_name for argument in paginated_labels.arguments] == [
        "first",
        "after",
        "prefix",
    ]
    connection = object()
    assert paginated_labels.inject_resolver_kwargs(
        source=object(),
        kwargs={"prefix": "The"},
        relationship_value=connection,
    ) == {
        "loaded_connection": connection,
        "prefix": "The",
    }


def test_relationship_and_connection_require_the_configured_source_param_name() -> None:
    class BookModel:
        pass

    @sc.relationship("books")
    def labels(
        self,
        loaded_books: list[BookModel],
        separator: str,
    ):  # pragma: no cover - body is not reached
        return [book for book in loaded_books if separator]

    with pytest.raises(TypeError, match="must declare a 'books' parameter"):
        _ = labels.arguments

    @sc.connection(source="books")
    def paginated_labels(
        self,
        loaded_connection: sc.Connection[BookModel],
        prefix: str,
    ):  # pragma: no cover - body is not reached
        return loaded_connection

    with pytest.raises(TypeError, match="must declare a 'books' parameter"):
        _ = paginated_labels.arguments


def test_node_lookup_keeps_custom_resolver_params_public() -> None:
    class Base(DeclarativeBase):
        pass

    class BookModel(Base):
        __tablename__ = "books"

        id: Mapped[int] = mapped_column(Integer, primary_key=True)
        title: Mapped[str] = mapped_column(String(200))

    @sc.node(model=BookModel)
    class Book:
        title: str

    @strawberry.type
    class Query:
        @sc.node_lookup(model=BookModel, id_name="book_id", node_param_name="book")
        def book_label(
            self,
            info: strawberry.Info,
            book: BookModel | None,
            prefix: str,
        ) -> str | None:
            del info, book, prefix
            return None

    schema = strawberry.Schema(query=Query, extensions=sc.extensions())
    sdl = schema.as_str()

    assert "bookLabel(bookId: ID!, prefix: String!): String" in sdl
    assert " book:" not in sdl
