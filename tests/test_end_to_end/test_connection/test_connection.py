import pytest
from sqlalchemy import select
from sqlalchemy.orm import joinedload
from sqlalchemy.orm.exc import DetachedInstanceError
from strawberry.utils.logging import StrawberryLogger

from tests.test_end_to_end.test_connection.schema import Person, Book, Base

hobbit: Book
lotr: Book
silmarillion: Book
hurin: Book
ice_fire: Book
harry_potter: Book

tolkien: Person
grr_martin: Person
yemets: Person


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
        grr_martin, \
        yemets, \
        harry_potter

    tolkien = Person(name="J.R.R. Tolkien")
    grr_martin = Person(name="George R.R. Martin")
    yemets = Person(name="Dmitriy Yemets")

    hobbit = Book(title="The Hobbit", author=tolkien, year=1937)
    lotr = Book(title="The Lord of the Rings", author=tolkien, year=1954)
    silmarillion = Book(title="The Silmarillion", author=tolkien, year=1977)
    hurin = Book(title="Children of Hurin", author=tolkien, year=2007)
    ice_fire = Book(title="Song of Ice and Fire", author=grr_martin, year=1996)
    harry_potter = Book(title="Harry Potter", author=None, year=1997)

    async with mock_sqlite_sqla_session as session:  # noqa
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
async def test_load_books_connection(authors_books, test_connection_client):
    first = 3
    query = "{ booksConnection(first: %s) { edges { node { title } } } }" % first
    result = test_connection_client.post("/", json={"query": query}).json()

    assert "errors" not in result
    assert len(result["data"]["booksConnection"]["edges"]) == first


@pytest.mark.asyncio
async def test_connection_does_not_load_whole_model_by_default(
    authors_books, test_connection_client, monkeypatch
):
    query = "{ booksConnection(first: %s) { edges { node { faultyField } } } }" % 10
    with monkeypatch.context() as m:
        # don't log errors, we expect them
        m.setattr(StrawberryLogger, "error", lambda *args, **kwargs: None)
        with pytest.raises(DetachedInstanceError):
            test_connection_client.post("/", json={"query": query}).json()


@pytest.mark.asyncio
async def test_load_nested_connection(authors_books, test_connection_client):
    # so that at least one has books
    first = 3
    query = (
        "{ peopleConnection(first: %s) { edges { node { "
        " name books(first: %s) { edges { node { title} } }"
        " } } } }" % (first, first)
    )
    result = test_connection_client.post("/", json={"query": query}).json()
    assert "errors" not in result

    assert len(result["data"]["peopleConnection"]["edges"]) == first
    result_people = result["data"]["peopleConnection"]["edges"]
    for res_person in result_people:
        # check those who have books
        if not res_person["node"]["name"] in [p.name for p in [tolkien, grr_martin]]:
            continue
        else:
            orm_person = (
                tolkien if res_person["node"]["name"] == tolkien.name else grr_martin
            )
        assert len(res_person["node"]["books"]["edges"]) <= first
        for book in res_person["node"]["books"]["edges"]:
            assert book["node"]["title"] in [b.title for b in orm_person.books]


@pytest.mark.asyncio
async def test_nested_connection_parent_select_loads_parent_fields(
    authors_books, test_connection_client
):
    query = """
    {
      peopleConnection(first: 10) {
        edges {
          node {
            name
            booksForAddress(first: 10) {
              edges {
                node {
                  title
                }
              }
            }
          }
        }
      }
    }
    """
    result = test_connection_client.post("/", json={"query": query}).json()

    assert "errors" not in result
    edges = result["data"]["peopleConnection"]["edges"]
    tolkien_node = next(
        edge["node"] for edge in edges if edge["node"]["name"] == tolkien.name
    )
    assert tolkien_node["booksForAddress"]["edges"] == [
        {"node": {"title": "The Hobbit"}},
        {"node": {"title": "The Lord of the Rings"}},
        {"node": {"title": "The Silmarillion"}},
        {"node": {"title": "Children of Hurin"}},
    ]


@pytest.mark.asyncio
async def test_load_connection_with_filter(authors_books, test_connection_client):
    year = 1960
    query = (
        "{ bookYearFilterConnection(first: 20, filter: {"
        "lessThan: %s } ) { edges { node { year } } } }" % year
    )
    result = test_connection_client.post("/", json={"query": query}).json()
    assert "errors" not in result
    assert len(result["data"]["bookYearFilterConnection"]["edges"]) == 2
    for book in result["data"]["bookYearFilterConnection"]["edges"]:
        assert book["node"]["year"] < year


