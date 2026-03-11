# Nested pagination arguments

This example defines the migration-friendly pagination story.

It covers:

- the public `sc.PaginationPolicy` concept
- built-in `sc.CursorPagination(...)` and `sc.OffsetPagination(...)`
- nested `pagination:` input arguments instead of flat field-level args
- keeping the same connection field API while changing only the pagination style

The point is migration pragmatism: an application should be able to keep a
legacy nested pagination input contract without introducing a separate manual
pagination API.

Run it in place with `make test`, `make schema`, or `make serve`.
