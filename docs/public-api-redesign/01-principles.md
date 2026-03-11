# Principles

## 1. Explicit Types Stay

The package should continue to require explicit Strawberry type classes.

Good:

```python
@sc.node(model=Book)
class BookNode:
    title: str
    year: int
```

Not a goal:

```python
BookNode = sc.generate_type(Book)
```

Reasoning:

- explicit types are easier to review
- application code stays close to GraphQL behavior
- production schemas usually need hand-authored naming, nullability, and custom fields anyway

## 2. Convenience At The Field Level, Not The Schema Level

Autogenerating scalar field mapping is good.
Autogenerating full type trees, CRUD, or mutation contracts is not a core goal.

Good:

```python
@sc.node(model=Book)
class BookNode:
    title: strawberry.auto
    published_at: strawberry.auto
```

Not a core goal:

- model-to-schema generation for every relationship automatically
- mutation generation
- full filter/order generation without explicit user declaration

## 3. Computed Fields Must Feel Like Normal Python

`post_processor` is powerful but shaped like an internal hook, not a public API.

The public API should prefer decorated functions whose parameters describe the loaded data.

Target style:

```python
@sc.field(select=["year"])
def years_since_published(self, year: int) -> int:
    return CURRENT_YEAR - year
```

This should replace:

```python
years_since_published: int = sc.field(
    sqlalchemy_name="year",
    post_processor=lambda source, result: CURRENT_YEAR - result,
)
```

## 4. Public API Names Should Describe Intent, Not Internals

Prefer names like:

- `attr`
- `field`
- `relationship`
- `connection`
- `filter`
- `order`
- `node`
- `extensions`

Avoid exposing names centered on internal implementation classes:

- `StrawberrySQLAlchemyField`
- `StrawberrySQLAlchemyCursorPagination`
- `ConnectionLoader`
- `RuntimeFilter`

## 5. Selection-Aware Loading Is A Core Feature

This package is meaningfully stronger than shallower integrations because it understands:

- parent-side extra fields
- relationship-side selected fields
- connection-specific loading and pagination
- computed fields that still avoid N+1 behavior

That should remain a defining capability, not an accidental implementation detail.

## 6. Escape Hatches Are Required

The polished API should cover the common path.
It must also provide explicit low-level hooks for unusual production cases.

Examples of necessary escape hatches:

- custom SQLAlchemy expressions in filters
- custom order expressions that alter joins
- custom node ID encoding/decoding
- full relationship loading when selection-based loading is not enough

## 7. Stable Surface, Narrower Surface

The standalone package should expose less than the original internal bridge did.

Public surface should be small and documented.
Everything else should be treated as internal support code.

## 8. Schema Context Should Be A Protocol, Not A Framework Class

Users should not have to subclass a mostly-empty context type just to satisfy the library.

The public contract should be minimal:

```python
class MyContext:
    @asynccontextmanager
    async def get_session(self) -> AsyncIterator[AsyncSession]:
        ...
```

If the package ships a helper context class, it should be convenience-only.

## 9. Relay Is Optional

Relay helpers are important, but they should remain opt-in.
The package should not force every user into relay naming, node fields, or encoded IDs.

## 10. API Maturity Means Deprecation Discipline

The redesign should be shipped with:

- clear aliases for one migration cycle
- deprecation warnings on old names
- migration examples, not just replacement tables
