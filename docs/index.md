# strawberry-chemist

Explicit GraphQL types. Smart SQLAlchemy loading, no N+1 anywhere.

- mapped fields
- computed fields
- scoped relationships
- queryable connections
- filters and ordering
- relay IDs
- node lookup
- selection-aware dataloading

`strawberry-chemist` is a Strawberry + SQLAlchemy integration for applications
that want explicit GraphQL types instead of whole-schema autogeneration.

That explicitness is intentional. You decide what your GraphQL DTOs look like,
which fields exist, how relationships are exposed, and where client-controlled
querying is allowed. The package focuses on reducing boilerplate around that
work, not hiding it. That makes the public contract easier to reason about,
easier to adapt over time, and easier to keep production-safe.

That does not come at the cost of naive loading. Chemist-managed relationship
and connection fields are selection-aware and dataloader-backed, so explicit
DTOs do not force per-parent N+1 behavior.

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

## Where to go next

- start with [Getting Started](getting-started.md)
- browse the [API Surface](api-surface.md)
- use the runnable [Examples](examples.md) as acceptance targets
