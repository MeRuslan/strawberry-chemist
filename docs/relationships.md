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
def publication_labels(self, books: list["Book"]) -> list[str]:
    return [f"{book.title} ({book.year})" for book in books]
```

Use `load="full"` when the computation needs full related rows instead of only
selected columns.

If clients need filtering, ordering, or pagination on a related collection,
switch from `sc.relationship(...)` to `sc.connection(...)` on that same
relationship source.

Primary example:

- [`examples/v0_2_api/02_relationships`](https://github.com/MeRuslan/strawberry-chemist/tree/main/examples/v0_2_api/02_relationships)
