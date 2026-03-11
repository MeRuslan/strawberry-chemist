from typing import List, Any, Optional

import strawberry
from sqlalchemy import Integer, String, select, ForeignKey, SmallInteger
from sqlalchemy.orm import declarative_base, relationship, Mapped, mapped_column
from strawberry.types import Info

import strawberry_chemist
from strawberry_chemist.gql_context import SQLAlchemyContext

Base = declarative_base()
current_year = 2023


class Person(Base):
    __tablename__ = "person"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    # id = Column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String)
    address: Mapped[str] = mapped_column(String, default="Baker Street 221B")
    books: Mapped[List["Book"]] = relationship("Book", back_populates="author")


class Book(Base):
    __tablename__ = "books"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String)
    year: Mapped[int] = mapped_column(SmallInteger)
    isbn: Mapped[str] = mapped_column(String)

    author_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("person.id"))
    author: Mapped[Optional["Person"]] = relationship("Person", back_populates="books")


@strawberry_chemist.type(model=Person)
class PersonNode:
    name: str
    books: List["BookNode"]
    books_before_1960: List["BookNode"] = strawberry_chemist.relationship(
        "books",
        where=lambda: Book.year < 1960,
    )
    books_after_1960_starting_with_the: List["BookNode"] = (
        strawberry_chemist.relationship(
            "books",
            where=[lambda: Book.year > 1960, lambda: Book.title.like("The %")],
        )
    )

    @strawberry_chemist.relationship("books", select=["year"])
    def book_years(self, books: List["Book"]) -> List[int]:
        return [book.year for book in books]

    @strawberry_chemist.relationship("books", load="full")
    def book_binary_years(self, books: List["Book"]) -> List["BinaryYear"]:
        return [BinaryYear(binary_year=f"{book.year:b}") for book in books]


def title_thrice(root: "Book", info: Info) -> str:
    return root.title * 3


@strawberry_chemist.type(model=Book)
class BookNode:
    title: str
    year: int
    author: Optional[PersonNode]

    @strawberry_chemist.field(select=["year"])
    def years_since_published(self, year: int) -> int:
        return current_year - year

    @strawberry_chemist.field(select=["title", "isbn"])
    def title_with_isbn(self, title: str, isbn: str) -> str:
        return f"{title} ({isbn})"

    @strawberry_chemist.field(select=["title"])
    def faulty_title_with_isbn(self, title: str) -> str:
        return f"{title} ({self.isbn})"

    @strawberry_chemist.field(select=["title"])
    def title_twice(self, title: str, info: Info) -> str:
        return title * 2

    title_thrice = strawberry_chemist.field(title_thrice, select=["title"])


@strawberry.type
class BinaryYear:
    binary_year: str
    base: int = 2


@strawberry.type
class Query:
    @strawberry.field
    async def person_by_name(
        self, info: Info[SQLAlchemyContext, Any], name: str
    ) -> Optional[PersonNode]:
        async with info.context.get_session() as session:
            person = (
                await session.execute(select(Person).where(Person.name.like(name)))
            ).scalar_one_or_none()
            return person


schema = strawberry.Schema(query=Query, extensions=strawberry_chemist.extensions())
