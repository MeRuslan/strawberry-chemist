# Types and computed fields

This example is the smallest consumer-facing read model in the public API.

It focuses on:

- explicit `@sc.type(model=...)` declarations
- direct attribute aliasing with `sc.attr(...)`
- computed fields via `@sc.field(select=[...])`
- the default `sc.extensions()` integration point

Its contract test is the smallest end-to-end example in the repo.

Run it in place with `make test`, `make schema`, or `make serve`.
