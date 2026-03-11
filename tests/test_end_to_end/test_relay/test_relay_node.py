from typing import List

import pytest
import strawberry
from bidict import bidict
from sqlalchemy import select, Column, Integer
from strawberry.annotation import StrawberryAnnotation
from strawberry.utils.logging import StrawberryLogger

import strawberry_sqlalchemy
from strawberry_sqlalchemy import relay
from strawberry_sqlalchemy.relay import NodeEdge, Node
from strawberry_sqlalchemy.relay.base import (
    compose_id_using_instance,
    node_type_to_int_bijection,
    compose_id_using_class, convert_and_check_exists_node_id,
)
from tests.test_end_to_end.test_relay.schema import BookType, Base, Book
from strawberry_sqlalchemy.utils import unwrap_type


def test_simple_query(test_relay_client):
    response = test_relay_client.post("/", json={"query": "{ hello }"})
    assert response.json() == {"data": {"hello": "Hello, world!"}}


@pytest.fixture
def relay_mock_node_inheritance(monkeypatch):
    node_type_to_int_bijection.cache_clear()
    relay.base.sqla_model_registry = None
    monkeypatch.setattr(Node, '__subclasses__', lambda: [BookType])


@pytest.fixture
async def relay_with_books(mock_sqlite_sqla_session, relay_mock_node_inheritance):
    # create tables
    async with mock_sqlite_sqla_session as session:
        await (await session.connection()).run_sync(Base.metadata.create_all)

    # add a couple of books to the database
    async with mock_sqlite_sqla_session as session:
        session.add_all([
            Book(title="The Hobbit"),
            Book(title="The Lord of the Rings"),
        ])
        await session.commit()
        books = (await session.execute(select(Book))).scalars().all()

    return books


@pytest.mark.asyncio
async def test_node_edge_pure_type_inheritance():
    @strawberry.type
    class Query(NodeEdge):
        ...

    schema = strawberry.Schema(query=Query)
    # chesk that the schema has node edge
    assert schema.schema_converter.type_map['Query'].definition.name == 'Query'
    assert schema.schema_converter.type_map['Query'].definition.origin == Query
    # check that query has node field
    node = schema.schema_converter.type_map['Query'].definition.fields[0]
    assert node.name == 'node'
    assert node.arguments[0].graphql_name == 'id'
    assert node.arguments[0].type_annotation == StrawberryAnnotation(strawberry.ID)
    assert unwrap_type(node.type) == Node


@pytest.mark.asyncio
async def test_node_sqla_model_inheritance(test_relay_client):
    schema = test_relay_client.app.schema
    book_type = schema.schema_converter.type_map['BookType']
    assert book_type.definition.name == 'BookType'
    assert book_type.definition.origin == BookType
    # check that book type implements Node interface
    assert book_type.definition.interfaces[0].name == 'Node'
    assert book_type.definition.interfaces[0].origin == Node


@pytest.mark.asyncio
async def test_node_default_ids(relay_with_books, test_relay_client):
    books: List = relay_with_books
    query = "{ allBooks { id title } }"
    result = test_relay_client.post("/", json={"query": query}).json()

    assert 'errors' not in result
    assert 'data' in result
    # check ids
    assert (
            set(book['id'] for book in result['data']["allBooks"]) ==
            set(compose_id_using_instance(book, book.id) for book in books)
    )
    # check titles
    assert (
            set(book['title'] for book in result['data']["allBooks"]) ==
            set(book.title for book in books)
    )


@pytest.mark.asyncio
async def test_node_custom_model_mapping_for_id_generation(relay_with_books, test_relay_client):
    books: List = relay_with_books
    # get ids before types are mapped
    ids_using_default = set(compose_id_using_instance(book, book.id) for book in books)
    # purge the cache and clear the mapping
    node_type_to_int_bijection.cache_clear()
    relay.base.sqla_model_registry = bidict({1: Book})

    query = "{ allBooks { id title } }"
    response = test_relay_client.post("/", json={"query": query})
    result = response.json()

    assert 'errors' not in result
    assert 'data' in result
    # check ids do not match the default ones
    assert ids_using_default != set(book['id'] for book in result['data']["allBooks"])


@pytest.mark.asyncio
async def test_node_get_by_id(relay_with_books, test_relay_client):
    books: List = relay_with_books
    book_relay_id = compose_id_using_instance(books[1], books[1].id)

    query = f"{{ node(id: \"{book_relay_id}\") {{ __typename id }} }}"
    response = test_relay_client.post("/", json={"query": query})
    result = response.json()

    assert 'errors' not in result
    assert 'data' in result
    assert book_relay_id == result['data']["node"]["id"]


@pytest.mark.asyncio
async def test_get_by_id_object_field(relay_with_books, test_relay_client):
    books: List = relay_with_books
    book_relay_id = compose_id_using_instance(books[1], books[1].id)
    book_title = books[1].title

    query = f"{{ bookById(id: \"{book_relay_id}\") {{ __typename id title }} }}"
    response = test_relay_client.post("/", json={"query": query})
    result = response.json()

    assert 'errors' not in result
    assert book_relay_id == result['data']["bookById"]["id"]
    assert book_title == result['data']["bookById"]["title"]


@pytest.mark.asyncio
async def test_get_by_id_object_field_no_permission(relay_with_books, test_relay_client, monkeypatch):
    books: List = relay_with_books
    book_relay_id = compose_id_using_instance(books[1], books[1].id)

    query = f"{{ noPermissionBookById(id: \"{book_relay_id}\") {{ __typename id title }} }}"
    with monkeypatch.context() as m:
        # don't log errors, we expect them
        m.setattr(StrawberryLogger, "error", lambda *args, **kwargs: None)
        with pytest.raises(PermissionError):
            test_relay_client.post("/", json={"query": query}).json()
            test_relay_client.post("/", json={"query": query})


@pytest.mark.asyncio
async def test_get_by_id_object_field_not_found(relay_with_books, test_relay_client):
    book_relay_id = compose_id_using_class(Book, 320)

    query = f"{{ bookById(id: \"{book_relay_id}\") {{ __typename id title }} }}"
    response = test_relay_client.post("/", json={"query": query})
    result = response.json()

    assert 'errors' not in result
    assert result['data']["bookById"] is None


def test_relay_include_int_identity_model(monkeypatch):
    class ModelWithIntIdentity(Base):
        __tablename__ = 'int_identity'
        __int_identity__ = 1
        id = Column(Integer, primary_key=True)

    @strawberry_sqlalchemy.type(model=ModelWithIntIdentity)
    class ModelWithIntIdentityType(Node):
        ...

    node_type_to_int_bijection.cache_clear()
    relay.base.sqla_model_registry = None
    monkeypatch.setattr(Node, '__subclasses__', lambda: [ModelWithIntIdentityType])
    real_bijection = node_type_to_int_bijection()
    assert real_bijection[ModelWithIntIdentity.__int_identity__] == ModelWithIntIdentity


@pytest.mark.asyncio
async def test_get_exists_by_relay_id(mock_sqlite_sqla_session, relay_with_books, test_relay_client):
    books: List = relay_with_books
    book_relay_id = compose_id_using_instance(books[1], books[1].id)
    not_book_relay_id = compose_id_using_class(Book, -1)
    exists = await convert_and_check_exists_node_id(
        id_=book_relay_id, model=Book, session=mock_sqlite_sqla_session)
    not_exists = await convert_and_check_exists_node_id(
        id_=not_book_relay_id, model=Book, session=mock_sqlite_sqla_session)
    assert exists
    assert not not_exists
