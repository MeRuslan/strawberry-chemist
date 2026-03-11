# Fields And Relationships

## Surface Split

The redesigned field surface should be split into three concepts:

- `attr(...)`: direct mapped field or alias
- `@field(...)`: computed field from selected parent data
- `relationship(...)` / `@relationship(...)`: relationship-backed field or computed relationship field

That split removes the current overload where one helper handles raw mapping, transforms, and relation behavior through a pile of options.

## 1. Direct Mapped Fields

### Matching Name

```python
@sc.type(model=Book)
class BookNode:
    title: str
    year: strawberry.auto
```

### Renamed GraphQL Field

```python
@sc.type(model=User)
class UserNode:
    display_name: str = sc.attr("username_to_display")
```

### When `attr(...)` Should Exist

Use `attr(...)` when the field is still fundamentally a direct attribute mapping.
Do not require a decorated function just to rename a model attribute.

## 2. Computed Scalar Fields

### Replace `post_processor` With A Decorated Function

Target API:

```python
@sc.type(model=Book)
class BookNode:
    title: str

    @sc.field(select=["year"])
    def years_since_published(self, year: int) -> int:
        return CURRENT_YEAR - year
```

This is the same capability as current `post_processor`, but expressed as a normal function.

### Extra Parent Fields

```python
@sc.type(model=Book)
class BookNode:
    @sc.field(select=["title", "isbn"])
    def title_with_isbn(self, title: str, isbn: str) -> str:
        return f"{title} ({isbn})"
```

This should replace:

```python
title_with_isbn: str = sc.field(
    sqlalchemy_name="title",
    additional_parent_fields=["isbn"],
    post_processor=lambda source, result: f"{source.title} ({source.isbn})",
)
```

## 3. Field Parameter Injection Contract

For decorated field functions, the contract should be explicit and stable.

### Proposed Rules

- `self` or `root` is the ORM source object.
- `info` is injected if present in the signature.
- every other parameter must be satisfied from `select=[...]`.
- parameter matching is by name, not by position.
- schema build should fail if a required parameter cannot be supplied.

Example:

```python
@sc.field(select=["title", "isbn"])
def label(self, title: str, isbn: str, info: Info) -> str:
    return f"{title} ({isbn})"
```

## 4. Relationship Fields

### Simple Relationship

```python
@sc.type(model=Book)
class BookNode:
    author: AuthorNode | None
```

When the GraphQL field name matches the SQLAlchemy relationship and the return type is another Chemist type, no helper is needed.

### Renamed Relationship

```python
related_books: list[BookNode] = sc.relationship("books")
```

### Scoped Relationship

`pre_filter` should become `where=`.

```python
classic_books: list[BookNode] = sc.relationship(
    "books",
    where=lambda: Book.year < 1960,
)
```

For multiple conditions:

```python
the_late_books: list[BookNode] = sc.relationship(
    "books",
    where=[
        lambda: Book.year > 1960,
        lambda: Book.title.like("The %"),
    ],
)
```

## 5. Relationship-Backed Computed Fields

This is one of the package's strongest capabilities and should become first-class.

```python
@sc.type(model=Person)
class PersonNode:
    @sc.relationship("books", select=["year"])
    def book_years(self, books: list[Book]) -> list[int]:
        return [book.year for book in books]
```

Binary transform example:

```python
@sc.relationship("books", load="full")
def binary_years(self, books: list[Book]) -> list[BinaryYear]:
    return [BinaryYear(binary_year=f"{book.year:b}") for book in books]
```

## 6. `load="selected"` vs `load="full"`

Current `ignore_field_selections=True` is an internal name leaking outward.
The public API should use a direct behavior switch.

- `load="selected"`: default; only fetch what the target field needs
- `load="full"`: fetch the related rows without selection-based restriction

## 7. Root Query Fields

Chemist should not try to replace normal Strawberry resolvers for one-off root fields.
This stays good:

```python
@strawberry.type
class Query:
    @strawberry.field
    async def book_by_title(self, info: Info[Ctx, None], title: str) -> BookNode | None:
        async with info.context.get_session() as session:
            ...
```

The package's opinionated root-field support should focus on collections and node lookup, not every possible resolver.

## 8. Proposed Implementation Boundary

Public code should talk in terms of:

- selected parent fields
- relationship source name
- query scope (`where`)
- load mode

It should not talk in terms of:

- `post_processor`
- `needs_fields`
- `additional_parent_fields`
- `ignore_field_selections`
- internal field subclasses
