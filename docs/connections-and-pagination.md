# Connections And Pagination

`sc.connection(...)` is the collection field entrypoint for both root fields and
relationship-backed collections.

Like relationship fields, Chemist-managed connection fields are selection-aware
and dataloader-backed. The point is to let you expose rich root and nested
collections without hand-building anti-N+1 plumbing.

Connections are also intentionally flexible. The same API covers:

- root collections
- relationship-backed collections
- server-scoped collections with `where=...`
- server-owned default ordering with `default_order_by=...`
- parent-aware nested connections with `parent_select=...`
- filter and order arguments
- flat pagination arguments
- nested `pagination:` input objects for compatibility-sensitive schemas

## Root connection

```python
@strawberry.type
class Query:
    books: sc.Connection[Book] = sc.connection(
        filter=BookFilter,
        order=BookOrder,
        pagination=sc.CursorPagination(max_limit=20),
    )
```

## Relationship-backed connection

```python
@sc.type(model=AuthorModel)
class Author:
    books: sc.Connection[Book] = sc.connection(
        source="books",
        filter=BookFilter,
        order=BookOrder,
    )
```

Use `parent_select=` when a nested connection resolver needs parent-row fields
in addition to the paginated related collection.

```python
@sc.connection(source="books", parent_select=["name"])
def books_for_author(
    self,
    loaded_connection: sc.Connection[BookModel],
) -> sc.Connection[Book]:
    if self.name:
        return loaded_connection
    return loaded_connection
```

The injected resolver argument is a hidden runtime value, not a GraphQL input.
For connections, that runtime value is the loaded connection wrapper whose nodes
are still ORM rows.

As with relationships, the split is:

- `parent_select=` for extra fields on the parent row
- `where=`, `filter=`, `order=`, `default_order_by=`, and `pagination=`
  for the child collection

`parent_select=` only applies to relationship-backed connections. Root
connections should not declare it.

## Scoped connection

```python
@strawberry.type
class Query:
    visible_books: sc.Connection[Book] = sc.connection(
        where=lambda: BookModel.visible.is_(True),
    )
```

`where=` applies server-owned SQLAlchemy predicates before any client-provided
filter or ordering inputs.

## Default server ordering

```python
@strawberry.type
class Query:
    ranked_books: sc.Connection[Book] = sc.connection(
        where=lambda: BookModel.visible.is_(True),
        default_order_by=(BookModel.ranking.desc(), BookModel.title.asc()),
    )
```

Use `default_order_by=` when a connection should have a stable server-owned
sort even when no `order=` argument is exposed or when the client does not pass
`orderBy:`.

## Pagination policies

Built-in policies:

- `sc.CursorPagination(...)`
- `sc.OffsetPagination(...)`

They both implement `sc.PaginationPolicy`.

Flat argument style:

```python
sc.connection(pagination=sc.CursorPagination(max_limit=20))
```

GraphQL:

```graphql
books(first: 20, after: "...")
```

Nested argument style:

```python
sc.connection(pagination=sc.CursorPagination(max_limit=20, nested=True))
```

GraphQL:

```graphql
books(pagination: { first: 20, after: "..." })
```

The nested style is especially useful when an existing client contract already
uses a `pagination:` input object.

Primary examples:

- [`examples/03_connections_filters_and_ordering`](https://github.com/MeRuslan/strawberry-chemist/tree/main/examples/03_connections_filters_and_ordering)
- [`examples/08_nested_pagination_arguments`](https://github.com/MeRuslan/strawberry-chemist/tree/main/examples/08_nested_pagination_arguments)
