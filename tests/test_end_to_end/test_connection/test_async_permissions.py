from contextlib import asynccontextmanager

import pytest
import strawberry
import strawberry_chemist as sc
from sqlalchemy import String
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from strawberry_chemist.gql_context import SQLAlchemyContext


class Base(DeclarativeBase):
    pass


class ItemModel(Base):
    __tablename__ = "item"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String)


class AllowAsync(strawberry.BasePermission):
    async def has_permission(self, source, info, **kwargs) -> bool:
        return True


class Context(SQLAlchemyContext):
    def __init__(self, maker):
        self.maker = maker

    @asynccontextmanager
    async def get_session(self):
        async with self.maker() as session:
            yield session


@sc.type(model=ItemModel)
class Item(sc.Node):
    name: str


@strawberry.type
class Query:
    items: sc.Connection[Item] = sc.connection(permission_classes=[AllowAsync])


@pytest.mark.asyncio
async def test_connection_supports_async_permission_classes() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    maker = async_sessionmaker(engine, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with maker() as session:
        session.add(ItemModel(id=1, name="one"))
        await session.commit()

    schema = strawberry.Schema(query=Query, extensions=sc.extensions())
    result = await schema.execute(
        "{ items(first: 10) { edges { node { name } } } }",
        context_value=Context(maker),
    )

    await engine.dispose()

    assert result.errors is None, result.errors
    assert result.data == {
        "items": {
            "edges": [
                {
                    "node": {
                        "name": "one",
                    }
                }
            ]
        }
    }
