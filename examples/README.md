# Public API Examples

These examples are standalone consumer projects for the current
`strawberry-chemist` public API.

Each example:

- pins `strawberry-chemist==0.2.1`
- includes a local `tool.uv.sources` override pointing at the current checkout
- has a `test_contract.py` file defining the intended behavior
- uses real SQLAlchemy models backed by SQLite via `aiosqlite`

Their contracts are also exercised from the root package test suite in
`tests/test_public_api/test_examples_contracts.py`.

## Coverage map

| Example | Main concepts |
| --- | --- |
| `01_types_and_fields` | `@sc.type`, `sc.attr`, `@sc.field`, `sc.extensions()` |
| `02_relationships` | `sc.relationship`, renamed relationship fields, `where=`, `load="full"` |
| `03_connections_filters_and_ordering` | `sc.connection`, `sc.Connection`, `sc.OffsetConnection`, `@sc.filter`, `sc.filter_field`, `@sc.order`, `sc.order_field`, pagination policy objects |
| `04_nodes_and_relay_ids` | `@sc.node`, `sc.node_field()`, default PK IDs, custom `ids=(...)`, composite IDs, optional codec |
| `05_context_and_extensions` | minimal context protocol, `sc.extensions()`, mixed Strawberry root resolvers with Chemist-managed fields |
| `06_manual_filters_and_orders` | `sc.manual_filter`, `sc.manual_order`, preserving legacy `filter` / `order` GraphQL contracts while still using `sc.connection(...)` |
| `07_node_lookup_and_permissions` | `sc.node_lookup`, custom ID argument names, injected ORM nodes, field permissions, post-load node permissions |
| `08_nested_pagination_arguments` | `sc.PaginationPolicy`, built-in cursor/offset policies, nested `pagination:` input arguments for migration compatibility |

## Usage shape

Each example can be verified in three ways.

From the repo root, run the root acceptance suite:

```bash
uv run pytest -q tests/test_public_api/test_examples_contracts.py
```

To run an example in isolation against the current checkout:

```bash
scripts/run-example-local 01_types_and_fields
make example-test EXAMPLE=01_types_and_fields
```

To run an example against the pinned published package instead of the checkout:

```bash
scripts/run-example-published 01_types_and_fields
make example-test-published EXAMPLE=01_types_and_fields
```

To print an example schema:

```bash
make example-schema EXAMPLE=01_types_and_fields
```

To serve a seeded example schema locally:

```bash
uv sync --group dev
make example-serve EXAMPLE=01_types_and_fields PORT=8000
```

To run published-mode against a locally built distribution artifact:

```bash
uv run python -m build --outdir /tmp/strawberry-chemist-dist
STRAWBERRY_CHEMIST_FIND_LINKS=/tmp/strawberry-chemist-dist \
  scripts/run-example-published 01_types_and_fields
```

The examples intentionally repeat a little boilerplate so that each one can
read on its own without jumping between shared helper modules.
