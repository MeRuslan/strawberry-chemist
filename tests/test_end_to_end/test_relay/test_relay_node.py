import asyncio
from typing import List

import pytest
import strawberry
from sqlalchemy import Integer, select
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from strawberry.utils.logging import StrawberryLogger

import strawberry_chemist as sc
from strawberry_chemist.relay.public import (
    compose_node_id,
    configure,
    decode_node_id,
    encode_node_id,
    get_node_definition,
)
from tests.test_end_to_end.test_relay.schema import BookType, Base, Book


def test_simple_query(test_relay_client):
    response = test_relay_client.post("/", json={"query": "{ hello }"})
    assert response.json() == {"data": {"hello": "Hello, world!"}}


@pytest.fixture
async def relay_with_books(mock_sqlite_sqla_session):
    async with mock_sqlite_sqla_session as session:
        await (await session.connection()).run_sync(Base.metadata.create_all)

    async with mock_sqlite_sqla_session as session:
        session.add_all(
            [
                Book(title="The Hobbit"),
                Book(title="The Lord of the Rings"),
            ]
        )
        await session.commit()
        books = (
            (await session.execute(select(Book).order_by(Book.id.asc())))
            .scalars()
            .all()
        )

    return books


def test_node_field_is_explicit_new_public_api():
    class Base(DeclarativeBase):
        pass

    class Dummy(Base):
        __tablename__ = "dummy"
        id: Mapped[int] = mapped_column(Integer, primary_key=True)

    @sc.node(model=Dummy)
    class ExplicitDummyNode:
        pass

    @strawberry.type
    class Query:
        node = sc.node_field(allowed_types=(ExplicitDummyNode,))

    schema = strawberry.Schema(query=Query)
    field = schema.schema_converter.type_map["Query"].definition.fields[0]

    assert field.name == "node"
    assert field.arguments[0].python_name == "id"
    assert field.arguments[0].type_annotation.annotation is strawberry.ID


def test_node_types_implement_node_interface_automatically():
    class Base(DeclarativeBase):
        pass

    class Dummy(Base):
        __tablename__ = "dummy_node"
        id: Mapped[int] = mapped_column(Integer, primary_key=True)

    @sc.node(model=Dummy)
    class InterfaceDummyNode:
        pass

    @strawberry.type
    class Query:
        hello: str = "world"

    schema = strawberry.Schema(query=Query)
    configure(schema, node_types=(InterfaceDummyNode,))
    sdl = schema.as_str()

    assert "interface Node" in sdl
    assert "type InterfaceDummyNode implements Node" in sdl
    assert [
        interface.name
        for interface in InterfaceDummyNode.__strawberry_definition__.interfaces
    ] == ["Node"]


def test_unrestricted_node_field_uses_node_interface_and_picks_up_late_nodes():
    class Base(DeclarativeBase):
        pass

    class BookModel(Base):
        __tablename__ = "late_book"
        id: Mapped[int] = mapped_column(Integer, primary_key=True)

    class ShelfModel(Base):
        __tablename__ = "late_shelf"
        slug: Mapped[str] = mapped_column(primary_key=True)

    @sc.node(model=BookModel)
    class LateBookNode:
        pass

    @strawberry.type
    class Query:
        node = sc.node_field()

    @sc.node(model=ShelfModel, ids=("slug",))
    class LateShelfNode:
        pass

    schema = configure(strawberry.Schema(query=Query))
    sdl = schema.as_str()

    assert "node(id: ID!): Node" in sdl
    assert "type LateBookNode implements Node" in sdl
    assert "type LateShelfNode implements Node" in sdl


def test_schema_default_codec_applies_to_ids_and_helper_api():
    class Base(DeclarativeBase):
        pass

    class Dummy(Base):
        __tablename__ = "dummy_codec"
        id: Mapped[int] = mapped_column(Integer, primary_key=True)

        def __init__(self, id: int):
            self.id = id

    codec = sc.relay.IntRegistryCodec(registry={Dummy: 7})

    @sc.node(model=Dummy)
    class CodecDummyNode:
        pass

    node = Dummy(3)

    @strawberry.type
    class Query:
        @strawberry.field
        def dummy(self) -> CodecDummyNode:
            return node

    schema = configure(strawberry.Schema(query=Query), default_codec=codec)

    assert encode_node_id(schema, CodecDummyNode, source=node) == strawberry.ID("7:3")
    assert encode_node_id(schema, CodecDummyNode, values=(3,)) == strawberry.ID("7:3")
    assert decode_node_id(schema, "7:3").node_type is CodecDummyNode

    result = asyncio.run(schema.execute("{ dummy { id } }"))
    assert result.data == {"dummy": {"id": "7:3"}}
    assert result.errors is None


