# strawberry-chemist

`strawberry-chemist` helps expose SQLAlchemy models through Strawberry without
turning your GraphQL schema into generated magic.

The package is intentionally explicit. You still write the Strawberry types you
want clients to see. That makes the DTO layer visible, keeps the public
contract adaptable, and fits production codebases that care about query shape,
permissions, loading behavior, and long-term schema maintenance.

Chemist focuses on the parts that are repetitive and SQLAlchemy-aware:

- field mapping and renaming
- relationship loading
- root and nested connections
- filtering, ordering, and pagination
- relay IDs and node lookup
- dataloaders and selection-aware loading

## Installation

```bash
pip install strawberry-chemist
```

Supported Python versions:

- `3.11`
- `3.12`

## Quick example

```python
import strawberry
import strawberry_chemist as sc


@sc.node(model=BookModel)
class Book:
    title: str
    published_year: int = sc.attr("year")


@sc.filter(model=BookModel)
class BookFilter(sc.FilterSet):
    title: sc.StringFilter = sc.filter_field()


@sc.order(model=BookModel)
class BookOrder:
    published_year = sc.order_field(path="year")


@strawberry.type
class Query:
    node = sc.node_field()
    books: sc.Connection[Book] = sc.connection(
        filter=BookFilter,
        order=BookOrder,
        pagination=sc.CursorPagination(max_limit=20),
    )


schema = strawberry.Schema(query=Query, extensions=sc.extensions())
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

The contract examples under `examples/v0_2_api/` can run in two modes.

Against the current checkout:

```bash
scripts/run-example-local 03_connections_filters_and_ordering
```

Against the pinned published package:

```bash
scripts/run-example-published 03_connections_filters_and_ordering
```

If you want to force published-mode testing against a locally built
distribution, point the script at a `build` output directory:

```bash
uv run python -m build --outdir /tmp/strawberry-chemist-dist
STRAWBERRY_CHEMIST_FIND_LINKS=/tmp/strawberry-chemist-dist \
  scripts/run-example-published 03_connections_filters_and_ordering
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

Run the default non-Postgres test suite:

```bash
uv run pytest
```

Run formatting and type checks:

```bash
uv run pre-commit run --all-files
uv run mypy
```

Release notes live in [CHANGELOG.md](CHANGELOG.md). Current limitations are
documented in [LIMITATIONS.md](LIMITATIONS.md).
