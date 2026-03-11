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

## Node types

Use `@sc.node(model=...)` when the type participates in relay/node resolution:

```python
@sc.node(model=BookModel)
class Book:
    title: str
```

Primary example:

- [`examples/01_types_and_fields`](https://github.com/MeRuslan/strawberry-chemist/tree/main/examples/01_types_and_fields)
- [`examples/04_nodes_and_relay_ids`](https://github.com/MeRuslan/strawberry-chemist/tree/main/examples/04_nodes_and_relay_ids)
