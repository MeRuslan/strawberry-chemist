# API Surface Refinement Plan

This document turns the public-surface redesign into an execution plan for the
current codebase.

The target is strict: the documented API should be the supported API. Anything
else should either become internal-only or be deleted.

## Objective

For the `field` / `relationship` / `connection` engine layer:

- keep only the surface taught in `docs/`, `README.md`, and runnable examples
- remove undocumented compatibility aliases from public factory signatures
- remove dead helpers and unused compatibility branches
- adapt existing tests onto the documented surface so behavior coverage stays
  intact while compatibility-only syntax disappears

## Source Of Truth

Going forward, the public contract should be defined by all three of these
together:

- package docs under `docs/`
- runnable examples under `examples/`
- explicit contract tests under `tests/test_public_api/`

If an argument or helper is not represented there, it should not remain part of
the public API by accident.

## Target Surface

### `sc.field`

Supported public usage:

- `@sc.field(select=[...])` for computed scalar fields
- `sc.attr(...)` for direct mapped aliases

Not part of the long-term public surface:

- `post_processor`
- `additional_parent_fields`
- `field(sqlalchemy_name=...)` as the primary way to define computed fields

### `sc.relationship`

Supported public usage:

- `sc.relationship("books")`
- `@sc.relationship("books", select=[...])`
- `sc.relationship(..., where=...)`
- `sc.relationship(..., load="selected" | "full")`

Not part of the long-term public surface:

- `pre_filter`
- `needs_fields`
- `ignore_field_selections`
- `relationship(sqlalchemy_name=...)`

### `sc.connection`

Supported public usage:

- `sc.connection()`
- `sc.connection(source="books")`
- `sc.connection(where=...)`
- `sc.connection(filter=...)`
- `sc.connection(order=...)`
- `sc.connection(default_order_by=...)`
- `sc.connection(pagination=...)`

Not part of the long-term public surface:

- `connection(sqlalchemy_name=...)`

## Current Residue Inventory

| Area | Current residue | Recommended action |
| --- | --- | --- |
| Field factories | `post_processor`, `additional_parent_fields` | remove from public factory; rewrite remaining callers |
| Relationship factories | `pre_filter`, `needs_fields`, `ignore_field_selections` | remove; keep only `where`, `select`, `load` |
| Connection factory | `where=` is underdocumented and `default_order_by` is hidden behind `**kwargs` | keep both and document them explicitly |
| Internal filtering helper | `RuntimeFilter` and `filters/pre_filter.py` | delete if no longer needed after factory cleanup |
| Unused branch | `RuntimeFilter.needs_connection` | delete |
| Dead code | `fields/resolvers.py::SQLAlchemyResolver` | delete |
| Connection-specific ordering hook | `default_order_by` via `**kwargs` | promote to explicit documented `sc.connection(...)` API |
| Legacy internal dependency | relay node id field built via old `field(...)` transform path | replace with dedicated internal node-id field construction |

## Recommended Delivery Phases

## Phase 1: Freeze The Intended Contract

Make the intended surface mechanically explicit before deleting anything.

- Add contract tests that assert the supported signatures for `sc.field`,
  `sc.relationship`, and `sc.connection`.
- Expand `tests/test_public_api/` so it covers the documented knobs directly.
- Treat `docs/` and `examples/` as the only allowed API teachers.
- Mark old end-to-end tests that exercise legacy knobs as migration targets, not
  contract tests.

Completion criteria:

- every documented argument is exercised in a public-api or example-contract test
- no undocumented argument is required by any contract test

## Phase 2: Remove Internal Dependencies On Legacy Knobs

The public cleanup should not be blocked by internal implementation shortcuts.

Required refactors:

- Replace the node-id implementation in `src/strawberry_chemist/relay/public.py`
  so it does not depend on `field(sqlalchemy_name=..., additional_parent_fields=..., post_processor=...)`.
- Promote `default_order_by` from a hidden passthrough into an explicit
  connection-level feature with docs and example coverage.
- Delete `fields/resolvers.py::SQLAlchemyResolver` if no real use case appears.
- Remove the unused `RuntimeFilter.needs_connection` branch.

Completion criteria:

- no internal package code depends on `post_processor`
- no internal package code depends on `additional_parent_fields`
- no internal package code depends on `RuntimeFilter.needs_connection`

## Phase 3: Prune Public Factory Signatures

Once internals are clean, simplify the public builders.

### `sc.field`

Keep:

- decorator usage
- `select=[...]`
- `name=`
- `default=`

Remove:

- `post_processor`
- `additional_parent_fields`
- `sqlalchemy_name` from computed-field usage

### `sc.relationship`

Keep:

- `source`
- `where`
- `select`
- `load`
- `name`
- `default`

Remove:

- `pre_filter`
- `needs_fields`
- `ignore_field_selections`
- `sqlalchemy_name`

### `sc.connection`

Keep:

- `source`
- `where`
- `filter`
- `order`
- `default_order_by`
- `pagination`
- `name`
- `default`

Remove:

- `sqlalchemy_name`
- undocumented passthrough knobs

Recommended policy: because the package is still pre-1.0, prefer direct removal
after internal callers are gone instead of keeping long-lived deprecation
shims for undocumented names.

## Phase 4: Adapt Legacy Tests To The Documented Surface

Several existing tests currently preserve the old surface even though the docs
do not.

Primary migration targets:

- `tests/test_end_to_end/test_related/schema.py`
- `tests/test_end_to_end/test_connection/schema.py`
- `tests/test_loaders/test_loading_strategy_sqlite.py`
- `tests/test_loaders/test_loading_strategies_psql.py`

Actions:

- preserve the existing behavioral assertions wherever possible; change the API
  construction style first, not the expected behavior
- rewrite `post_processor`-style field tests into `@sc.field(select=[...])`
  tests
- rewrite `needs_fields` / `ignore_field_selections` expectations into
  `select=` / `load="full"` expectations
- replace tests that mutate `pre_filter` directly with tests that exercise the
  documented `where=` API and assert the same scoped-loading behavior
- keep loader tests focused on behavior, not compatibility-only attribute names
- only delete a test when it covers dead internal code with no remaining
  user-facing behavior behind it, and only after equivalent coverage exists

Completion criteria:

- no test outside migration-specific coverage relies on legacy arg names
- `tests/test_public_api/` is the contract authority for builder signatures

## Phase 5: Delete Compatibility Modules And Branches

After factories and tests are aligned:

- delete `src/strawberry_chemist/filters/pre_filter.py` if it is no longer used
- remove `RuntimeFilter` imports from field/connection code
- delete `src/strawberry_chemist/fields/resolvers.py`
- remove compatibility comments and warning exceptions that only mention old
  names such as `ignore_field_selections`

## Acceptance Criteria

The refinement is complete when all of the following are true:

- `sc.field`, `sc.relationship`, and `sc.connection` only accept documented
  public arguments
- every remaining public argument is described in `docs/` and shown in at least
  one runnable example
- `tests/test_public_api/` fails if an undocumented argument reappears
- no internal code depends on deleted compatibility aliases
- no dead helper modules remain in the package tree

## Recommended First Patch Series

The lowest-risk implementation order is:

1. add signature-level contract tests
2. replace the relay node-id use of the old field transform path
3. delete `SQLAlchemyResolver` and the unused `RuntimeFilter.needs_connection`
   branch
4. rewrite legacy tests to the documented surface
5. remove alias parameters from `field`, `relationship`, and `connection`
6. delete `RuntimeFilter` / `pre_filter.py` if no longer needed

This order keeps the external cleanup honest: docs first, tests next, then
surface reduction.
