from __future__ import annotations

import strawberry
import strawberry_chemist
from sqlalchemy import Integer, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from strawberry.types import Info

from strawberry_chemist.gql_context import SQLAlchemyContext


class Base(DeclarativeBase):
    pass


class Book(Base):
    __tablename__ = "book"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String)


@strawberry_chemist.type(model=Book)
class BookNode:
    title: str


@strawberry.type
class Query:
    @strawberry.field
    def book(self, info: Info[SQLAlchemyContext, None]) -> BookNode:
        del info
        return Book(id=1, title="The Hobbit")


def main() -> None:
    schema = strawberry.Schema(query=Query)
    result = schema.execute_sync("{ book { title } }")
    if result.errors:
        raise SystemExit(result.errors[0])

    assert result.data == {"book": {"title": "The Hobbit"}}
    print(result.data)


if __name__ == "__main__":
    main()
