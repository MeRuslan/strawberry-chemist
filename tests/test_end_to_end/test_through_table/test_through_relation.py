import pytest
from sqlalchemy import select
from sqlalchemy.orm import joinedload

from tests.test_end_to_end.test_through_table.schema import Author, Book, Base


(
    hobbit,
    lotr,
    silmarillion,
    hurin,
    ice_fire,
    tolkien,
    tolkien_jr,
    grr_martin,
    yemets,
    harry_potter,
) = (None, None, None, None, None, None, None, None, None, None)


@pytest.fixture(scope="function")
async def authors_books(mock_sqlite_sqla_session):
    # set global variables, have to do this because of sqlalchemy session invalidation after creating objects
    global \
        hobbit, \
        lotr, \
        silmarillion, \
        hurin, \
        ice_fire, \
        tolkien, \
        tolkien_jr, \
        grr_martin, \
        yemets, \
        harry_potter
    tolkien = Author(name="J.R.R. Tolkien")
    tolkien_jr = Author(name="Christopher Tolkien")

    grr_martin = Author(name="George R.R. Martin")
    yemets = Author(name="Dmitriy Yemets")

    hobbit = Book(title="The Hobbit", authors=[tolkien])
    lotr = Book(title="The Lord of the Rings", authors=[tolkien])

    silmarillion = Book(title="The Silmarillion", authors=[tolkien, tolkien_jr])
    hurin = Book(title="Children of Hurin", authors=[tolkien, tolkien_jr])

    ice_fire = Book(title="Song of Ice and Fire", authors=[grr_martin])
    harry_potter = Book(title="Harry Potter", authors=[])

    async with mock_sqlite_sqla_session as session:  # noqa
        async with session.begin():
            await (await session.connection()).run_sync(Base.metadata.create_all)

    # add a couple of books to the database
    async with mock_sqlite_sqla_session as session:
        session.add_all([tolkien, grr_martin, yemets])
        session.add_all([hobbit, lotr, silmarillion, hurin, ice_fire, harry_potter])
        await session.commit()
        await session.execute(select(Book).options(joinedload(Book.authors)))
        await session.execute(select(Author).options(joinedload(Author.books)))


@pytest.mark.asyncio
async def test_load_related(authors_books, test_through_client):
    query = '{ personByName(name: "%s") { name books { title } } }' % tolkien.name
    result = test_through_client.post("/", json={"query": query}).json()

    assert "errors" not in result
    # check author name
    assert tolkien.name == result["data"]["personByName"]["name"]
    # check books
    assert set(book.title for book in tolkien.books) == set(
        book["title"] for book in result["data"]["personByName"]["books"]
    )


@pytest.mark.asyncio
async def test_load_related_through_junior(authors_books, test_through_client):
    query = '{ personByName(name: "%s") { name books { title } } }' % tolkien_jr.name
    result = test_through_client.post("/", json={"query": query}).json()

    assert "errors" not in result
    # check books
    assert set(book.title for book in tolkien_jr.books) == set(
        book["title"] for book in result["data"]["personByName"]["books"]
    )


@pytest.mark.asyncio
async def test_load_related_reverse(authors_books, test_through_client):
    query = (
        '{ bookByTitle(title: "%s") { title authors { name } } }' % silmarillion.title
    )
    result = test_through_client.post("/", json={"query": query}).json()

    assert "errors" not in result
    # check author name
    assert silmarillion.title == result["data"]["bookByTitle"]["title"]
    # check authors
    assert set(author.name for author in [tolkien_jr, tolkien]) == set(
        author["name"] for author in result["data"]["bookByTitle"]["authors"]
    )


@pytest.mark.asyncio
async def test_load_related_through_three_levels(authors_books, test_through_client):
    query = (
        '{ personByName(name: "%s") { name books { title authors { name  books { title } } } } }'
        % tolkien.name
    )
    result = test_through_client.post("/", json={"query": query}).json()

    assert "errors" not in result
    assert tolkien.name == result["data"]["personByName"]["name"]
    assert len(result["data"]["personByName"]["books"]) == len(tolkien.books)
    for book in result["data"]["personByName"]["books"]:
        orm_book = next(b for b in tolkien.books if b.title == book["title"])
        # check authors of the book
        assert set(author["name"] for author in book["authors"]) == set(
            a.name for a in orm_book.authors
        )


@pytest.mark.asyncio
async def test_load_nested_connection_with_through(authors_books, test_through_client):
    query = (
        '{ personByName(name: "%s") {'
        " name booksConnection(first: 10) {"
        " edges { node { title authors { name  } } } } } }" % tolkien.name
    )
    result = test_through_client.post("/", json={"query": query}).json()

    assert "errors" not in result
    assert tolkien.name == result["data"]["personByName"]["name"]
    for book_edge in result["data"]["personByName"]["booksConnection"]["edges"]:
        book = book_edge["node"]
        orm_book = next(b for b in tolkien.books if b.title == book["title"])
        # check authors of the book
        assert set(author["name"] for author in book["authors"]) == set(
            a.name for a in orm_book.authors
        )
