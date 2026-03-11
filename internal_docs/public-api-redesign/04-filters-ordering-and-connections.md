# Filters, Ordering, And Connections

## 1. Filters Need A Public DSL, Not A Map Of Lambdas

Current filter construction is too rough for a standalone public package:

```python
book_year_filter = StrawberrySQLAlchemyFilter(
    input_type=BookAgeFilter,
    input_filter_map={...},
)
```

That API is workable internally, but it is not polished enough to become the main story.

The public filter and order story should have two lanes:

- a declarative DSL for the common case
- explicit manual helpers for preserving a hand-authored GraphQL contract

## 2. Proposed Filter API

```python
@sc.filter(model=Book)
class BookFilter(sc.FilterSet):
    title: sc.StringFilter = sc.filter_field()
    year: sc.IntFilter = sc.filter_field()
    author_name: sc.StringFilter = sc.filter_field(path="author.name")
```

### Built-In Filter Operator Types

Recommended built-ins:

- `StringFilter`
- `IntFilter`
- `FloatFilter`
- `BooleanFilter`
- `IDFilter`
- `DateFilter`
- `DateTimeFilter`

These types can expose polished operators like:

```python
@strawberry.input
class StringFilter:
    eq: str | None = None
    ne: str | None = None
    in_: list[str] | None = None
    contains: str | None = None
    startswith: str | None = None
    endswith: str | None = None
    ilike: str | None = None
    is_null: bool | None = None
```

For comparable values:

```python
@strawberry.input
class IntFilter:
    eq: int | None = None
    ne: int | None = None
    lt: int | None = None
    lte: int | None = None
    gt: int | None = None
    gte: int | None = None
    between: tuple[int, int] | None = None
    in_: list[int] | None = None
    is_null: bool | None = None
```

## 3. Logical Composition

A public filter API is incomplete without boolean composition.

Recommended base mixin:

```python
class FilterSet:
    and_: list[Self] | None = None
    or_: list[Self] | None = None
    not_: Self | None = None
```

That lets users express real production filtering without inventing custom one-off inputs.

## 4. DSL-Level Custom Filter Escape Hatch

The DSL must not block advanced cases.

```python
@sc.filter(model=Book)
class BookFilter(sc.FilterSet):
    published_after: int | None = sc.filter_field(
        apply=lambda stmt, value, ctx: stmt.where(Book.year >= value)
    )
```

Stable callback contract:

```python
def apply(stmt: Select, value: Any, ctx: sc.FilterContext) -> Select: ...
```

`FilterContext` can expose:

- `model`
- `info`
- `node_type`
- `resolve_path(stmt, path)` for join-aware path resolution

## 5. Manual Filter Escape Hatch

Some applications need to preserve an existing GraphQL input type exactly during
migration.

That should be supported directly instead of forcing the DSL to become
polymorphic.

```python
@strawberry.input
class ReviewFilterInput:
    author_id: strawberry.ID
    query: str | None = None


review_filter = sc.manual_filter(
    input=ReviewFilterInput,
    required=True,
    apply=lambda stmt, value, ctx: ...,
)
```

Recommended callback contract:

```python
def apply(stmt: Select, value: Any, ctx: sc.FilterContext) -> Select: ...
```

Recommended helper shape:

```python
sc.manual_filter(
    *,
    input: type,
    apply: Callable[[Select, Any, sc.FilterContext], Select],
    name: str = "filter",
    python_name: str | None = None,
    required: bool = False,
    default: Any = UNSET,
    validate: Callable[[Any], Any] | None = None,
    cache_key: Callable[[Any], Hashable] | None = None,
    description: str | None = None,
    model: type | None = None,
)
```

This path should allow:

- a completely hand-authored Strawberry input type
- required filter arguments
- non-standard filter field names
- schema-preserving migrations away from old helper objects

## 6. Proposed Ordering API

Current ordering is also too low-level as a public default.

Target shape:

```python
@sc.order(model=Book)
class BookOrder:
    year = sc.order_field()
    title = sc.order_field()
    author_name = sc.order_field(path="author.name")
```

This spec should generate the GraphQL order item shape for the user.

Recommended GraphQL shape:

```graphql
books(orderBy: [{ field: YEAR, direction: DESC }])
```

### Stable Order Concepts

- `field`
- `direction`
- `nulls`

Recommended enums:

- `SortDirection.ASC | DESC`
- `NullsOrder.FIRST | LAST`

## 7. DSL-Level Custom Order Escape Hatch

Some ordering requires altered joins or computed expressions.

```python
@sc.order(model=Book)
class BookOrder:
    popularity = sc.order_field(
        resolve=lambda stmt, ctx: (stmt.outerjoin(Vote), func.count(Vote.id))
    )
```

