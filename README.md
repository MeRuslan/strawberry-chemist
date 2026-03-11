# strawberry-chemist

Explicit GraphQL types. Smart SQLAlchemy loading.

- mapped fields
- computed fields
- scoped relationships
- queryable connections
- filters and ordering
- relay IDs
- node lookup
- selection-aware dataloading

`strawberry-chemist` helps expose SQLAlchemy models through Strawberry without
turning your GraphQL schema into generated magic.

The package is intentionally explicit. You still write the Strawberry types you
want clients to see. That keeps the DTO layer visible, keeps the public
contract adaptable, and fits production codebases that care about query shape,
permissions, loading behavior, and long-term schema maintenance.

That explicitness does not mean giving up performance. Chemist-managed
relationship and connection fields are selection-aware and dataloader-backed, so
you can keep explicit DTOs without falling into per-parent N+1 loading.

## Installation

```bash
pip install strawberry-chemist
```

## What It Looks Like

Server-scoped relationship-backed field:

```python
import strawberry_chemist as sc
from strawberry_chemist.gql_context import context_var


@sc.type(model=BookModel)
class Book:
    @sc.relationship(
        "bookmarks",
        where=lambda: BookmarkModel.user_id == context_var.get().current_user_id,
        select=["id"],
    )
    def is_bookmarked(self, bookmarks: list[BookmarkModel]) -> bool:
        return bool(bookmarks)
```

Note: `current_user_id` is application data; the package does not ship auth.

Computed field from selected columns:

```python
import strawberry_chemist as sc


@sc.type(model=BookModel)
class Book:
    @sc.field(select=["title", "isbn"])
    def title_with_isbn(self, title: str, isbn: str) -> str:
        return f"{title} ({isbn})"
```

Queryable relationship-backed connection:

```python
import strawberry_chemist as sc


@sc.type(model=AuthorModel)
class Author:
    books: sc.Connection[Book] = sc.connection(
        source="books",
        filter=BookFilter,
        order=BookOrder,
        pagination=sc.CursorPagination(max_limit=20),
    )
```

Your GraphQL context must provide a `get_session()` async context manager that
returns a SQLAlchemy `AsyncSession`.

## Public docs

The public docs live in [docs/](docs/). The published site is intended for
GitHub Pages and is built with MkDocs.

Useful entrypoints:

- [Overview](docs/index.md)
- [Getting Started](docs/getting-started.md)
- [API Surface](docs/api-surface.md)
- [Examples](docs/examples.md)

Serve the docs locally:

```bash
uv sync --group dev
uv run mkdocs serve
```

Build the docs locally:

```bash
uv run mkdocs build --strict
```

## Runnable examples

Each numbered example under `examples/` is self-contained. The root
`example-*` commands below just delegate into that example's own `Makefile`.
Each example is intentionally split into:

- `db.py` for SQLAlchemy models and seeded database setup
- `schema.py` for `AppContext`, GraphQL types, and `build_schema()`
- `app.py` for the tiny runtime CLI that prints SDL or serves the schema

Serve a seeded sample schema locally:

```bash
make example-serve EXAMPLE=03_connections_filters_and_ordering PORT=8000
```

The contract examples tests under `examples/` can run in two modes.

Against the current checkout:

```bash
make example-test EXAMPLE=03_connections_filters_and_ordering
```

Against the pinned published package:

```bash
make example-test-published EXAMPLE=03_connections_filters_and_ordering
```

Print a sample schema:

```bash
make example-schema EXAMPLE=03_connections_filters_and_ordering
```

Run the same example directly from its own directory:

```bash
cd examples/03_connections_filters_and_ordering
make test
make schema
make serve PORT=8000
```

If you want to force published-mode testing against a locally built
distribution, point the published-mode flow at a `build` output directory:

```bash
uv run python -m build --outdir /tmp/strawberry-chemist-dist
STRAWBERRY_CHEMIST_FIND_LINKS=/tmp/strawberry-chemist-dist \
  make example-test-published EXAMPLE=03_connections_filters_and_ordering
```

## API overview

- Types and fields: `@sc.type`, `@sc.node`, `sc.attr`, `@sc.field`
- Relationships: `sc.relationship(...)`
- Collections: `sc.connection(...)`, `sc.Connection`, `sc.OffsetConnection`
- Pagination: `sc.CursorPagination`, `sc.OffsetPagination`, `sc.PaginationPolicy`
- Filters: `@sc.filter`, `sc.FilterSet`, `sc.filter_field`, `sc.manual_filter`
- Ordering: `@sc.order`, `sc.order_field`, `sc.manual_order`
- Relay: `sc.node_field()`, `sc.node_lookup(...)`
- Schema integration: `sc.extensions()`

Each part of the surface has a dedicated public docs page and at least one
example reference in [docs/examples.md](docs/examples.md).

## Development

Run the default non-Postgres test suite with either:

```bash
uv run pytest
make test
```

Run formatting and type checks:

```bash
uv run pre-commit run --all-files
uv run mypy
make mypy
make check
```

Release notes live in [CHANGELOG.md](CHANGELOG.md). Current limitations are
documented in [LIMITATIONS.md](LIMITATIONS.md).
