# Nodes And Relay IDs

Use a normal Chemist type plus an explicit `sc.Node` base when the GraphQL type
participates in relay/node resolution.

## Basic node

```python
@sc.type(model=BookModel)
class Book(sc.Node):
    title: str
```

By default, Chemist infers the identifier columns from the SQLAlchemy mapper
primary key.

## Custom identifiers

```python
@sc.type(model=BookmarkModel)
class Bookmark(sc.Node):
    id = sc.node_id(ids=("user_id", "book_id"))
    created_at: datetime
```

Composite IDs are supported.

## Root node lookup

```python
@strawberry.type
class Query:
    node = sc.node_field()

sc.configure(
    default_pagination=sc.CursorPagination(default_limit=10, max_limit=20),
    default_relay_id_codec=sc.relay.IntRegistryCodec(registry={BookModel: 1}),
)

schema = strawberry.Schema(
    query=Query,
    types=(Book, Bookmark),
    extensions=sc.extensions(),
)
```

You can also narrow the field to specific node types with
`sc.node_field(allowed_types=(Book,))`.

When an unrestricted `sc.node_field()` is present, the concrete node types must
already be visible to the schema at build time, either through normal field
reachability or through `types=(...)`.

Call `sc.configure(...)` before `strawberry.Schema(...)` when an application
wants package-level defaults such as relay codecs or connection pagination.

## Node ID codecs

The default IDs are readable, for example `Book_1`.

If an application needs a different token format, configure it on the node ID
field:

```python
@sc.type(model=LegacyBookmarkModel)
class LegacyBookmark(sc.Node):
    id = sc.node_id(
        codec=sc.relay.IntRegistryCodec(registry={LegacyBookmarkModel: 7}),
    )
```

Or set a package-level default before building the schema:

```python
sc.configure(
    default_relay_id_codec=sc.relay.IntRegistryCodec(
        registry={BookModel: 1, ShelfModel: 2},
    )
)
```

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
