# Context And Extensions

Chemist-managed fields rely on a small context contract rather than a framework
base class.

Chemist does not create the GraphQL context object. Your application supplies
that object to Strawberry, and `sc.extensions()` adds the request-local loader
container and selection cache onto it during execution.

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

## Execution wiring

Pass your application context into Strawberry execution explicitly:

```python
context = build_context(session_factory, request_id="req-001")
result = await schema.execute(query, context_value=context)
```

For ASGI integrations, return that same context object from the framework
context hook for each request.

Primary example:

- [`examples/05_context_and_extensions`](https://github.com/MeRuslan/strawberry-chemist/tree/main/examples/05_context_and_extensions)
