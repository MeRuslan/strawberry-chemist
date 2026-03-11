import pytest
from sqlalchemy import select
from sqlalchemy.orm import joinedload
from sqlalchemy.orm.exc import DetachedInstanceError
from strawberry.utils.logging import StrawberryLogger

from tests.test_end_to_end.test_related.schema import Base, Book, Person, current_year

hobbit: Book
lotr: Book
silmarillion: Book
hurin: Book
ice_fire: Book
harry_potter: Book

tolkien: Person
grr_martin: Person
yemets: Person


@pytest.fixture
async def relay_with_authors_books(mock_sqlite_sqla_session):
    # set global variables, have to do this because of sqlalchemy session invalidation after creating objects
    global \
        hobbit, \
        lotr, \
        silmarillion, \
        hurin, \
        ice_fire, \
        tolkien, \
        grr_martin, \
        yemets, \
        harry_potter

    tolkien = Person(name="J.R.R. Tolkien")
    grr_martin = Person(name="George R.R. Martin")
    yemets = Person(name="Dmitriy Yemets")

    hobbit = Book(title="The Hobbit", author=tolkien, year=1937, isbn="978-0547928227")
    lotr = Book(
        title="The Lord of the Rings", author=tolkien, year=1954, isbn="978-0261102385"
    )
    silmarillion = Book(
        title="The Silmarillion", author=tolkien, year=1977, isbn="978-0007523221"
    )
    hurin = Book(
        title="Children of Hurin", author=tolkien, year=2007, isbn="978-0007246229"
    )
    ice_fire = Book(
        title="Song of Ice and Fire",
        author=grr_martin,
        year=1996,
        isbn="978-0345535528",
    )
    harry_potter = Book(
        title="Harry Potter", author=None, year=1997, isbn="978-0439708180"
    )

    async with mock_sqlite_sqla_session as session:
        async with session.begin():
            await (await session.connection()).run_sync(Base.metadata.create_all)

    # add a couple of books to the database
    async with mock_sqlite_sqla_session as session:
        session.add_all([tolkien, grr_martin, yemets])
        session.add_all([hobbit, lotr, silmarillion, hurin, ice_fire, harry_potter])
        await session.commit()
        await session.execute(select(Book).options(joinedload(Book.author)))
        await session.execute(select(Person).options(joinedload(Person.books)))


@pytest.mark.asyncio
async def test_load_related(relay_with_authors_books, test_relay_client):
    tolkien_name = tolkien.name
    tolkien_books = tolkien.books

    query = '{ personByName(name: "%s") { name books { title } } }' % tolkien_name
    result = test_relay_client.post("/", json={"query": query}).json()

    assert "errors" not in result
    # check author name
    assert tolkien_name == result["data"]["personByName"]["name"]
    # check books
    assert len(result["data"]["personByName"]["books"]) == len(tolkien_books)
    assert hurin.title in [
        book["title"] for book in result["data"]["personByName"]["books"]
    ]


@pytest.mark.asyncio
async def test_load_related_level2(relay_with_authors_books, test_relay_client):
    grr_martin_name = grr_martin.name

    query = (
        '{ personByName(name: "%s") { name books { title author {name} } } }'
        % grr_martin_name
    )
    result = test_relay_client.post("/", json={"query": query}).json()

    assert "errors" not in result
    # check author name
    assert grr_martin_name == result["data"]["personByName"]["name"]
    assert (
        grr_martin_name == result["data"]["personByName"]["books"][0]["author"]["name"]
    )


@pytest.mark.asyncio
async def test_related_with_compound_filter(
    relay_with_authors_books, test_relay_client
):
    author_name = tolkien.name
    query = (
        '{ personByName(name: "%s") { name booksBefore1960 { title year } } }'
        % author_name
    )
    result = test_relay_client.post("/", json={"query": query}).json()

    assert "errors" not in result
    # check author name
    assert author_name == result["data"]["personByName"]["name"]
    # check books
    assert len(result["data"]["personByName"]["booksBefore1960"]) == 2
    assert all(
        book["year"] < 1960
        for book in result["data"]["personByName"]["booksBefore1960"]
    )


