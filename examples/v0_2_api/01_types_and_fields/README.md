# Types and computed fields

This example is the smallest consumer-facing read model for the redesigned API.

It focuses on:

- explicit `@sc.type(model=...)` declarations
- direct attribute aliasing with `sc.attr(...)`
- computed fields via `@sc.field(select=[...])`
- the default `sc.extensions()` integration point

The contract test should read as the first acceptance target for replacing the
current `post_processor` surface.
