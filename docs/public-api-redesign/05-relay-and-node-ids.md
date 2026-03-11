# Relay And Node IDs

## 1. Relay Should Stop Assuming `model.id`

The stable API must support:

- a non-`id` primary identifier
- composite identifiers
- custom string identifiers
- optional compact model registry encoding

The current hardcoded `model.id` assumption is too narrow for a public package.

## 2. Proposed Node Decorator API

The preferred relay API should be a dedicated decorator:

```python
@sc.node(model=Book)
class BookNode:
    title: str
```

That should be enough for the common case.

Default behavior:

- infer ID fields from the SQLAlchemy mapper primary key columns, in mapper order
- if the model has a single `id` primary key, that naturally becomes the default
- if the model has a composite primary key, use all PK columns
- if the model cannot produce a stable identifier set, raise at schema build

Override only when the default is not what you want.

Natural key example:

```python
@sc.node(model=Book, ids=("slug",))
class BookNode:
    title: str
```

Composite key example:

```python
@sc.node(model=Membership, ids=("user_id", "organization_id"))
class MembershipNode:
    role: str
```

Custom display name example:

```python
@sc.node(model=Book, name="Book", ids=("slug",))
class BookNode:
    ...
```

This is materially better than forcing every node type through:

```python
@sc.type(model=Book, node=sc.node(...))
class BookNode(sc.Node):
    ...
```

## 3. Default Relay ID Format

Recommended default format:

```python
f"{node_name}_{id_str}"
```

Where:

- `node_name` defaults to the GraphQL node type name
- `id_str` is the serialized configured identifier payload

Examples:

```text
Book_123
Book_slug-the-hobbit
Membership_12,34
```

## 4. Composite ID Serialization

For composites, the package should serialize the configured identifier fields in declaration order.

Example:

```python
@sc.node(model=Invoice, ids=("country_code", "number"))
class InvoiceNode:
    ...
```

Possible resulting token:

```text
Invoice_RU,1024
```

The serializer should URL-escape each component before joining, so commas and separators remain safe.

## 5. Parsing Strategy Must Not Be Naive

The parser should not rely on a dumb `split("_", 1)` against arbitrary model names.
It should parse against the registered node configuration.

Recommended rule:

- node lookup first resolves the node prefix against known node names
- the remainder is decoded through the configured codec

That makes the human-readable default viable without brittle string parsing.

## 6. Optional Compact Codec

The current model-to-int bijection can remain valuable, but it should become optional.

Recommended codec surface:

```python
@sc.node(
    model=Book,
    codec=sc.relay.IntRegistryCodec(registry={Book: 1, Author: 2}),
)
class BookNode:
    ...
```

Default should be the readable string codec.
Compact registry encoding should be opt-in.

## 7. Custom Codec Protocol

There should be a stable codec protocol for advanced users.

```python
class RelayIdCodec(Protocol):
    def encode(self, node_name: str, values: tuple[str, ...]) -> str: ...
    def decode(self, token: str) -> tuple[str, tuple[str, ...]]: ...
```

This lets applications choose their own tradeoff between readability, compactness, and compatibility.

## 8. Optional `sc.Node` Base

The package may still expose `sc.Node`, but it should not be required in the normal path.

Recommended usage:

```python
@sc.node(model=Book)
class BookNode:
    ...
```

Compatibility usage:

```python
@sc.node(model=Book)
class BookNode(sc.Node):
    ...
```

If `sc.Node` remains, treat it as a compatibility or explicit-interface marker, not as the primary API.

## 9. Root Node Field

`NodeEdge` should not be the long-term public relay root story.

Recommended root field:

```python
@strawberry.type
class Query:
    node = sc.node_field()
```

Optional restricted node field:

```python
book = sc.node_field(allowed_types=(BookNode,))
```

Node registration should come from `@sc.node(...)` types automatically.

## 10. Node Lookup Should Use Configured IDs

When a node is looked up, the package should build the SQLAlchemy predicate from the declared identifiers.

Single field:

```python
Book.slug == decoded_slug
```

Composite field:

```python
and_(
    Membership.user_id == decoded_user_id,
    Membership.organization_id == decoded_org_id,
)
```

No hardcoded `.id` access in the public relay implementation.

## 11. Keep Relay Optional

Users who do not need relay should still be able to use:

- `@sc.type(model=...)`
- `sc.field`
- `sc.relationship`
- `sc.connection`
- `@sc.filter`
- `@sc.order`

without inheriting from `sc.Node` or configuring node codecs.
