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
- `EnumFilter[T]`

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

## 4. Custom Filter Escape Hatch

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
- current SQLAlchemy statement

## 5. Proposed Ordering API

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

## 6. Custom Order Escape Hatch

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

## 7. Connections Should Be Unified

The package should expose one connection builder, not separate top-level helpers split by pagination style.

### Relationship Connection

```python
books: sc.Connection[BookNode] = sc.connection(
    filter=BookFilter,
    order=BookOrder,
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

## 8. Pagination Configuration

The public surface should not require users to construct pagination implementation classes.

Recommended policy objects:

```python
books: sc.Connection[BookNode] = sc.connection(
    pagination=sc.CursorPagination(max_limit=50),
)
```

```python
books: sc.OffsetConnection[BookNode] = sc.connection(
    pagination=sc.OffsetPagination(default_limit=20, max_limit=100),
)
```

Default recommendation:

- cursor pagination for `sc.Connection`
- limit-offset as explicit opt-in

## 9. `where=` On Connections

Connection fields need the same scoped filtering concept as relationships.

```python
books: sc.Connection[BookNode] = sc.connection(
    where=lambda: Book.visible == True,
    filter=BookFilter,
    order=BookOrder,
)
```

This replaces the current rough split between `pre_filter`, filter objects, and loader-specific connection hooks.

## 10. What The Public API Should Hide

The package should continue using internal dataloaders and query strategies, but users should not have to know about:

- `ConnectionLoader`
- `ValuesLoadingStrategy`
- `UnionLoadingStrategy`
- tuple-ized filter/order/pagination cache keys
