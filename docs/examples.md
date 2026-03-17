# Examples

The `examples/` projects are runnable contract examples for the public
API.

Each numbered example is self-contained. The repo-root `example-*` commands
delegate into the example directory, and the example directory itself can be
copied and run on its own with `make`.
Each one keeps the same internal boundary:

- `db.py` for SQLAlchemy models and seeded database setup
- `schema.py` for `AppContext`, GraphQL types, and `build_schema()`
- `app.py` for the runtime CLI that prints SDL or serves the schema

## Run against the current checkout

```bash
make example-test EXAMPLE=03_connections_filters_and_ordering
```

This uses the example project's own environment, but resolves
`strawberry-chemist` from the current repository checkout through
`tool.uv.sources`.

## Run against the pinned published package

```bash
make example-test-published EXAMPLE=03_connections_filters_and_ordering
```

This ignores the local source override and resolves the pinned published
version instead.

## Run inside an example directory

```bash
cd examples/03_connections_filters_and_ordering
make test
make schema
make serve PORT=8000
```

These in-directory commands default to the pinned published package so the
example still works after being copied out of the repository.

When working inside the repository checkout and you want the current source
tree instead, use `make test-local`, `make schema-local`, and
`make serve-local`.

## Print or serve a sample schema

Print an example SDL from the repo root:

```bash
make example-schema EXAMPLE=03_connections_filters_and_ordering
```

Serve a seeded example locally:

```bash
make example-serve EXAMPLE=03_connections_filters_and_ordering PORT=8000
```

To point that published-mode flow at a locally built distribution instead of
PyPI, set `STRAWBERRY_CHEMIST_FIND_LINKS`:

```bash
uv run python -m build --outdir /tmp/strawberry-chemist-dist
STRAWBERRY_CHEMIST_FIND_LINKS=/tmp/strawberry-chemist-dist \
  make example-test-published EXAMPLE=03_connections_filters_and_ordering
```

## Example index

| Example | Main concepts |
| --- | --- |
| [`01_types_and_fields`](https://github.com/MeRuslan/strawberry-chemist/tree/main/examples/01_types_and_fields) | `@sc.type`, `sc.Node`, `sc.attr`, `@sc.field` |
| [`02_relationships`](https://github.com/MeRuslan/strawberry-chemist/tree/main/examples/02_relationships) | `sc.relationship`, renamed relationships, scoped relationships, relationship-backed computed fields |
| [`03_connections_filters_and_ordering`](https://github.com/MeRuslan/strawberry-chemist/tree/main/examples/03_connections_filters_and_ordering) | `sc.connection`, filter DSL, order DSL, flat pagination |
| [`04_nodes_and_relay_ids`](https://github.com/MeRuslan/strawberry-chemist/tree/main/examples/04_nodes_and_relay_ids) | node types, root node lookup, default and custom IDs |
| [`05_context_and_extensions`](https://github.com/MeRuslan/strawberry-chemist/tree/main/examples/05_context_and_extensions) | context contract, schema integration, `sc.extensions()` |
| [`06_manual_filters_and_orders`](https://github.com/MeRuslan/strawberry-chemist/tree/main/examples/06_manual_filters_and_orders) | manual filter and order contracts |
| [`07_node_lookup_and_permissions`](https://github.com/MeRuslan/strawberry-chemist/tree/main/examples/07_node_lookup_and_permissions) | `sc.node_lookup`, resolver injection, permissions |
| [`08_nested_pagination_arguments`](https://github.com/MeRuslan/strawberry-chemist/tree/main/examples/08_nested_pagination_arguments) | nested `pagination:` argument style with built-in policies |
| [`09_resolver_argument_contracts`](https://github.com/MeRuslan/strawberry-chemist/tree/main/examples/09_resolver_argument_contracts) | hidden injected resolver params, public GraphQL args, `select={source: param}`, `source_param_name=`, runtime-only return-node fields |
| [`10_inheritance_and_relay_bootstrap`](https://github.com/MeRuslan/strawberry-chemist/tree/main/examples/10_inheritance_and_relay_bootstrap) | subclassed Chemist base inheritance, plain mixin caveats, complex node inheritance, explicit schema reachability for detached non-node types |