def test_decode_node_id_rejects_allowed_type_mismatch():
    class Base(DeclarativeBase):
        pass

    class BookModel(Base):
        __tablename__ = "decode_book"
        id: Mapped[int] = mapped_column(Integer, primary_key=True)

    class ShelfModel(Base):
        __tablename__ = "decode_shelf"
        slug: Mapped[str] = mapped_column(primary_key=True)

    @sc.node(model=BookModel)
    class DecodeBookNode:
        pass

    @sc.node(model=ShelfModel, ids=("slug",))
    class DecodeShelfNode:
        pass

    @strawberry.type
    class Query:
        node = sc.node_field()

    schema = configure(strawberry.Schema(query=Query))

    with pytest.raises(ValueError, match="Unknown node token"):
        decode_node_id(
            schema,
            "DecodeShelfNode_main",
            allowed_types=(DecodeBookNode,),
        )


@pytest.mark.asyncio
async def test_node_type_uses_registered_definition(test_relay_client):
    schema = test_relay_client.app.schema
    book_type = schema.schema_converter.type_map["BookType"]

    assert book_type.definition.name == "BookType"
    assert book_type.definition.origin == BookType
    definition = get_node_definition(BookType)
    assert definition is not None
    assert definition.model is Book
    assert definition.ids == ("id",)


@pytest.mark.asyncio
async def test_node_default_ids(relay_with_books, test_relay_client):
    books: List[Book] = relay_with_books
    definition = get_node_definition(BookType)
    assert definition is not None

    query = "{ allBooks { id title } }"
    result = test_relay_client.post("/", json={"query": query}).json()

    assert "errors" not in result
    assert "data" in result
    assert set(book["id"] for book in result["data"]["allBooks"]) == {
        compose_node_id(book, definition) for book in books
    }
    assert set(book["title"] for book in result["data"]["allBooks"]) == {
        book.title for book in books
    }


@pytest.mark.asyncio
async def test_node_get_by_id(relay_with_books, test_relay_client):
    books: List[Book] = relay_with_books
    definition = get_node_definition(BookType)
    assert definition is not None
    book_relay_id = compose_node_id(books[1], definition)

    query = (
        f'{{ node(id: "{book_relay_id}") {{ __typename ... on BookType {{ id }} }} }}'
    )
    response = test_relay_client.post("/", json={"query": query})
    result = response.json()

    assert "errors" not in result
    assert "data" in result
    assert book_relay_id == result["data"]["node"]["id"]


@pytest.mark.asyncio
async def test_get_by_id_node_field(relay_with_books, test_relay_client):
    books: List[Book] = relay_with_books
    definition = get_node_definition(BookType)
    assert definition is not None
    book_relay_id = compose_node_id(books[1], definition)
    book_title = books[1].title

    query = f'{{ bookById(id: "{book_relay_id}") {{ __typename ... on BookType {{ id title }} }} }}'
    response = test_relay_client.post("/", json={"query": query})
    result = response.json()

    assert "errors" not in result
    assert book_relay_id == result["data"]["bookById"]["id"]
    assert book_title == result["data"]["bookById"]["title"]


@pytest.mark.asyncio
async def test_get_by_id_node_field_no_permission(
    relay_with_books, test_relay_client, monkeypatch
):
    books: List[Book] = relay_with_books
    definition = get_node_definition(BookType)
    assert definition is not None
    book_relay_id = compose_node_id(books[1], definition)

    query = f'{{ noPermissionBookById(id: "{book_relay_id}") {{ __typename ... on BookType {{ id title }} }} }}'
    with monkeypatch.context() as m:
        m.setattr(StrawberryLogger, "error", lambda *args, **kwargs: None)
        with pytest.raises(PermissionError):
            test_relay_client.post("/", json={"query": query}).json()


@pytest.mark.asyncio
async def test_get_by_id_node_field_not_found(relay_with_books, test_relay_client):
    definition = get_node_definition(BookType)
    assert definition is not None
    book_relay_id = definition.codec.encode(definition.node_name, ("320",))

    query = f'{{ bookById(id: "{book_relay_id}") {{ __typename ... on BookType {{ id title }} }} }}'
    response = test_relay_client.post("/", json={"query": query})
    result = response.json()

    assert "errors" not in result
    assert result["data"]["bookById"] is None
