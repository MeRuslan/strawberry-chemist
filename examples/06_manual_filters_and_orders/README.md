# Manual filters and orders

This example defines the intended low-level escape hatch for collection query
arguments.

It covers:

- `sc.manual_filter(...)` with a hand-authored Strawberry input
- `sc.manual_order(...)` with a hand-authored Strawberry input
- preserving a legacy `order:` argument instead of `orderBy:`
- required filter arguments
- custom SQL query modifiers that can add joins and grouping

The main point is migration safety: applications should be able to adopt
`sc.connection(...)` while keeping an existing public GraphQL schema shape when
needed.

Run it in place with `make test`, `make schema`, or `make serve`.
