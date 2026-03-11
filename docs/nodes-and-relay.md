# Nodes And Relay IDs

Use `@sc.node(model=...)` to register a GraphQL type as a relay/node type.

## Basic node

```python
@sc.node(model=BookModel)
class Book:
    title: str
```

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
```

You can also narrow the field to specific node types with
`sc.node_field(allowed_types=(Book,))`.

## Node ID codecs

The default IDs are readable, for example `Book_1`.

If an application needs a different token format, `@sc.node(...)` also supports
an explicit codec.

Primary example:

- [`examples/v0_2_api/04_nodes_and_relay_ids`](https://github.com/MeRuslan/strawberry-chemist/tree/main/examples/v0_2_api/04_nodes_and_relay_ids)

## Resolver node injection

Use `sc.node_lookup(...)` when a query or mutation should accept a node ID
argument but operate on the loaded ORM object.

```python
@sc.node_lookup(model=PostModel, id_name="post_id", node_param_name="post")
async def rename_post(self, info, post, title: str) -> Post:
    ...
```

Primary example:

- [`examples/v0_2_api/07_node_lookup_and_permissions`](https://github.com/MeRuslan/strawberry-chemist/tree/main/examples/v0_2_api/07_node_lookup_and_permissions)
