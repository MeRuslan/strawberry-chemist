from typing import Optional, List

import strawberry
from sqlalchemy import ForeignKey, select
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from strawberry.types import Info

import strawberry_chemist


class Base(DeclarativeBase):
    pass


class BookRole(Base):
    __tablename__ = "association_table"
    left_id: Mapped[int] = mapped_column(ForeignKey("author.id"), primary_key=True)
    right_id: Mapped[int] = mapped_column(ForeignKey("book.id"), primary_key=True)
    role: Mapped[Optional[str]]
    # child: Mapped["Book"] = relationship(back_populates="authors")
    # parent: Mapped["Author"] = relationship(back_populates="books")


class Author(Base):
    __tablename__ = "author"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str]
    # children_ass: Mapped[List["BookRole"]] = relationship(back_populates="parent")
    books: Mapped[List["Book"]] = relationship(
        secondary="association_table", back_populates="authors"
    )


class Book(Base):
    __tablename__ = "book"
    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str]
    # parents_ass: Mapped[List["BookRole"]] = relationship(back_populates="child")
    authors: Mapped[List["Author"]] = relationship(
        secondary="association_table", back_populates="books"
    )


@strawberry_chemist.type(model=Author)
class AuthorNode:
    name: str
    books: List["BookNode"]
    books_connection: strawberry_chemist.Connection["BookNode"] = (
        strawberry_chemist.connection(source="books")
    )


@strawberry_chemist.type(model=Book)
class BookNode:
    title: str
    authors: List["AuthorNode"]
    authors_connection: strawberry_chemist.Connection["AuthorNode"] = (
        strawberry_chemist.connection(source="authors")
    )


@strawberry.type
class Query:
    people_connection: strawberry_chemist.Connection["AuthorNode"] = (
        strawberry_chemist.connection()
    )
    books_connection: strawberry_chemist.Connection["BookNode"] = (
        strawberry_chemist.connection()
    )

    @strawberry.field
    async def person_by_name(self, info: Info, name: str) -> Optional[AuthorNode]:
        async with info.context.get_session() as session:
            person = (
                await session.execute(select(Author).where(Author.name.like(name)))
            ).scalar_one_or_none()
            return person

    @strawberry.field
    async def book_by_title(self, info: Info, title: str) -> Optional[BookNode]:
        async with info.context.get_session() as session:
            book = (
                await session.execute(select(Book).where(Book.title.like(title)))
            ).scalar_one_or_none()
            return book


schema = strawberry.Schema(query=Query, extensions=strawberry_chemist.extensions())
