# 0.2.0 API contract examples

These examples are forward-looking consumer projects for the redesigned
`strawberry-chemist` 0.2.0 public API.

They are intentionally TDD-oriented:

- each example pins `strawberry-chemist==0.2.0`
- each example has a `test_contract.py` file that defines the intended behavior
- the tests are expected to be meaningful only after the 0.2.0 API exists
- every example uses real SQLAlchemy models backed by SQLite via `aiosqlite`

They are examples, and their contracts are exercised from the root package test
suite in `tests/test_public_api/test_v0_2_contracts.py`.

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

Each example can be verified in two ways.

From the repo root, run the root acceptance suite:

```bash
uv run pytest -q tests/test_public_api/test_v0_2_contracts.py
```

To run an example in isolation against a prepublish local build:

```bash
uv run python -m build --outdir /tmp/strawberry-chemist-dist
uv sync --project examples/v0_2_api/01_types_and_fields \
  --find-links /tmp/strawberry-chemist-dist
uv run --project examples/v0_2_api/01_types_and_fields \
  pytest examples/v0_2_api/01_types_and_fields/test_contract.py
```

The examples intentionally repeat a little boilerplate so that each one can be
read on its own without jumping between shared helper modules.
