# strawberry-chemist

`strawberry-chemist` is a Strawberry + SQLAlchemy integration for applications
that want explicit GraphQL types instead of whole-schema autogeneration.

That explicitness is intentional. You decide what your GraphQL DTOs look like,
which fields exist, how relationships are exposed, and where client-controlled
querying is allowed. The package focuses on reducing boilerplate around that
work, not hiding it. That makes the public contract easier to reason about,
easier to adapt over time, and easier to keep production-safe.

The design center is:

- explicit Strawberry classes stay
- SQLAlchemy stays first-class
- connections, filters, ordering, relay IDs, and dataloading stay practical
- unusual production cases still have escape hatches

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

## What the package helps with

- mapping explicit Strawberry types to SQLAlchemy models
- renaming and computing fields without losing visibility into the schema
- loading related data with selection-aware dataloading
- exposing root and nested collections through a unified connection API
- adding filter, order, pagination, and relay/node behavior without giving up
  control of the GraphQL contract

## Where to go next

- start with [Getting Started](getting-started.md)
- browse the [API Surface](api-surface.md)
- use the runnable [Examples](examples.md) as acceptance targets
