# Connections, filters, and ordering

This example defines the intended public shape for collection querying.

It covers:

- declarative `@sc.filter` and `@sc.order` classes
- path-based filters and ordering over relationships
- boolean filter composition through `and` / `or` / `not`
- custom filter escape hatches through `apply=`
- one `sc.connection(...)` entrypoint for both cursor and offset pagination

The contract tests assume a GraphQL surface with `filter:` and `orderBy:`
arguments, using the default flat pagination argument shape.

Run it in place with `make test`, `make schema`, or `make serve`.
