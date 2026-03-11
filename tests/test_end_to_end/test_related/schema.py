from typing import List, Any, Optional

import strawberry
from sqlalchemy import Integer, String, select, ForeignKey, SmallInteger
from sqlalchemy.orm import declarative_base, relationship, Mapped, mapped_column
from strawberry.types import Info

import strawberry_sqlalchemy
from strawberry_sqlalchemy.extentions import DataLoadersExtension, InfoCacheExtension
from strawberry_sqlalchemy.filters.pre_filter import RuntimeFilter
from strawberry_sqlalchemy.gql_context import SQLAlchemyContext
from strawberry_sqlalchemy.relay import NodeEdge, Node

Base = declarative_base()
current_year = 2023


class Person(Base):
    __tablename__ = 'person'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    # id = Column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String)
    address: Mapped[str] = mapped_column(String, default="Baker Street 221B")
    books: Mapped[List["Book"]] = relationship("Book", back_populates="author")


class Book(Base):
    __tablename__ = 'books'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String)
    year: Mapped[int] = mapped_column(SmallInteger)
    isbn: Mapped[str] = mapped_column(String)

    author_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("person.id"))
    author: Mapped[Optional["Person"]] = relationship("Person", back_populates="books")


@strawberry_sqlalchemy.type(model=Person)
class PersonNode(Node):
    name: str
    books: List['BookNode']
    books_before_1960: List['BookNode'] = strawberry_sqlalchemy.relation_field(
        sqlalchemy_name="books",
        pre_filter=RuntimeFilter([
            lambda: Book.year < 1960
        ]),
    )
    books_after_1960_starting_with_the: List['BookNode'] = strawberry_sqlalchemy.relation_field(
        sqlalchemy_name="books",
        pre_filter=RuntimeFilter([
            lambda: Book.year > 1960,
            lambda: Book.title.like("The %")
        ]),
    )
    book_years: List[int] = strawberry_sqlalchemy.relation_field(
        sqlalchemy_name="books",
        needs_fields=['year'],
        post_processor=lambda source, result: [book.year for book in result]
    )
    book_binary_years: List["BinaryYear"] = strawberry_sqlalchemy.relation_field(
        sqlalchemy_name="books",
        ignore_field_selections=True,
        post_processor=lambda source, result: [BinaryYear(binary_year=f"{book.year:b}") for book in result]
    )


def title_thrice(root: "Book", info: Info) -> str:
    return root.title * 3


@strawberry_sqlalchemy.type(model=Book)
class BookNode(Node):
    title: str
    year: int
    author: Optional[PersonNode]
    years_since_published: int = strawberry_sqlalchemy.field(
        sqlalchemy_name='year',
        post_processor=lambda source, result: current_year - result
    )
    title_with_isbn: str = strawberry_sqlalchemy.field(
        sqlalchemy_name='title',
        additional_parent_fields=['isbn'],
        post_processor=lambda source, result: f"{source.title} ({source.isbn})"
    )
    faulty_title_with_isbn: str = strawberry_sqlalchemy.field(
        sqlalchemy_name='title',
        post_processor=lambda source, result: f"{source.title} ({source.isbn})"
    )

    @strawberry_sqlalchemy.field(sqlalchemy_name='title')
    def title_twice(self, info: Info) -> str:
        return self.title * 2

    title_thrice = strawberry_sqlalchemy.field(title_thrice, sqlalchemy_name='title')


@strawberry.type
class BinaryYear:
    binary_year: str
    base: int = 2


@strawberry.type
class Query(NodeEdge):
    @strawberry.field
    async def person_by_name(self, info: Info[SQLAlchemyContext, Any], name: str) -> Optional[PersonNode]:
        async with info.context.get_session() as session:
            person = (await session.execute(
                select(Person).where(Person.name.like(name))
            )).scalar_one_or_none()
            return person


schema = strawberry.Schema(query=Query, extensions=[DataLoadersExtension, InfoCacheExtension])
