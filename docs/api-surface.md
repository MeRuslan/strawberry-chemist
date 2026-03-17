# API Surface

This is the stable public shape of the package.

The pattern is consistent across the surface:

- explicit Strawberry type classes define the public GraphQL contract
- Chemist helpers attach SQLAlchemy-aware behavior to those types
- the package stays adaptable by exposing escape hatches where real production
  schemas need them

Two practical properties are worth calling out:

- Chemist-managed relationship and connection fields are batched through
  dataloaders and selection-aware SQL shaping, so they avoid per-parent N+1
  loading.
- Relationship and connection APIs are intentionally broad enough to cover
  plain mapped fields, renamed fields, scoped fields, computed fields, root
  collections, and nested collections.

## Surface overview

| Area | Main entrypoints | Purpose | Example |
| --- | --- | --- | --- |
| Types and mapped fields | `@sc.type`, `sc.attr`, `@sc.field` | Define explicit GraphQL DTOs and computed fields | [`01_types_and_fields`](https://github.com/MeRuslan/strawberry-chemist/tree/main/examples/01_types_and_fields) |
| Relationships | `sc.relationship` / `@sc.relationship` | Expose related data or relationship-backed computed fields without N+1 boilerplate | [`02_relationships`](https://github.com/MeRuslan/strawberry-chemist/tree/main/examples/02_relationships) |
| Connections | `sc.connection`, `sc.Connection`, `sc.OffsetConnection` | Expose queryable collections at root or on relationships with batched loading | [`03_connections_filters_and_ordering`](https://github.com/MeRuslan/strawberry-chemist/tree/main/examples/03_connections_filters_and_ordering) |
| Pagination | `sc.CursorPagination`, `sc.OffsetPagination`, `sc.PaginationPolicy` | Choose flat or nested pagination argument styles and result envelopes | [`08_nested_pagination_arguments`](https://github.com/MeRuslan/strawberry-chemist/tree/main/examples/08_nested_pagination_arguments) |
| Filters | `@sc.filter`, `sc.FilterSet`, `sc.filter_field`, `sc.manual_filter` | Add client-controlled filtering with declarative or manual contracts | [`03_connections_filters_and_ordering`](https://github.com/MeRuslan/strawberry-chemist/tree/main/examples/03_connections_filters_and_ordering), [`06_manual_filters_and_orders`](https://github.com/MeRuslan/strawberry-chemist/tree/main/examples/06_manual_filters_and_orders) |
| Ordering | `@sc.order`, `sc.order_field`, `sc.manual_order` | Add client-controlled ordering with declarative or manual contracts | [`03_connections_filters_and_ordering`](https://github.com/MeRuslan/strawberry-chemist/tree/main/examples/03_connections_filters_and_ordering), [`06_manual_filters_and_orders`](https://github.com/MeRuslan/strawberry-chemist/tree/main/examples/06_manual_filters_and_orders) |
| Relay IDs and nodes | `sc.Node`, `sc.node_id`, `sc.node_field`, `sc.relay.encode_node_id(...)`, `sc.relay.decode_node_id(...)` | Define explicit node types and resolve them through schema-owned relay IDs | [`04_nodes_and_relay_ids`](https://github.com/MeRuslan/strawberry-chemist/tree/main/examples/04_nodes_and_relay_ids) |
| Resolver node injection | `sc.node_lookup` | Load an ORM object from a node ID into a query or mutation resolver | [`07_node_lookup_and_permissions`](https://github.com/MeRuslan/strawberry-chemist/tree/main/examples/07_node_lookup_and_permissions) |
| Resolver contracts | `@sc.field(select=...)`, `sc.relationship`, `sc.connection`, `sc.node_lookup` | Hide Chemist-injected runtime params and expose the rest as GraphQL args | [`09_resolver_argument_contracts`](https://github.com/MeRuslan/strawberry-chemist/tree/main/examples/09_resolver_argument_contracts) |
| Schema integration | `sc.extensions()` | Enable dataloaders and selection caching for Chemist-managed fields | [`05_context_and_extensions`](https://github.com/MeRuslan/strawberry-chemist/tree/main/examples/05_context_and_extensions) |

## Practical rule of thumb

- use `@sc.type` to define the schema you want clients to see
- use `sc.Node` only for types that should participate in relay/node lookup
- use `sc.relationship(...)` for related data and relationship-backed computed
  fields
- use `sc.connection(...)` when clients need filtering, ordering, or pagination
  on root or nested collections
- use the declarative DSLs first
- use `manual_filter` and `manual_order` when the GraphQL input shape itself
  must stay custom