@pytest.mark.asyncio
async def test_related_with_filter(relay_with_authors_books, test_relay_client):
    author_name = tolkien.name
    query = (
        '{ personByName(name: "%s") { name booksAfter1960StartingWithThe { title year } } }'
        % author_name
    )
    result = test_relay_client.post("/", json={"query": query}).json()

    assert "errors" not in result
    # check author name
    assert author_name == result["data"]["personByName"]["name"]
    # check books
    assert len(result["data"]["personByName"]["booksAfter1960StartingWithThe"]) == 1
    assert all(
        book["year"] > 1960
        for book in result["data"]["personByName"]["booksAfter1960StartingWithThe"]
    )
    assert all(
        book["title"].startswith("The")
        for book in result["data"]["personByName"]["booksAfter1960StartingWithThe"]
    )


@pytest.mark.asyncio
async def test_related_load_nonsql_data_dependant_field(
    relay_with_authors_books, test_relay_client
):
    author_name = tolkien.name
    query = (
        '{ personByName(name: "%s") { name books {'
        " title yearsSincePublished } } }" % author_name
    )
    result = test_relay_client.post("/", json={"query": query}).json()

    assert "errors" not in result
    # check author name
    assert author_name == result["data"]["personByName"]["name"]
    book_the_hobbit_from_result = next(
        book
        for book in result["data"]["personByName"]["books"]
        if book["title"] == hobbit.title
    )
    assert (
        book_the_hobbit_from_result["yearsSincePublished"] == current_year - hobbit.year
    )


@pytest.mark.asyncio
async def test_related_load_does_not_load_whole_model_by_default(
    relay_with_authors_books, test_relay_client, monkeypatch
):
    author_name = grr_martin.name
    query = (
        '{ personByName(name: "%s") { name books {'
        " title faultyTitleWithIsbn } } }" % author_name
    )
    with monkeypatch.context() as m:
        # don't log errors, we expect them
        m.setattr(StrawberryLogger, "error", lambda *args, **kwargs: None)
        with pytest.raises(DetachedInstanceError):
            test_relay_client.post("/", json={"query": query}).json()


@pytest.mark.asyncio
async def test_author_with_no_books(relay_with_authors_books, test_relay_client):
    author_name = yemets.name
    query = '{ personByName(name: "%s") { name books { title} } }' % author_name
    result = test_relay_client.post("/", json={"query": query}).json()
    assert "errors" not in result
    assert 0 == len(result["data"]["personByName"]["books"])


@pytest.mark.asyncio
async def test_no_author(relay_with_authors_books, test_relay_client):
    author_name = "No Author"
    query = '{ personByName(name: "%s") { name books { title} } }' % author_name
    result = test_relay_client.post("/", json={"query": query}).json()
    assert "errors" not in result
    assert result["data"]["personByName"] is None


@pytest.mark.asyncio
async def test_field_with_resolver_class_method(
    relay_with_authors_books, test_relay_client
):
    author_name = grr_martin.name
    book_title = ice_fire.title

    query = '{ personByName(name: "%s") { name books { titleTwice } } }' % author_name
    result = test_relay_client.post("/", json={"query": query}).json()
    assert "errors" not in result
    assert book_title * 2 in [
        book["titleTwice"] for book in result["data"]["personByName"]["books"]
    ]


@pytest.mark.asyncio
async def test_field_with_resolver_func(relay_with_authors_books, test_relay_client):
    author_name = grr_martin.name
    book_title = ice_fire.title

    query = '{ personByName(name: "%s") { name books { titleThrice } } }' % author_name
    result = test_relay_client.post("/", json={"query": query}).json()
    assert "errors" not in result
    assert book_title * 3 in [
        book["titleThrice"] for book in result["data"]["personByName"]["books"]
    ]


@pytest.mark.asyncio
async def test_relation_with_needs_fields(relay_with_authors_books, test_relay_client):
    author_name = tolkien.name
    years = [book.year for book in tolkien.books]

    query = '{ personByName(name: "%s") { name bookYears } }' % author_name
    result = test_relay_client.post("/", json={"query": query}).json()
    assert "errors" not in result
    assert set(years) == set(result["data"]["personByName"]["bookYears"])


@pytest.mark.asyncio
async def test_relation_with_ignore_field_selections_positive(
    relay_with_authors_books, test_relay_client
):
    author_name = tolkien.name
    years = [f"{book.year:b}" for book in tolkien.books]

    query = (
        '{ personByName(name: "%s") { name bookBinaryYears { binaryYear } } }'
        % author_name
    )
    result = test_relay_client.post("/", json={"query": query}).json()
    assert "errors" not in result
    res_binary_years = [
        res["binaryYear"] for res in result["data"]["personByName"]["bookBinaryYears"]
    ]
    assert set(years) == set(res_binary_years)
