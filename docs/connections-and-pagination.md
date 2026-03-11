# Connections And Pagination

`sc.connection(...)` is the collection field entrypoint for both root fields and
relationship-backed collections.

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

- [`examples/v0_2_api/03_connections_filters_and_ordering`](https://github.com/MeRuslan/strawberry-chemist/tree/main/examples/v0_2_api/03_connections_filters_and_ordering)
- [`examples/v0_2_api/08_nested_pagination_arguments`](https://github.com/MeRuslan/strawberry-chemist/tree/main/examples/v0_2_api/08_nested_pagination_arguments)
