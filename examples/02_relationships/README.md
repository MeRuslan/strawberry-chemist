# Relationships

This example covers the redesigned relationship API.

It demonstrates:

- a renamed relationship field via `sc.relationship("books")`
- scoped relationship loading with `where=`
- relationship-backed computed fields
- `load="full"` for transforms that need unrestricted model rows

The main intent is to make the old `relation_field(..., post_processor=...)`
shape feel like normal class code.
