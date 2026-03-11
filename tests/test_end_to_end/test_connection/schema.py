from enum import Enum
from typing import List, Optional, Any

import strawberry
from sqlalchemy import Integer, String, ForeignKey, SmallInteger, select
from sqlalchemy.orm import declarative_base, relationship, Mapped, mapped_column
from strawberry.types import Info

import strawberry_chemist
from strawberry_chemist.gql_context import SQLAlchemyContext

Base = declarative_base()


class Book(Base):
    __tablename__ = "books"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String)
    year: Mapped[int] = mapped_column(SmallInteger)

    author_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("person.id"))
    author: Mapped[Optional["Person"]] = relationship("Person", back_populates="books")


class Person(Base):
    __tablename__ = "person"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String)
    address: Mapped[str] = mapped_column(String, default="Baker Street 221B")
    books: Mapped[List["Book"]] = relationship("Book", back_populates="author")


@strawberry_chemist.type(model=Person)
class PersonNode:
    name: str
    books: strawberry_chemist.Connection["BookNode"] = strawberry_chemist.connection()


@strawberry_chemist.type(model=Book)
class BookNode:
    title: str
    year: int
    author: Optional[PersonNode]
    faulty_field: str = strawberry_chemist.field(
        sqlalchemy_name="title",
        post_processor=lambda source, result: f"{source.title} ({source.year})",
    )


@strawberry.input
class BookAgeFilter:
    less_than: Optional[int] = None
    greater_than: Optional[int] = None


def apply_book_year_filter(query, value: BookAgeFilter, ctx):
    if value.less_than is not None:
        query = query.where(Book.year < value.less_than)
    if value.greater_than is not None:
        query = query.where(Book.year > value.greater_than)
    return query


book_year_filter = strawberry_chemist.manual_filter(
    input=BookAgeFilter,
    apply=apply_book_year_filter,
)


@strawberry.enum
class OrderEnum(Enum):
    YEAR: str = "year"
    TITLE: str = "title"


@strawberry.input
class BookOrder:
    field: OrderEnum
    order: strawberry_chemist.SortDirection


def apply_book_order(query, value: BookOrder, ctx):
    if value.field == OrderEnum.YEAR:
        order_column = Book.year
    else:
        order_column = Book.title

    if value.order == strawberry_chemist.SortDirection.DESC:
        return query.order_by(order_column.desc())
    return query.order_by(order_column.asc())


book_order = strawberry_chemist.manual_order(
    input=BookOrder,
    name="order",
    python_name="order",
    apply=apply_book_order,
)


@strawberry.type
class Query:
    people_connection: strawberry_chemist.Connection["PersonNode"] = (
        strawberry_chemist.connection()
    )
    books_connection: strawberry_chemist.Connection["BookNode"] = (
        strawberry_chemist.connection()
    )

    book_year_filter_connection: strawberry_chemist.Connection["BookNode"] = (
        strawberry_chemist.connection(filter=book_year_filter)
    )

    book_order_connection: strawberry_chemist.Connection["BookNode"] = (
        strawberry_chemist.connection(order=book_order)
    )

    @strawberry.field
    async def person_by_name(
        self, info: Info[SQLAlchemyContext, Any], name: str
    ) -> Optional[PersonNode]:
        async with info.context.get_session() as session:
            return (
                await session.execute(select(Person).where(Person.name.like(name)))
            ).scalar_one_or_none()


schema = strawberry.Schema(query=Query, extensions=strawberry_chemist.extensions())
