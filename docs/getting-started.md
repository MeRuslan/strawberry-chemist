# Getting Started

## Installation

```bash
pip install strawberry-chemist
```

Supported Python versions: `3.11` through `3.14`.

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


def build_context(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    request_id: str = "dev-request",
    current_user_id: int | None = None,
) -> AppContext:
    del request_id, current_user_id
    return AppContext(session_factory)


@sc.node(model=BookModel)
class Book:
    title: str


@strawberry.type
class Query:
    books: sc.Connection[Book] = sc.connection()


schema = strawberry.Schema(query=Query, extensions=sc.extensions())
```

## Execution context

Chemist does not create a GraphQL context for you. Your application passes one
into Strawberry execution, and `sc.extensions()` augments that same object with
request-local dataloaders and selection caches.

```python
result = await schema.execute(
    query,
    context_value=build_context(session_factory),
)
```

## Local docs and examples

Serve the docs locally:

```bash
uv sync --group dev
uv run mkdocs serve
```

Run an example against the current checkout:

```bash
make example-test EXAMPLE=03_connections_filters_and_ordering
```

Run the same example against the pinned published package instead:

```bash
make example-test-published EXAMPLE=03_connections_filters_and_ordering
```

Or work directly inside the example directory:

```bash
cd examples/03_connections_filters_and_ordering
make test
make schema
make serve PORT=8000
```
