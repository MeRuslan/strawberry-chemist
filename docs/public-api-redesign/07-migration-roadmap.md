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
- filters and ordering get a proper declarative DSL plus explicit manual helpers for schema-preserving migrations
- relay IDs become configurable and readable by default

## 2. Recommended Release Phases

### Phase 1: Ship The New Surface

Ship these new APIs first:

- `attr`
- `node`
- `relationship`
- `connection`
- `filter` / `filter_field`
- `order` / `order_field`
- `manual_filter` / `manual_order`
- `node` / `node_field`
- `extensions`

### Phase 2: Migrate Internal And Consumer Usage

Move package docs, examples, and downstream applications onto:

- `relationship`
- `connection`
- `manual_filter` / `manual_order`
- `extensions`

Keep explicit migration examples for:

- `post_processor`
- `relation_field`
- `relay_connection_field`
- `limit_offset_connection_field`
- `RuntimeFilter`
- `StrawberrySQLAlchemyFilter`
- `StrawberrySQLAlchemyOrdering`
- `NodeEdge`
- `extentions`

### Phase 3: Surface Freeze

At 1.0, the documented public API should be the new one only.
Names outside that surface should be removed instead of lingering as semi-supported aliases.

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
subscribers_filter = StrawberrySQLAlchemyFilter(
    input_type=SubInput,
    input_filter_map={...},
    required=True,
)
```

### Target

```python
subscribers_filter = sc.manual_filter(
    input=SubInput,
    required=True,
    apply=lambda stmt, value, ctx: ...,
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

### Current

```python
review_order = StrawberrySQLAlchemyOrdering(
    input_type=ReviewOrder,
    resolve_ordering_map={...},
)
```

### Target

```python
review_order = sc.manual_order(
    input=ReviewOrder,
    name="order",
    apply=lambda stmt, value, ctx: ...,
)
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
3. add `connection` unification
4. add new filter DSL
5. add new ordering DSL plus manual filter/order escape hatches
6. add `@node(model=...)` with primary-key defaults and readable default codec
7. remove old names from the public surface
8. rewrite examples and README around the new surface

## 6. Acceptance Criteria For A Stable API

Before calling the redesigned API stable, the package should have:

- short example docs for every public concept
- migration examples from the old API
- tests for decorated computed fields with extra selected fields
- tests for relationship-backed computed fields
- tests for generated filter operator inputs
- tests for multiple ordering clauses
- tests for manual filters and manual orders with custom input shapes
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
