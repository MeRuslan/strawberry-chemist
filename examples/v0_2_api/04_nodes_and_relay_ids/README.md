# Nodes and relay IDs

This example defines the intended relay ergonomics for the standalone package.

It covers:

- `@sc.node(model=...)` without an explicit `sc.Node` base class
- default identifier inference from model primary keys
- custom `ids=(...)` for natural keys
- composite identifiers
- an optional compact codec for legacy or integration-sensitive environments

The readable default token shape assumed here is `"<NodeName>_<serialized ids>"`.
