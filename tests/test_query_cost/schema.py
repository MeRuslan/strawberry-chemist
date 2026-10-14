from typing import List, Optional, Union

import strawberry
from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, declarative_base, mapped_column, relationship

import strawberry_chemist as sc
from strawberry_chemist.pagination import CursorPaginationInput

Base = declarative_base()


class Author(Base):
    __tablename__ = "cost_author"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String)
    books: Mapped[List["Book"]] = relationship("Book", back_populates="author")


class Book(Base):
    __tablename__ = "cost_book"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String)
    author_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("cost_author.id")
    )
    author: Mapped[Optional[Author]] = relationship("Author", back_populates="books")


@strawberry.type
class Tag:
    name: str


@sc.type(model=Author)
class AuthorNode:
    name: str
    books: sc.Connection["BookNode"] = sc.connection(
        pagination=sc.CursorPagination(max_limit=10, nested=True)
    )
    flat_books: sc.Connection["BookNode"] = sc.connection(
        source="books", pagination=sc.CursorPagination(max_limit=10)
    )
    books_page: sc.OffsetConnection["BookNode"] = sc.connection(
        source="books",
        pagination=sc.OffsetPagination(default_limit=2, max_limit=20, nested=True),
    )

    @strawberry.field(metadata=sc.cost(list_size=3))
    def tags(self) -> List[Tag]:
        return []

    @strawberry.field
    def labels(self) -> List[Tag]:
        return []


@sc.type(model=Book)
class BookNode:
    title: str
    author: Optional[AuthorNode]


@strawberry.type
class Query:
    authors: sc.Connection[AuthorNode] = sc.connection(
        pagination=sc.CursorPagination(max_limit=20, nested=True)
    )

    @strawberry.field(
        metadata=sc.cost(pagination=sc.CursorPagination(max_limit=5, nested=True))
    )
    def featured(
        self, pagination: Optional[CursorPaginationInput] = None
    ) -> sc.Connection[BookNode]:
        raise AssertionError("never resolved in these tests")

    @strawberry.field(metadata=sc.cost(pagination=sc.OffsetPagination(max_limit=4)))
    def recent(self, limit: int = 2) -> List[BookNode]:
        raise AssertionError("never resolved in these tests")

    @strawberry.field(metadata=sc.cost(list_size=2))
    def search(self) -> List[Union[AuthorNode, BookNode]]:
        raise AssertionError("never resolved in these tests")

    @sc.node_lookup(
        model=Author,
        node_param_name="author",
        metadata=sc.cost(pagination=sc.CursorPagination(max_limit=5, nested=True)),
    )
    async def author_books(
        self,
        info: strawberry.Info,
        author: Optional[Author],
        pagination: Optional[CursorPaginationInput] = None,
    ) -> sc.Connection[BookNode]:
        raise AssertionError("never resolved in these tests")


schema = strawberry.Schema(query=Query, extensions=sc.extensions())
