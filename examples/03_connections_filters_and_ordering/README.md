# Connections, filters, and ordering

This example defines the intended public shape for collection querying.

It covers:

- declarative `@sc.filter` and `@sc.order` classes
- scoped collections via `sc.connection(where=...)`
- server-owned default collection ordering via `default_order_by=...`
- `parent_select=` for nested connections that also depend on parent-row data
- path-based filters and ordering over relationships
- boolean filter composition through `and` / `or` / `not`
- custom filter escape hatches through `apply=`
- one `sc.connection(...)` entrypoint for both cursor and offset pagination

The contract tests assume a GraphQL surface with `filter:` and `orderBy:`
arguments, using the default flat pagination argument shape.

Run it in place with `make test`, `make schema`, or `make serve`.
