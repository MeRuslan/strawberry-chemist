# Relationships

Use `sc.relationship(...)` when you want a related field to stay relationship
aware and selection-aware.

Chemist-managed relationship fields are loaded through the package dataloader
stack, so they do not degrade into one SQL query per parent object.

The API is intentionally flexible enough to cover:

- direct related fields
- renamed relationships
- server-scoped relationships
- relationship-backed computed fields
- parent-aware relationship transforms via `parent_select=...`
- full-row loading when a computation needs it

## Simple relationship

```python
@sc.type(model=AuthorModel)
class Author:
    books: list["Book"]
```

If the names line up, no helper is needed.

## Renamed relationship

```python
@sc.type(model=AuthorModel)
class Author:
    published_books: list["Book"] = sc.relationship("books")
```

## Scoped relationship

```python
classic_books: list["Book"] = sc.relationship(
    "books",
    where=lambda: BookModel.year < 1960,
)
```

## Relationship-backed computed field

```python
@sc.relationship("books", select=["title", "year"])
def publication_labels(
    self,
    books: list[BookModel],
) -> list[str]:
    return [f"{book.title} ({book.year})" for book in books]
```

The loaded relationship value is injected into the resolver parameter whose
name matches the effective relationship source. It is a hidden runtime value,
not a public GraphQL argument. Any other resolver params you declare stay
public GraphQL arguments.

By default, the hidden injected resolver parameter uses the relationship
`source` name. If you want a different Python parameter name, set
`source_param_name=` explicitly.

```python
@sc.relationship("books", source_param_name="loaded_books", load="full")
def publication_labels(
    self,
    loaded_books: list[BookModel],
) -> list[str]:
    return [f"{book.title} ({book.year})" for book in loaded_books]
```

Use `parent_select=` when the computation also needs parent-row attributes that
are not otherwise selected.

```python
@sc.relationship("books", select=["title"], parent_select=["name"])
def labeled_books(
    self,
    books: list[BookModel],
) -> list[str]:
    return [f"{self.name}: {book.title}" for book in books]
```

The split is deliberate:

- `select=` loads child-row fields from the related model
- `parent_select=` loads extra parent-row fields from `self` / `root`

Use `load="full"` when the computation needs full related rows instead of only
selected columns.

If clients need filtering, ordering, or pagination on a related collection,
switch from `sc.relationship(...)` to `sc.connection(...)` on that same
relationship source.

Primary example:

- [`examples/02_relationships`](https://github.com/MeRuslan/strawberry-chemist/tree/main/examples/02_relationships)
