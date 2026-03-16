# Node lookup and permissions

This example defines the intended ergonomics for loading a concrete ORM object
from a relay/node ID and injecting it into a resolver.

It covers:

- `sc.node_lookup(...)` on a normal query field
- `sc.node_lookup(...)` on a mutation-style field
- `sc.relay.configure(schema)` for the unrestricted root `node(id: ...)` field
- custom ID argument names such as `postId`
- field permission classes before lookup
- post-load node permission classes after lookup
- rejecting mismatched node IDs by returning `null`

Run it in place with `make test`, `make schema`, or `make serve`.
