# Nodes And Relay IDs

Use `@sc.node(model=...)` to register a GraphQL type as a relay/node type.

## Basic node

```python
@sc.node(model=BookModel)
class Book:
    title: str
```

Chemist automatically makes the type implement `sc.Node`, so an explicit
`sc.Node` base class is optional.

By default, Chemist infers the identifier columns from the SQLAlchemy mapper
primary key.

## Custom identifiers

```python
@sc.node(model=BookmarkModel, ids=("user_id", "book_id"))
class Bookmark:
    created_at: datetime
```

Composite IDs are supported.

## Root node lookup

```python
@strawberry.type
class Query:
    node = sc.node_field()

schema = sc.relay.configure(
    strawberry.Schema(query=Query, extensions=sc.extensions())
)
```

You can also narrow the field to specific node types with
`sc.node_field(allowed_types=(Book,))`.

When an unrestricted `sc.node_field()` is present, call
`sc.relay.configure(schema)` after creating the Strawberry schema so the `Node`
interface knows which concrete node types belong to that schema.

## Node ID codecs

The default IDs are readable, for example `Book_1`.

If an application needs a different token format, `@sc.node(...)` also supports
an explicit codec.

If many node types should share the same default codec, configure it on the
schema:

```python
schema = strawberry.Schema(query=Query, extensions=sc.extensions())
schema = sc.relay.configure(
    schema,
    default_codec=sc.relay.IntRegistryCodec(registry={BookModel: 1}),
)
```

Per-node `codec=` still overrides the schema default.

Call `sc.relay.configure(schema, ...)` as the schema finalization step whenever
you use an unrestricted `sc.node_field()` or want a schema-wide default codec.

For application code and tests, use the schema-bound helpers instead of
hardcoding token strings:

```python
book_id = sc.relay.encode_node_id(schema, Book, values=(1,))
decoded = sc.relay.decode_node_id(schema, book_id)
assert decoded.node_type is Book
assert decoded.values == ("1",)
```

Primary example:

- [`examples/04_nodes_and_relay_ids`](https://github.com/MeRuslan/strawberry-chemist/tree/main/examples/04_nodes_and_relay_ids)

## Resolver node injection

Use `sc.node_lookup(...)` when a query or mutation should accept a node ID
argument but operate on the loaded ORM object.

```python
@sc.node_lookup(model=PostModel, id_name="post_id", node_param_name="post")
async def rename_post(self, info, post, title: str) -> Post:
    ...
```

Primary example:

- [`examples/07_node_lookup_and_permissions`](https://github.com/MeRuslan/strawberry-chemist/tree/main/examples/07_node_lookup_and_permissions)
