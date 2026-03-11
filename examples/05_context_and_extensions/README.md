# Context and extensions

This example shows the integration boundary between Chemist-managed fields and
the surrounding Strawberry application.

It keeps Chemist focused on SQLAlchemy-aware field behavior while leaving the
root resolver layer and application-specific context shape in normal Strawberry
code.

It demonstrates:

- a minimal `get_session()` context protocol
- application-specific context data (`request_id`)
- `sc.extensions()` on the schema
- manual Strawberry root resolvers returning ORM objects that Chemist fields can use

Run it in place with `make test`, `make schema`, or `make serve`.
