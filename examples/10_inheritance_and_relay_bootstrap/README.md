# Inheritance and relay reachability

This example captures the current inheritance and schema-reachability shape of
the library.

It covers:

- subclassed Chemist bases carrying inherited annotations, `sc.attr`, and `@sc.field`
- subclassed node bases carrying inherited `sc.relationship(...)` fields
- plain Python mixins with inherited `@sc.field` / `@sc.relationship` methods staying absent from the SDL
- concrete-class field descriptors still materializing even when mixin-carried Chemist methods do not
- explicit `types=(...)` preserving detached non-node schema types during normal schema construction
- an interface-backed preview type that remains a valid fragment target without any post-build relay step

The contract is:

- Chemist-to-Chemist subclass inheritance works for the cases exercised here
- complex node inheritance still resolves inherited base fields and relationships
- plain mixin-carried Chemist methods should be treated as unsafe during this migration
- detached non-node schema types must stay reachable through normal `types=(...)` wiring

Run it in place with `make test`, `make schema`, or `make serve`.
