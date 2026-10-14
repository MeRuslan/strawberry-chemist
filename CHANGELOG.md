# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [0.7.0] - 2026-10-14

### Added

- Query cost limits: `sc.QueryCostLimiter(max_objects=..., max_fields=...)`
  rejects an operation whose worst case is over a limit before anything
  resolves (`QUERY_COST_EXCEEDED` in the error's extensions), or only logs it
  with `dry_run=True`. The worst case comes from `sc.estimate_query_cost(...)`:
  connection pages as large as their arguments ask, capped by their pagination
  policy, multiply what's selected under them. Fields Chemist can't size get
  `metadata=sc.cost(list_size=...)` or `metadata=sc.cost(pagination=...)`.
- `CursorPagination.page_size(arguments)` and `OffsetPagination.page_size(arguments)`:
  the page size for raw GraphQL argument values, capped like `paginate_query`.
- `sc.node_lookup(...)` takes `metadata=` for the field it makes.

## [0.6.9] - 2026-10-13

### Fixed

- `node(id:)` failed with "Expected value of type 'X' but got: <Model instance>"
  for models that several node types split with `is_type_of` (say, posts and
  reviews on one table). `resolve_node` cast the row to the first type the
  token matched, and strawberry-graphql 0.334 resolves interfaces by
  `strawberry.cast`, where 0.311 asked `is_type_of`. The row is cast only to a
  type that takes it now; otherwise the schema picks one by `is_type_of`.

## [0.6.8] - 2026-10-13

### Fixed

- On Python 3.14+ types, interfaces and filters lost their annotated fields:
  annotations were read from the class `__dict__`, where PEP 649 no longer
  keeps them. They are read with `typing_extensions.get_annotations` now.

### Changed

- Supports strawberry-graphql 0.311.1 up to 0.334.x and graphql-core 3.2 and
  3.3; depends on typing-extensions>=4.14.0.
- Tested on Python 3.11 to 3.15 and SQLAlchemy 2.0 and 2.1. CI runs the tests,
  including the PostgreSQL ones, on the matrix Python (it used
  `.python-version` before) with both the locked and the lowest allowed
  dependencies; a Dependencies workflow checks the lockfile, known
  vulnerabilities and that the dependency ranges admit the newest releases.
- Refreshed `uv.lock`, the dev dependencies, the examples and the CI actions.

## [0.6.7] - 2026-10-12

### Changed

- On PostgreSQL, relationship and connection loaders now pass parent keys as
  array parameters of `unnest()` (`UnnestLoadingStrategy`, the new default)
  instead of a literal `VALUES` list. The statements get a SQLAlchemy cache
  key, so they are compiled once per shape rather than on every load. Other
  dialects keep `ValuesLoadingStrategy`, SQLite keeps `UnionLoadingStrategy`.
- Relationship and connection fields collect their sub-selection once per query
  node in an operation instead of once per parent object. The seen nodes live
  in `SelectionCacheExtension`'s per-operation state.

### Fixed

- PostgreSQL test fixtures work with pytest-postgresql 8 (`DatabaseJanitor`
  takes keyword arguments only).

## [0.6.6] - 2026-05-15

### Added

- Added `sc.interface(model=...)` for declaring SQLAlchemy-backed Strawberry
  interfaces with the same field processing and model metadata used by
  `sc.type(model=...)`.

### Fixed

- Fixed root `sc.Connection[InterfaceType]` fields for model-backed interfaces
  so they resolve the SQLAlchemy model from the interface metadata instead of
  requiring relationship metadata.

## [0.6.5] - 2026-03-22

### Fixed

- Shared loader-session teardown now drains in-flight borrowers before closing
  the request-local `AsyncSession`, and late internal loads during shutdown
  fall back to fresh short-lived sessions instead of racing the close.

## [0.6.4] - 2026-03-22

### Added

- Added global `sc.configure(use_single_loader_session=True)` support so
  Chemist-managed loaders can reuse one request-local SQLAlchemy
  `AsyncSession` instead of opening a new session for each internal load.

### Changed

- Loader session reuse is now tracked through explicit `SQLAlchemyContext`
  fields rather than dynamic attribute assignment, and shared-session access is
  serialized internally to avoid concurrent `AsyncSession` use.

## [0.6.3] - 2026-03-21

### Fixed

- Restored raw-field support for SQLAlchemy composite attributes such as
  `Character.birth_date` by accepting SQLAlchemy proxy descriptors during type
  processing instead of requiring every mapped attribute to be an
  `InstrumentedAttribute`.

### Added

- Added regression coverage for composite raw fields to ensure Chemist types
  can expose `composite(...)` model attributes and resolve them through GraphQL.

## [0.6.2] - 2026-03-21

### Fixed

- Evaluated callable `where=` clauses at loader runtime for relationships and
  connections instead of passing raw lambdas through to SQLAlchemy.
- Restored support for request-context-dependent `where=[lambda: ...]` filters,
  including lists of callable clauses that read from `context_var`.

### Added

- Added loader regression coverage for callable `where=` clauses on both
  relationship-backed and root connection queries.

## [0.6.1] - 2026-03-21

### Fixed

- Fixed async `permission_classes=[...]` on Chemist relation-backed fields so
  connections and relationships continue through Strawberry's async execution
  path instead of leaking un-awaited coroutines.
- Preserved Strawberry field permission metadata when Chemist upgrades inherited
  or declared fields through `from_field(...)`, including interface-driven
  upgrades from `sc.field(...)` into relationship-backed Chemist fields.

### Added

- Added inheritance regression coverage for interface-defined fields on Chemist
  types, including both simple-field inheritance and the relation-field upgrade
  path with permissions.

## [0.6.0] - 2026-03-18

### Added

- Added `sc.settings` module for setting global pagination and relay id codec defaults 

### Changed

- Node API surface remodeled completely: you need to inherit from `sc.Node` explicitly.
- Adapted node example projects like `04_nodes_and_relay_ids` and relay documentation.
- Better mypy coverage and typing througout the repository.

### Removed
- `@sc.node(...)` type decorator, node interface implementations are declared using 
`sc.Node`.

## [0.5.1] - 2026-03-18

### Fixed

- Preserved explicit non-node `types=(...)` entries across `sc.relay.configure(...)`.

## [0.5.0] - 2026-03-17

### Added

- Added the public resolver-argument contract surface: `@sc.field(select={...})`
  bindings, `source_param_name=` on relationship and connection resolvers, and
  `select=` on `sc.connection(...)` for computed return-node data.
- Added the `09_resolver_argument_contracts` runnable example and aligned the
  public docs around the supported resolver injection rules.

### Changed

- Chemist resolver decorators now hide only Chemist-injected runtime params;
  application-defined resolver params remain public GraphQL arguments.
- Relationship and connection resolver injection now follows the effective
  source parameter name instead of positional first-parameter behavior.
- Connection field loading now ignores plain runtime-only GraphQL fields that do
  not map to SQLAlchemy columns, which allows resolvers to annotate returned
  node objects with computed fields.

### Fixed

- Fixed counted relationship-backed connections to compute `totalCount` from
  the unpaginated result set instead of the current page slice.

## [0.4.0] - 2026-03-16

### Added

- Added schema-owned relay configuration via
  `sc.relay.configure(schema, default_codec=...)` plus public
  `sc.relay.encode_node_id(...)` and `sc.relay.decode_node_id(...)` helpers for
  application code and tests.
- Added relay contract coverage for automatic `Node` interface implementation,
  unrestricted `node(id: ...)` setup, and schema-default codec behavior.

### Changed

- `@sc.node(...)` types now automatically implement the public `Node` interface
  without requiring explicit inheritance from `sc.Node`.
- Unrestricted `sc.node_field()` now exposes the `Node` interface and uses
  schema configuration to register the concrete node types that belong to that
  schema.
- Relay ID encoding and decoding now resolve the default codec from the schema
  at runtime instead of freezing it at decorator import time; per-node
  `codec=` remains the explicit override path.
- Updated relay docs and runnable examples to show the supported
  `sc.relay.configure(schema)` setup path and schema-bound node ID helpers.

## [0.3.1] - 2026-03-12

### Added

- Docs improvements

## [0.3.0] - 2026-03-12

### Added

- Added `parent_select=` to `sc.relationship(...)` and `sc.connection(...)`
  for parent-aware relationship and nested connection transforms.

### Changed

- Stabilized the `field` / `relationship` / `connection` surface around the
  documented API and aligned examples, docs, and contract tests with the
  supported runtime behavior.
- Promoted `default_order_by=` and `connection(where=...)` as explicit
  documented connection features, with updated example coverage.
- Reworked connection decorated-resolver handling so loaded connection results
  are injected without leaking pagination/filter/order kwargs into user
  resolvers.
- Completed practical mypy coverage for `src/strawberry_chemist` under the
  current config and added mypy as a dedicated CI gate.
- Refreshed the docs entrypoints and removed stale package documentation such
  as `LIMITATIONS.md`.

### Removed

- Removed undocumented legacy factory knobs from the supported public surface,
  including `post_processor`, `additional_parent_fields`, `pre_filter`,
  `needs_fields`, and `ignore_field_selections`.

## [0.2.4] - 2026-03-11

### Changed

- Made the numbered example projects self-contained by adding per-example
  `Makefile` workflows plus example-local schema print and serve entrypoints.
- Changed the repo-root `example-*` commands to delegate directly into the
  example directories instead of relying on repo-level example runner scripts.
- Updated the examples docs to describe the in-directory `make` workflows and
  the portable copied-example path.

## [0.2.2] - 2026-03-11

### Added

- Example workflow commands via `make`, including single-example and
  all-examples test targets plus schema print/serve helpers.

### Changed

- Split the runnable example contract suites into smaller, more isolated tests
  without introducing shared cross-example helpers.
- Moved the public runnable examples from `examples/v0_2_api/` to `examples/`
  and updated scripts, docs, tests, and example project metadata to match the
  new layout.
- Hardened the example runners to invoke `python -m pytest`, which avoids
  broken moved-environment entrypoints.
- Renamed the preferred example `make` targets to `example-*` / `examples-*`
  while keeping the older `sample-*` aliases working.

## [0.2.1] - 2026-03-11

### Changed

- Upgraded `strawberry-graphql` to the `0.311.x` line and updated the package
  internals for compatibility with current Strawberry releases.
- Expanded tested Python support to `3.11` through `3.14` and added a GitHub
  Actions pytest matrix for those versions.

## [0.2.0] - 2026-03-11

### Added

- Redesigned public API centered on `@sc.type`, `@sc.node`, `sc.attr`,
  `@sc.field`, `sc.relationship`, and `sc.connection(...)`.
- Declarative filter and ordering DSLs plus `manual_filter(...)` and
  `manual_order(...)` escape hatches.
- Relay/node redesign with inferred mapper primary keys, readable default IDs,
  `sc.node_field()`, and `sc.node_lookup(...)`.
- Public pagination policy surface with flat and nested argument styles.
- Runnable public API contract examples under `examples/`, public docs under
  `docs/`, and GitHub Pages-ready MkDocs configuration.

### Changed

- Made the 0.2.0 API the preferred package surface and updated top-level
  exports accordingly.
- Added dual-mode example project workflows for testing against the current
  checkout or a published/prepublish package build.

### Removed

- Legacy public helper surfaces such as `relation_field`,
  `relay_connection_field`, `limit_offset_connection_field`, old relay lookup
  decorators, and the old filter/order implementation classes from the
  supported API.

## [0.1.0] - 2026-03-11

### Added

- Standalone packaging using a `src/` layout and Hatchling build backend.
- MIT license and publish-ready package metadata.
- Basic package-user README and separate limitations document.
- Ruff formatter, mypy, and pre-commit hooks for local quality checks.
- GitHub Actions workflow for building and publishing releases.
- `CHANGELOG.md` for release notes.

### Changed

- Extracted from the parent project into its own package.
- Renamed the public package to `strawberry-chemist`.
- Renamed the import package from `strawberry_sqlalchemy` to `strawberry_chemist`.
- Made non-Postgres tests the default pytest selection.
- Moved Postgres-only tests under the `psql` marker.

[0.6.3]: https://github.com/MeRuslan/strawberry-chemist/releases/tag/0.6.3
[0.6.2]: https://github.com/MeRuslan/strawberry-chemist/releases/tag/0.6.2
[0.6.1]: https://github.com/MeRuslan/strawberry-chemist/releases/tag/0.6.1
[0.6.0]: https://github.com/MeRuslan/strawberry-chemist/releases/tag/0.6.0
[0.5.0]: https://github.com/MeRuslan/strawberry-chemist/releases/tag/0.5.0
[0.4.0]: https://github.com/MeRuslan/strawberry-chemist/releases/tag/0.4.0
[0.3.1]: https://github.com/MeRuslan/strawberry-chemist/releases/tag/0.3.1
[0.2.2]: https://github.com/MeRuslan/strawberry-chemist/releases/tag/0.2.2
[0.3.0]: https://github.com/MeRuslan/strawberry-chemist/releases/tag/0.3.0
[0.2.4]: https://github.com/MeRuslan/strawberry-chemist/releases/tag/0.2.4
[0.2.3]: https://github.com/MeRuslan/strawberry-chemist/releases/tag/0.2.3
[0.2.1]: https://github.com/MeRuslan/strawberry-chemist/releases/tag/0.2.1
[0.2.0]: https://github.com/MeRuslan/strawberry-chemist/releases/tag/0.2.0
[0.1.0]: https://github.com/MeRuslan/strawberry-chemist/releases/tag/0.1.0
