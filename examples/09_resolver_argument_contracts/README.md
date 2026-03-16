# Resolver argument contracts

This example defines the intended public contract for Chemist-managed resolver
decorators.

It covers:

- `@sc.field` with public custom args and with `select=`-backed injected args
- `@sc.field(select={source: param})` for explicit source-to-parameter binding
- `@sc.relationship` with one hidden loaded relationship param plus public args
- `@sc.connection` with one hidden loaded connection param plus public args
- `@sc.connection(select=[...])` for loading source fields needed by computed return-node data
- connection resolvers annotating returned node objects instead of reshaping pagination
- `source_param_name=` for relationship and connection loaders that want a custom hidden Python parameter name
- `@sc.node_lookup(...)` with a hidden loaded node param plus public args
- manual `@strawberry.field` fields declared alongside Chemist-managed fields

The contract is:

- Chemist-injected runtime resolver params stay out of the schema
- application-defined resolver params stay in the schema
- non-Chemist fields can live on the same types without special handling

Run it in place with `make test`, `make schema`, or `make serve`.
