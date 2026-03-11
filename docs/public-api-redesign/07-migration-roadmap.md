# Migration And Delivery Roadmap

## 1. Public API Direction

This redesign is evolutionary in runtime capability, but revolutionary in surface shape.

What stays:

- explicit schema types
- auto scalar mapping
- selection-aware relation loading
- pragmatic SQLAlchemy-first behavior

What changes:

- `post_processor` -> decorated functions
- field helpers become more specialized and intention-revealing
- filters and ordering get a proper declarative DSL
- relay IDs become configurable and readable by default

## 2. Recommended Release Phases

### Phase 1: Add The New Surface Beside The Old One

Ship these new APIs first:

- `attr`
- `node`
- `relationship`
- `connection`
- `filter` / `filter_field`
- `order` / `order_field`
- `node` / `node_field`
- `extensions`

Keep the current APIs working.

### Phase 2: Deprecation Warnings

Deprecate with warnings:

- `post_processor`
- `relation_field`
- `relay_connection_field`
- `limit_offset_connection_field`
- `RuntimeFilter`
- `StrawberrySQLAlchemyFilter`
- `StrawberrySQLAlchemyOrdering`
- `NodeEdge`
- `extentions`

### Phase 3: 1.0 Surface Freeze

At 1.0, the documented public API should be the new one only.
Compatibility aliases can remain temporarily, but docs and examples should stop using them.

## 3. Migration Examples

### Current

```python
title_with_isbn: str = sc.field(
    sqlalchemy_name="title",
    additional_parent_fields=["isbn"],
    post_processor=lambda source, result: f"{source.title} ({source.isbn})",
)
```

### Target

```python
@sc.field(select=["title", "isbn"])
def title_with_isbn(self, title: str, isbn: str) -> str:
    return f"{title} ({isbn})"
```

### Current

```python
books_before_1960: list[BookNode] = sc.relation_field(
    sqlalchemy_name="books",
    pre_filter=RuntimeFilter([lambda: Book.year < 1960]),
)
```

### Target

```python
books_before_1960: list[BookNode] = sc.relationship(
    "books",
    where=lambda: Book.year < 1960,
)
```

### Current

```python
books: RelayConnection[BookNode] = sc.relay_connection_field(order=book_order)
```

### Target

```python
books: sc.Connection[BookNode] = sc.connection(order=BookOrder)
```

### Current

```python
book_order = StrawberrySQLAlchemyOrdering(
    input_type=BookOrderInput,
    resolve_ordering_map={...},
)
```

### Target

```python
@sc.order(model=Book)
class BookOrder:
    year = sc.order_field()
    title = sc.order_field()
```

## 4. What To Explicitly Defer

These areas should be called experimental or omitted until there is a clean story:

- write/mutation helpers
- model-derived input generation
- generic sync session support
- auto-generated GraphQL CRUD

The current `input()` and `mutation()` helpers are too underdefined to present as mature public API.

## 5. Implementation Order

Recommended implementation order inside the codebase:

1. add `extensions` spelling-safe module and top-level helper
2. add `attr`, new `field`, and `relationship` APIs
3. add `connection` unification while keeping aliases
4. add new filter DSL
5. add new ordering DSL
6. add `@node(model=...)` with primary-key defaults and readable default codec
7. deprecate old names
8. rewrite examples and README around the new surface

## 6. Acceptance Criteria For A Stable API

Before calling the redesigned API stable, the package should have:

- short example docs for every public concept
- migration examples from the old API
- tests for decorated computed fields with extra selected fields
- tests for relationship-backed computed fields
- tests for generated filter operator inputs
- tests for multiple ordering clauses
- tests for non-`id` node identifiers
- tests for composite identifiers
- tests for readable default relay IDs
- tests for optional int-registry relay codec

## 7. Final Recommendation

Treat the current package as proof of runtime capability, not as proof of ideal public shape.

The redesign should preserve the package's production strengths while making the public contract:

- smaller
- more explicit
- more Pythonic
- less hook-oriented
- less coupled to internals
- more obviously stable to outside users