@pytest.mark.asyncio
async def test_load_connection_with_compound_filter(
    authors_books, test_connection_client
):
    l_year, r_year = 1960, 1980
    query = (
        "{ bookYearFilterConnection(first: 20, filter: {"
        "lessThan: %s, greaterThan: %s  } ) { edges { node { year } } } }"
        % (r_year, l_year)
    )
    result = test_connection_client.post("/", json={"query": query}).json()
    assert "errors" not in result
    assert len(result["data"]["bookYearFilterConnection"]["edges"]) == 1
    for book in result["data"]["bookYearFilterConnection"]["edges"]:
        assert (book["node"]["year"] < r_year) and (book["node"]["year"] > l_year)


@pytest.mark.asyncio
async def test_load_connection_with_filter_empty(authors_books, test_connection_client):
    query = (
        "{ bookYearFilterConnection(first: 20, filter: {"
        "} ) { edges { node { year } } } }"
    )
    result = test_connection_client.post("/", json={"query": query}).json()
    assert "errors" not in result
    assert len(result["data"]["bookYearFilterConnection"]["edges"]) == 6


@pytest.mark.asyncio
async def test_load_connection_with_order(authors_books, test_connection_client):
    query = (
        "{ bookOrderConnection(first: 20, order: {"
        "field: YEAR, order: ASC} ) { edges { node { year } } } }"
    )
    result = test_connection_client.post("/", json={"query": query}).json()
    assert "errors" not in result
    assert len(result["data"]["bookOrderConnection"]["edges"]) == 6
    years = [
        book["node"]["year"] for book in result["data"]["bookOrderConnection"]["edges"]
    ]
    assert years == sorted(years)


@pytest.mark.asyncio
async def test_load_connection_with_order_title(authors_books, test_connection_client):
    query = (
        "{ bookOrderConnection(first: 20, order: {"
        "field: TITLE, order: ASC} ) { edges { node { year title } } } }"
    )
    result = test_connection_client.post("/", json={"query": query}).json()
    assert "errors" not in result
    assert len(result["data"]["bookOrderConnection"]["edges"]) == 6
    titles = [
        book["node"]["title"] for book in result["data"]["bookOrderConnection"]["edges"]
    ]
    years = [
        book["node"]["year"] for book in result["data"]["bookOrderConnection"]["edges"]
    ]
    assert titles == sorted(titles)
    assert years != sorted(years)


@pytest.mark.asyncio
async def test_load_connection_empty(authors_books, test_connection_client):
    l_year, r_year = 1960, 1980
    query = (
        "{ bookYearFilterConnection(first: 20, filter: {"
        "lessThan: %s, greaterThan: %s  } ) { edges { node { year } } } }"
        % (l_year, r_year)
    )
    result = test_connection_client.post("/", json={"query": query}).json()
    assert "errors" not in result
    assert len(result["data"]["bookYearFilterConnection"]["edges"]) == 0


@pytest.mark.asyncio
async def test_load_connection_paginate_trough_it(
    authors_books, test_connection_client
):
    query = (
        "{ bookOrderConnection(first: 20, order: {"
        "field: YEAR, order: ASC} ) { edges { node { year } cursor } } }"
    )
    result = test_connection_client.post("/", json={"query": query}).json()
    assert "errors" not in result
    second_book_cursor = result["data"]["bookOrderConnection"]["edges"][1]["cursor"]
    third_book = result["data"]["bookOrderConnection"]["edges"][2]["node"]
    query = (
        '{ bookOrderConnection(first: 20, after: "%s", order: {'
        "field: YEAR, order: ASC} ) { edges { node { year } cursor } } }"
        % second_book_cursor
    )
    result2 = test_connection_client.post("/", json={"query": query}).json()
    assert "errors" not in result2
    assert len(result2["data"]["bookOrderConnection"]["edges"]) == 4
    assert result2["data"]["bookOrderConnection"]["edges"][0]["node"] == third_book


@pytest.mark.asyncio
async def test_load_nested_connection_empty(authors_books, test_connection_client):
    query = (
        '{ personByName( name: "%s" ) { '
        "name books(first: %s) { edges { node { title} } } } }" % (yemets.name, 10)
    )
    result = test_connection_client.post("/", json={"query": query}).json()
    assert "errors" not in result
    assert result["data"]["personByName"]["name"] == yemets.name
    assert len(result["data"]["personByName"]["books"]["edges"]) == 0


@pytest.mark.asyncio
async def test_root_connection_parent_select_fails_clearly(
    authors_books, test_connection_client
):
    query = """
    {
      invalidParentSelectConnection(first: 2) {
        edges {
          node {
            title
          }
        }
      }
    }
    """
    with pytest.raises(ValueError, match="relationship-backed connections"):
        test_connection_client.post("/", json={"query": query}).json()
