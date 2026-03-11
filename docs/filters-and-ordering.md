# Filters And Ordering

Chemist supports both a declarative DSL and manual schema-preserving helpers.

## Declarative filter DSL

```python
@sc.filter(model=BookModel)
class BookFilter(sc.FilterSet):
    title: sc.StringFilter = sc.filter_field()
    year: sc.IntFilter = sc.filter_field()
    author_name: sc.StringFilter = sc.filter_field(path="author.name")
```

Use `apply=` on `sc.filter_field(...)` when a field needs custom SQL shaping.

## Declarative ordering DSL

```python
@sc.order(model=BookModel)
class BookOrder:
    year = sc.order_field()
    author_name = sc.order_field(path="author.name")
```

Use `resolve=` on `sc.order_field(...)` when ordering needs custom joins or
expressions.

## Manual helpers

When the GraphQL input shape itself must stay custom, use:

- `sc.manual_filter(...)`
- `sc.manual_order(...)`

```python
legacy_filter = sc.manual_filter(
    input=LegacyFilterInput,
    required=True,
    apply=lambda stmt, value, ctx: ...,
)

legacy_order = sc.manual_order(
    input=LegacyOrderInput,
    name="order",
    apply=lambda stmt, value, ctx: ...,
)
```

That keeps the collection field on `sc.connection(...)` while letting the
application own the public `filter:` and `order:` contracts exactly.

Primary examples:

- [`examples/v0_2_api/03_connections_filters_and_ordering`](https://github.com/MeRuslan/strawberry-chemist/tree/main/examples/v0_2_api/03_connections_filters_and_ordering)
- [`examples/v0_2_api/06_manual_filters_and_orders`](https://github.com/MeRuslan/strawberry-chemist/tree/main/examples/v0_2_api/06_manual_filters_and_orders)
