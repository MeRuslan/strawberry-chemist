# Public API Redesign

This dossier proposes a stable public API for `strawberry-chemist` as a standalone package.

It is intentionally biased toward:

- explicit Strawberry type declarations
- strong production ergonomics over framework cleverness
- field-level convenience instead of whole-schema code generation
- selection-aware SQLAlchemy loading
- clear escape hatches for advanced query shaping

The package's current strengths are worth preserving:

- explicit GraphQL type classes authored by the application
- automatic scalar field mapping from SQLAlchemy models
- dynamic fields computed from loaded parent data
- relationship-aware dataloading and selection-based loading
- pragmatic SQLAlchemy-first behavior instead of abstract ORM wrappers

The main redesign theme is: keep the runtime power, but replace rough helper objects and overloaded field options with a smaller, more intentional surface.

## Recommended Direction

```python
import strawberry
import strawberry_chemist as sc


@sc.filter(model=Book)
class BookFilter(sc.FilterSet):
    title: sc.StringFilter = sc.filter_field()
    year: sc.IntFilter = sc.filter_field()
    author_name: sc.StringFilter = sc.filter_field(path="author.name")


@sc.order(model=Book)
class BookOrder:
    year = sc.order_field()
    title = sc.order_field()


@sc.node(model=Book)
class BookNode:
    title: str
    year: int
    author: "AuthorNode | None"

    @sc.field(select=["title", "isbn"])
    def title_with_isbn(self, title: str, isbn: str) -> str:
        return f"{title} ({isbn})"


@strawberry.type
class Query:
    node = sc.node_field()
    books: sc.Connection[BookNode] = sc.connection(
        filter=BookFilter,
        order=BookOrder,
    )


schema = strawberry.Schema(query=Query, extensions=sc.extensions())
```

## Index

- [01-principles.md](01-principles.md)
- [02-public-surface.md](02-public-surface.md)
- [03-fields-and-relationships.md](03-fields-and-relationships.md)
- [04-filters-ordering-and-connections.md](04-filters-ordering-and-connections.md)
- [05-relay-and-node-ids.md](05-relay-and-node-ids.md)
- [06-context-and-schema-integration.md](06-context-and-schema-integration.md)
- [07-migration-roadmap.md](07-migration-roadmap.md)

## Executive Summary

The proposed stable API should revolve around these concepts:

- `@strawberry_chemist.type(model=...)`: keep explicit non-node schema classes.
- `@strawberry_chemist.node(model=...)`: dedicated decorator for relay/node schema classes.
- `strawberry_chemist.attr(...)`: direct mapped fields and aliases.
- `@strawberry_chemist.field(...)`: computed scalar fields from selected parent data.
- `strawberry_chemist.relationship(...)`: relationship loading and relationship-backed computed fields.
- `strawberry_chemist.connection(...)`: one connection API for root and relationship collections.
- `strawberry_chemist.PaginationPolicy`: a stable protocol for connection pagination strategies.
- `@strawberry_chemist.filter(...)` and `@strawberry_chemist.order(...)`: declarative public filter/order DSLs.
- `strawberry_chemist.manual_filter(...)` and `strawberry_chemist.manual_order(...)`: explicit escape hatches when the app must keep a custom GraphQL input contract.
- `strawberry_chemist.node_field()`: relay/node lookup without hardcoding `id`.
- `strawberry_chemist.node_lookup(...)`: inject a looked-up ORM node into a field or mutation from a relay ID argument.
- `strawberry_chemist.extensions()`: the package-owned schema extensions bundle.
- minimal context protocol instead of a mandatory framework base class.

The following current surface should not be treated as the long-term public contract:

- `post_processor`
- `RuntimeFilter`
- `StrawberrySQLAlchemyFilter`
- `StrawberrySQLAlchemyOrdering`
- `relation_field`
- `relay_connection_field` / `limit_offset_connection_field`
- `NodeEdge`
- `input()` / `mutation()`
- internal field / loader / pagination classes
- direct reliance on `SQLAlchemyContext` / `context_var` internals
