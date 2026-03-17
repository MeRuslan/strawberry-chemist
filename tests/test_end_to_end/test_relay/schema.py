from typing import Any, List, Optional

import strawberry
from sqlalchemy import Integer, String, select
from sqlalchemy.orm import declarative_base, Mapped, mapped_column
from strawberry import BasePermission
from strawberry.types import Info

import strawberry_chemist as sc
from strawberry_chemist.gql_context import SQLAlchemyContext
from strawberry_chemist.relay import resolve_node


Base = declarative_base()


class Book(Base):
    __tablename__ = "books"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String)


@sc.type(model=Book)
class BookType(sc.Node):
    title: str


class NoPermission(BasePermission):
    async def has_permission(self, source: Any, info: Info, **kwargs):
        return False


@strawberry.type
class Query:
    node = sc.node_field(allowed_types=(BookType,))
    book_by_id = sc.node_field(allowed_types=(BookType,), name="bookById")

    @strawberry.field
    def hello(self) -> str:
        return "Hello, world!"

    @strawberry.field
    async def all_books(self, info: Info[SQLAlchemyContext, Any]) -> List[BookType]:
        async with info.context.get_session() as session:
            return (await session.execute(select(Book))).scalars().all()

    @strawberry.field
    async def no_permission_book_by_id(
        self,
        info: Info[SQLAlchemyContext, Any],
        id: strawberry.ID,
    ) -> Optional[BookType]:
        node = await resolve_node(info, id, allowed_types=(BookType,))
        if node is None:
            return None

        permission = NoPermission()
        allowed = await permission.has_permission(node, info=info)
        if not allowed:
            raise PermissionError(getattr(permission, "message", None))
        return node


schema = strawberry.Schema(query=Query, extensions=sc.extensions())
