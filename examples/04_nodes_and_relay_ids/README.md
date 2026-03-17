# Nodes and relay IDs

This example defines the relay ergonomics of the public API.

It covers:

- explicit `sc.Node` subclasses on normal `@sc.type(model=...)` types
- `sc.node_id(...)` for custom IDs or codecs
- schema-time `types=(...)` for unrestricted root `node(id: ...)` reachability
- default identifier inference from model primary keys
- custom identifiers for natural keys
- composite identifiers
- `sc.relay.encode_node_id(...)` and `sc.relay.decode_node_id(...)` for application code and tests
- an optional compact codec for legacy or integration-sensitive environments

The readable default token shape assumed here is `"<NodeName>_<serialized ids>"`.

Run it in place with `make test`, `make schema`, or `make serve`.
