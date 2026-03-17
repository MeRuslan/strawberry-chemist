# Inheritance and relay bootstrap

This example captures the current 0.5.0 inheritance and relay-bootstrap shape
without patching the library.

It covers:

- subclassed Chemist bases carrying inherited annotations, `sc.attr`, and `@sc.field`
- subclassed node bases carrying inherited `sc.relationship(...)` fields
- plain Python mixins with inherited `@sc.field` / `@sc.relationship` methods staying absent from the SDL
- concrete-class field descriptors still materializing even when mixin-carried Chemist methods do not
- `sc.relay.configure(...)` preserving detached non-node `types=(...)` entries that were already on the initial schema
- an interface-backed preview type that remains a valid fragment target after `configure(...)`

The contract is:

- Chemist-to-Chemist subclass inheritance works for the cases exercised here
- complex node inheritance still resolves inherited base fields and relationships
- plain mixin-carried Chemist methods should be treated as unsafe during this migration
- relay bootstrap must preserve explicit non-node schema types instead of dropping them

Run it in place with `make test`, `make schema`, or `make serve`.
