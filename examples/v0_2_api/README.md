# 0.2.0 API contract examples

These examples are forward-looking consumer projects for the redesigned
`strawberry-chemist` 0.2.0 public API.

They are intentionally TDD-oriented:

- each example pins `strawberry-chemist==0.2.0`
- each example has a `test_contract.py` file that defines the intended behavior
- the tests are expected to be meaningful only after the 0.2.0 API exists
- every example uses real SQLAlchemy models backed by SQLite via `aiosqlite`

They are examples, not part of the current package test suite.

## Coverage map

| Example | Main concepts |
| --- | --- |
| `01_types_and_fields` | `@sc.type`, `sc.attr`, `@sc.field`, `sc.extensions()` |
| `02_relationships` | `sc.relationship`, renamed relationship fields, `where=`, `load="full"` |
| `03_connections_filters_and_ordering` | `sc.connection`, `sc.Connection`, `sc.OffsetConnection`, `@sc.filter`, `sc.filter_field`, `@sc.order`, `sc.order_field`, pagination policy objects |
| `04_nodes_and_relay_ids` | `@sc.node`, `sc.node_field()`, default PK IDs, custom `ids=(...)`, composite IDs, optional codec |
| `05_context_and_extensions` | minimal context protocol, `sc.extensions()`, mixed Strawberry root resolvers with Chemist-managed fields |

## Usage shape

Once the 0.2.0 API exists, each example should be runnable in isolation.

Example flow:

```bash
uv sync --project examples/v0_2_api/01_types_and_fields
uv run --project examples/v0_2_api/01_types_and_fields pytest
```

The examples intentionally repeat a little boilerplate so that each one can be
read on its own without jumping between shared helper modules.
