from typing import List, Any, Optional

import strawberry
from sqlalchemy import Integer, String, select
from sqlalchemy.orm import declarative_base, Mapped, mapped_column
from strawberry import BasePermission
from strawberry.types import Info

import strawberry_sqlalchemy
from strawberry_sqlalchemy.extentions import DataLoadersExtension, InfoCacheExtension
from strawberry_sqlalchemy.gql_context import SQLAlchemyContext
from strawberry_sqlalchemy.relay import NodeEdge, Node, object_field

Base = declarative_base()


class Book(Base):
    __tablename__ = "books"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String)


@strawberry_sqlalchemy.type(model=Book)
class BookType(Node):
    title: str


class NoPermission(BasePermission):
    async def has_permission(self, source: Any, info: Info, **kwargs):
        return False


@strawberry.type
class Query(NodeEdge):
    @strawberry.field
    def hello(self) -> str:
        return "Hello, world!"

    @strawberry.field
    async def all_books(self, info: Info[SQLAlchemyContext, Any]) -> List[BookType]:
        async with info.context.get_session() as session:
            return (await session.execute(select(Book))).scalars().all()

    @object_field(model=Book)
    async def book_by_id(
        self, node: Book, info: Info[SQLAlchemyContext, Any]
    ) -> Optional[BookType]:
        return node

    @object_field(model=Book, node_permission_classes=[NoPermission])
    async def no_permission_book_by_id(
        self, node: Book, info: Info[SQLAlchemyContext, Any]
    ) -> Optional[BookType]:
        return node


schema = strawberry.Schema(
    query=Query, extensions=[DataLoadersExtension, InfoCacheExtension]
)
