# Context And Extensions

Chemist-managed fields rely on a small context contract rather than a framework
base class.

## Required context behavior

Your GraphQL context should provide:

- `get_session()`: an async context manager yielding an `AsyncSession`

At runtime, `sc.extensions()` also attaches the internal dataloader container
and the field-selection cache used by Chemist-managed fields.

## Schema integration

```python
schema = strawberry.Schema(
    query=Query,
    extensions=sc.extensions(),
)
```

You can mix Chemist-managed fields with normal Strawberry resolvers on the same
schema.

Primary example:

- [`examples/05_context_and_extensions`](https://github.com/MeRuslan/strawberry-chemist/tree/main/examples/05_context_and_extensions)
