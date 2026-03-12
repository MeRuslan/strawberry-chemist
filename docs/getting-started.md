# Getting Started

## Installation

```bash
pip install strawberry-chemist uvicorn aiosqlite
```

Supported Python versions: `3.11` through `3.14`.

## Context contract

In practice, your GraphQL context should provide an async `get_session()`
context manager that yields a SQLAlchemy `AsyncSession`.

Your own root resolvers will usually use it to load ORM rows, and
Chemist-managed fields such as `sc.relationship(...)`, `sc.connection(...)`,
and node lookup helpers use that same contract.

At runtime, `sc.extensions()` also attaches request-local dataloaders and
selection caches onto that same context object. That is usually invisible to
application code, but it is still part of the execution contract.

## Minimal setup

This is a single-file minimal app that serves a Chemist-backed GraphQL schema
over ASGI and resolves `@sc.type(model=...)` instances from real SQLAlchemy
queries:

```python
from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from typing import Any

import strawberry
import strawberry_chemist as sc
from sqlalchemy import Integer, String, select
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from strawberry.asgi import GraphQL

DATABASE_URL = "sqlite+aiosqlite:///./app.db"


class Base(DeclarativeBase):
    pass


class BookModel(Base):
    __tablename__ = "books"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(200))

engine = create_async_engine(DATABASE_URL)
session_factory = async_sessionmaker(engine, expire_on_commit=False)


class AppContext:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]):
        self._session_factory = session_factory

    @asynccontextmanager
    async def get_session(self):
        async with self._session_factory() as session:
            yield session


def build_context(session_factory: async_sessionmaker[AsyncSession]) -> AppContext:
    return AppContext(session_factory)


@sc.type(model=BookModel)
class Book:
    title: str


@strawberry.type
class Query:
    @strawberry.field
    async def books(
        self,
        info: strawberry.Info[AppContext, None],
    ) -> list[Book]:
        async with info.context.get_session() as session:
            result = await session.scalars(
                select(BookModel).order_by(BookModel.title.asc())
            )
            return list(result)


def build_schema() -> strawberry.Schema:
    return strawberry.Schema(query=Query, extensions=sc.extensions())


class ChemistGraphQL(GraphQL):
    def __init__(
        self,
        schema: strawberry.Schema,
        *,
        session_factory: async_sessionmaker[AsyncSession],
    ) -> None:
        super().__init__(schema)
        self._session_factory = session_factory

    async def get_context(self, request: Any, response: Any) -> AppContext:
        del request, response
        return build_context(self._session_factory)


async def prepare_database() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with session_factory() as session:
        has_books = await session.scalar(select(BookModel.id).limit(1))
        if has_books is None:
            session.add(BookModel(title="The Hobbit"))
            await session.commit()


app = ChemistGraphQL(build_schema(), session_factory=session_factory)


if __name__ == "__main__":
    import uvicorn

    asyncio.run(prepare_database())
    uvicorn.run(app, host="127.0.0.1", port=8000)
```

Run it:

```bash
python app.py
```

Then open `http://127.0.0.1:8000` and run:

```graphql
query {
  books {
    title
  }
}
```

Expected result:

```json
{
  "data": {
    "books": [
      {
        "title": "The Hobbit"
      }
    ]
  }
}
```

## Example projects

The strawberry-chemist ships a dozen examples that serve as a public contract
validation tests for the project. You can have a look at them, 
or spin them up locally for references:

```bash
cd examples/03_connections_filters_and_ordering
make test
make schema
make serve PORT=8000
```
