# Types And Fields

Chemist keeps explicit Strawberry classes at the center of the API.

## Direct mapping

When the GraphQL field name matches the SQLAlchemy attribute, just annotate it:

```python
@sc.type(model=BookModel)
class Book:
    title: str
```

Use `sc.attr(...)` when the GraphQL field should be renamed:

```python
@sc.type(model=BookModel)
class Book:
    published_year: int = sc.attr("year")
```

## Computed fields

Use `@sc.field(select=[...])` when the field is computed from parent data:

```python
@sc.type(model=BookModel)
class Book:
    @sc.field(select=["title", "isbn"])
    def title_with_isbn(self, title: str, isbn: str) -> str:
        return f"{title} ({isbn})"
```

That keeps the DTO explicit and keeps required model data visible at the field
definition site.
Selected resolver params are hidden from the GraphQL schema. Any other resolver
params you declare stay public GraphQL arguments.

If the resolver parameter names should differ from the selected model field
paths, pass a mapping instead:

```python
@sc.type(model=BookModel)
class Book:
    @sc.field(select={"title": "book_title", "isbn": "book_isbn"})
    def title_with_isbn(self, book_title: str, book_isbn: str) -> str:
        return f"{book_title} ({book_isbn})"
```

## Node types

Use `sc.Node` when the type participates in relay/node resolution:

```python
@sc.type(model=BookModel)
class Book(sc.Node):
    title: str
```

Override the default primary-key relay ID only when needed:

```python
@sc.type(model=BookmarkModel)
class Bookmark(sc.Node):
    id = sc.node_id(ids=("user_id", "book_id"))
```

Primary example:

- [`examples/01_types_and_fields`](https://github.com/MeRuslan/strawberry-chemist/tree/main/examples/01_types_and_fields)
- [`examples/04_nodes_and_relay_ids`](https://github.com/MeRuslan/strawberry-chemist/tree/main/examples/04_nodes_and_relay_ids)
