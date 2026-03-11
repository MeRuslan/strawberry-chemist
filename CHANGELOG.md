# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

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
- Runnable `v0_2_api` contract examples, public docs under `docs/`, and GitHub
  Pages-ready MkDocs configuration.

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

[0.2.1]: https://github.com/MeRuslan/strawberry-chemist/releases/tag/0.2.1
[0.2.0]: https://github.com/MeRuslan/strawberry-chemist/releases/tag/0.2.0
[0.1.0]: https://github.com/MeRuslan/strawberry-chemist/releases/tag/0.1.0
