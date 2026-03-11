# strawberry-chemist

Helpers for exposing SQLAlchemy models through Strawberry GraphQL with less
boilerplate.

This package wraps common patterns for:

- generating Strawberry types from SQLAlchemy models
- exposing model fields and relationships
- relay-style IDs and connections
- connection filtering, ordering, and pagination

## Status

This project is currently alpha. The API is usable, but you should still expect
some rough edges and breaking changes while the standalone package settles.

## Installation

```bash
pip install strawberry-chemist
```

Supported Python versions:

- 3.11
- 3.12

## Minimal example

```python
from typing import Optional

import strawberry
import strawberry_chemist
from sqlalchemy import Integer, String, select
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
    async def book_by_title(
        self, info: Info[SQLAlchemyContext, None], title: str
    ) -> Optional[BookNode]:
        async with info.context.get_session() as session:
            return (
                await session.execute(select(Book).where(Book.title == title))
            ).scalar_one_or_none()


schema = strawberry.Schema(query=Query)
```

Your GraphQL context must provide a `get_session()` async context manager that
returns a SQLAlchemy `AsyncSession`.

## Development

Run the default non-Postgres test suite:

```bash
uv run pytest
```

Run formatter and type checks:

```bash
uv run pre-commit run --all-files
```

Small runnable examples live in [examples/](examples/).

## Changelog

Release notes live in [CHANGELOG.md](CHANGELOG.md).

## Limitations

Current behavioral constraints and relay ID caveats are documented in
[LIMITATIONS.md](LIMITATIONS.md).
