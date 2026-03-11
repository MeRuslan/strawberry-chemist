# Getting Started

## Installation

```bash
pip install strawberry-chemist
```

Supported Python versions:

- `3.11`
- `3.12`

## Context contract

Chemist-managed fields expect your GraphQL context to provide an async
`get_session()` context manager that yields a SQLAlchemy `AsyncSession`.

## Minimal setup

```python
from contextlib import asynccontextmanager

import strawberry
import strawberry_chemist as sc
from sqlalchemy import Integer, String
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class BookModel(Base):
    __tablename__ = "books"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(200))


class AppContext:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]):
        self._session_factory = session_factory

    @asynccontextmanager
    async def get_session(self):
        async with self._session_factory() as session:
            yield session


@sc.node(model=BookModel)
class Book:
    title: str


@strawberry.type
class Query:
    books: sc.Connection[Book] = sc.connection()


schema = strawberry.Schema(query=Query, extensions=sc.extensions())
```

## Local docs and examples

Serve the docs locally:

```bash
uv sync --group dev
uv run mkdocs serve
```

Run an example against the current checkout:

```bash
scripts/run-example-local 03_connections_filters_and_ordering
```

Run the same example against the pinned published package instead:

```bash
scripts/run-example-published 03_connections_filters_and_ordering
```