Stable callback contract:

```python
def resolve(stmt: Select, ctx: sc.OrderContext) -> tuple[Select, Any]: ...
```

## 8. Manual Order Escape Hatch

Some applications need a custom order argument shape that the DSL should not try
to generate.

```python
@strawberry.input
class ReviewOrder:
    field: ReviewOrderField
    order: ReviewOrderDirection


review_order = sc.manual_order(
    input=ReviewOrder,
    name="order",
    apply=lambda stmt, value, ctx: ...,
)
```

Recommended callback contract:

```python
def apply(stmt: Select, value: Any, ctx: sc.OrderContext) -> Select: ...
```

Recommended helper shape:

```python
sc.manual_order(
    *,
    input: type,
    apply: Callable[[Select, Any, sc.OrderContext], Select],
    name: str = "orderBy",
    python_name: str | None = None,
    required: bool = False,
    default: Any = UNSET,
    validate: Callable[[Any], Any] | None = None,
    cache_key: Callable[[Any], Hashable] | None = None,
    description: str | None = None,
    model: type | None = None,
)
```

This path should allow:

- legacy `order` arguments instead of `orderBy`
- single input objects instead of generated order item lists
- custom enums and field names
- hand-authored join and grouping behavior

## 9. Connections Should Be Unified

The package should expose one connection builder, not separate top-level helpers split by pagination style.

### Relationship Connection

```python
books: sc.Connection[BookNode] = sc.connection(
    filter=BookFilter,
    order=BookOrder,
)
```

Manual definitions should plug into the same `sc.connection(...)` entrypoint:

```python
reviews: sc.Connection[ReviewNode] = sc.connection(
    filter=review_filter,
    order=review_order,
)
```

### Root Connection

```python
@strawberry.type
class Query:
    books: sc.Connection[BookNode] = sc.connection(
        filter=BookFilter,
        order=BookOrder,
    )
```

For root fields, the package can infer the SQLAlchemy model from `BookNode`.

### Explicit Source

```python
author_books: sc.Connection[BookNode] = sc.connection(source="books")
```

## 10. Pagination Configuration

The connection field should accept a stable pagination policy object.

Built-in policies:

- `sc.CursorPagination(...)`
- `sc.OffsetPagination(...)`

Both should implement the same public `sc.PaginationPolicy` contract.

Recommended common protocol:

```python
class PaginationPolicy(Protocol):
    def get_fields_from_typed_request(
        self,
        selected_fields: list[SelectedField],
    ) -> list[SelectedField]: ...

    def cache_key(self, page: Any) -> Hashable: ...
    def paginate_query(self, query: Select, page: Any) -> Select: ...
    def paginate_result(self, result: list[Any], **kwargs: Any) -> Any: ...
```

Policies can expose arguments in either of two shapes:

- flat field-level arguments through `arguments`
- one nested input argument through `argument`

Flat cursor arguments:

```python
books: sc.Connection[BookNode] = sc.connection(
    pagination=sc.CursorPagination(max_limit=50),
)
```

GraphQL:

```graphql
books(first: 20, after: "...")
```

Nested cursor argument for migration compatibility:

```python
books: sc.Connection[BookNode] = sc.connection(
    pagination=sc.CursorPagination(max_limit=50, nested=True),
)
```

GraphQL:

```graphql
books(pagination: { first: 20, after: "..." })
```

Offset pagination follows the same pattern:

```python
books_page: sc.OffsetConnection[BookNode] = sc.connection(
    pagination=sc.OffsetPagination(default_limit=20, max_limit=100),
)

legacy_books_page: sc.OffsetConnection[BookNode] = sc.connection(
    pagination=sc.OffsetPagination(
        default_limit=20,
        max_limit=100,
        nested=True,
    ),
)
```

This keeps the default public API flat and modern while still letting migration
projects retain an existing nested `pagination:` argument without inventing a
separate manual-pagination DSL.

Default recommendation:

- cursor pagination for `sc.Connection`
- limit-offset as explicit opt-in

## 11. `where=` On Connections

Connection fields need the same scoped filtering concept as relationships.

```python
books: sc.Connection[BookNode] = sc.connection(
    where=lambda: Book.visible == True,
    filter=BookFilter,
    order=BookOrder,
)
```

This replaces the current rough split between `pre_filter`, filter objects, and loader-specific connection hooks.

## 12. What The Public API Should Hide

The package should continue using internal dataloaders and query strategies, but users should not have to know about:

- `ConnectionLoader`
- `ValuesLoadingStrategy`
- `UnionLoadingStrategy`
- tuple-ized filter/order/pagination cache keys
