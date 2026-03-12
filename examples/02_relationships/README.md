# Relationships

This example covers the public relationship API.

It demonstrates:

- a renamed relationship field via `sc.relationship("books")`
- scoped relationship loading with `where=`
- relationship-backed computed fields
- `parent_select=` for transforms that also need parent-row data
- `load="full"` for transforms that need unrestricted model rows

The main intent is to make relationship fields read like normal class code.

Run it in place with `make test`, `make schema`, or `make serve`.
