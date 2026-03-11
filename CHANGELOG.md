# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

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

[0.1.0]: https://github.com/MeRuslan/strawberry-chemist/releases/tag/0.1.0