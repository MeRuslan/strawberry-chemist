# Query Cost Limits

A depth limit doesn't stop a short query from asking for a lot: three nested
connections of 40 nodes each are 64 000 rows in a dozen lines. Chemist knows how
large every `sc.connection` page can get, so it can work out an operation's
worst case before running it, and reject operations over a limit.

## The estimate

`sc.estimate_query_cost(schema, document, operation_name=None, variables=None)`
returns a `QueryCost`:

- `objects`: how many GraphQL objects (every `{...}` in the response, each list
  item separately) the operation may return
- `fields`: how many fields it may resolve, leaves included

Both are upper bounds, counted like this:

- a connection's page is as large as its arguments ask, capped the way its
  pagination policy caps it (`max_limit`, the nested input's limit of 40); the
  page size multiplies everything selected under `edges` / `items`
- a plain list field counts `default_list_size` items (1 unless you pass
  another), unless it has a cost hint
- fields asked twice under one response key are counted once, aliases each
- a union or interface selection costs as much as its most expensive member
- `@skip` / `@include` follow their condition
- `__typename` and introspection fields are free

With `variables=None` every variable is assumed at its worst (pages at
`max_limit`, conditional fields included). That suits checking a client's
documents ahead of time, say in CI:

```python
cost = sc.estimate_query_cost(schema, open("getPost.graphql").read())
assert cost.objects < 10_000
```

## Rejecting expensive operations

```python
schema = strawberry.Schema(
    query=Query,
    extensions=[
        *sc.extensions(),
        lambda: sc.QueryCostLimiter(max_objects=10_000, max_fields=50_000),
    ],
)
```

The limiter estimates every operation with its real variables after validation,
and if `max_objects` or `max_fields` is exceeded answers with one error and no
data; nothing is resolved. For

```graphql
{ authors(pagination: {first: 40}) { edges { node {
  books(pagination: {first: 40}) { edges { node { author {
    books(pagination: {first: 40}) { edges { node { title } } }
  } } } }
} } } }
```

(64 000 books at the bottom, each with its edge) the error's `extensions` are

```json
{
  "code": "QUERY_COST_EXCEEDED",
  "objects": 134521,
  "fields": 134522,
  "maxObjects": 10000,
  "maxFields": 50000
}
```

and its `original_error` is a `strawberry_chemist.query_cost.QueryCostExceeded`
with the `cost` on it.

Options:

- `dry_run=True` runs everything and logs the operations that would be rejected
  (a warning on the `strawberry_chemist.query_cost` logger): measure your
  clients before turning it on
- `callback=lambda cost, execution_context: ...` gets every operation's cost,
  for logs or metrics
- `default_list_size` as in the estimate

Strawberry builds a new extension per request from a factory (`lambda` above).
Older strawberry-graphql versions call the factory with `execution_context=`;
`functools.partial(sc.QueryCostLimiter, max_objects=10_000)` works with all of
them.

## Fields Chemist can't size

`sc.connection` fields are sized by their pagination policy. For anything else,
tell the estimate with `sc.cost(...)` in the field's metadata.

A plain list with a known bound:

```python
@strawberry.field(metadata=sc.cost(list_size=5))
def first_five_objects(self) -> list[ActivityObject]: ...
```

A resolver that pages by itself: give it the policy its arguments follow, and
its page size is worked out from the arguments like a `sc.connection`'s:

```python
@strawberry.field(
    metadata=sc.cost(pagination=sc.CursorPagination(max_limit=20, nested=True))
)
async def activity(
    self, info: Info, pagination: CursorPaginationInput
) -> sc.Connection[ActivityNode]: ...
```

The page size multiplies the list fields of the returned connection (`edges`);
on a field that returns a list itself, it's the length of that list.

`sc.relationship(...)`, `sc.connection(...)` and `sc.node_lookup(...)` take
`metadata=` too. A custom
pagination policy is sized by its `page_size(arguments)` method when it has one
(`CursorPagination` and `OffsetPagination` do), by its `max_limit` otherwise.
