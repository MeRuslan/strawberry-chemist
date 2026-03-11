from enum import Enum
from typing import List, Optional, Any

import strawberry
from sqlalchemy import Integer, String, ForeignKey, SmallInteger, select
from sqlalchemy.orm import declarative_base, relationship, Mapped, mapped_column
from strawberry.types import Info

import strawberry_chemist
from strawberry_chemist.extentions import DataLoadersExtension, InfoCacheExtension
from strawberry_chemist.gql_context import SQLAlchemyContext
from strawberry_chemist.pagination import RelayConnection
from strawberry_chemist.relay import NodeEdge, Node
from strawberry_chemist.filters import StrawberrySQLAlchemyFilter
from strawberry_chemist.order import StrawberrySQLAlchemyOrdering, OrderAD

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
class PersonNode(Node):
    name: str
    books: RelayConnection["BookNode"] = strawberry_chemist.relay_connection_field()


@strawberry_chemist.type(model=Book)
class BookNode(Node):
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


book_year_filter = StrawberrySQLAlchemyFilter(
    input_type=BookAgeFilter,
    input_filter_map={
        "less_than": lambda query, value: (
            query.where(Book.year < value) if value else query
        ),
        "greater_than": lambda query, value: (
            query.where(Book.year > value) if value else query
        ),
    },
)


@strawberry.enum
class OrderEnum(Enum):
    YEAR: str = "year"
    TITLE: str = "title"


@strawberry.input
class BookOrder:
    field: OrderEnum
    order: OrderAD


book_order = StrawberrySQLAlchemyOrdering(
    input_type=BookOrder,
    resolve_ordering_map={
        OrderEnum.YEAR: lambda query: (query, Book.year),
        OrderEnum.TITLE: lambda query: (query, Book.title),
    },
)


@strawberry.type
class Query(NodeEdge):
    people_connection: RelayConnection["PersonNode"] = (
        strawberry_chemist.relay_connection_field()
    )
    books_connection: RelayConnection["BookNode"] = (
        strawberry_chemist.relay_connection_field()
    )

    book_year_filter_connection: RelayConnection["BookNode"] = (
        strawberry_chemist.relay_connection_field(filter=book_year_filter)
    )

    book_order_connection: RelayConnection["BookNode"] = (
        strawberry_chemist.relay_connection_field(order=book_order)
    )

    @strawberry.field
    async def person_by_name(
        self, info: Info[SQLAlchemyContext, Any], name: str
    ) -> Optional[PersonNode]:
        async with info.context.get_session() as session:
            return (
                await session.execute(select(Person).where(Person.name.like(name)))
            ).scalar_one_or_none()


schema = strawberry.Schema(
    query=Query, extensions=[DataLoadersExtension, InfoCacheExtension]
)
