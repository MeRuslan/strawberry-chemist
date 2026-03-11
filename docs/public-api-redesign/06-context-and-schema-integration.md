# Context And Schema Integration

## 1. Current Problem

The package currently exposes a mostly-empty `SQLAlchemyContext` type and a misspelled `extentions` module.
That is serviceable for an internal bridge, but weak as a standalone public contract.

A public package should make it obvious:

- what the user must provide
- what the package provides
- what should remain internal

## 2. Proposed Context Contract

Chemist should depend on a minimal protocol, not on subclassing a concrete base type.

```python
from contextlib import asynccontextmanager
from typing import AsyncIterator, Protocol
from sqlalchemy.ext.asyncio import AsyncSession


class ChemistContext(Protocol):
    @asynccontextmanager
    async def get_session(self) -> AsyncIterator[AsyncSession]:
        ...
```

Optional fields like `user`, `request`, or tracing state should remain application-defined.

## 3. Package Helper For Extensions

The package should expose a simple helper:

```python
schema = strawberry.Schema(
    query=Query,
    extensions=sc.extensions(),
)
```

That helper should return the stable required extension list, for example:

- dataloader setup
- per-request field selection cache

The application can still append its own extensions after that.

## 4. Explicit Extension Types Can Still Exist

Advanced users may still import extension classes directly:

```python
from strawberry_chemist.extensions import DataLoadersExtension, SelectionCacheExtension
```

But the preferred docs path should be `sc.extensions()`.

## 5. Naming Fix

The stable public module should be `strawberry_chemist.extensions`.

`strawberry_chemist.extentions` should remain as a compatibility alias only.

## 6. Internal State Should Stay Internal

These are useful implementation details, but should not be core documented API:

- `context_var`
- `field_sub_selections` internal cache shape
- `dataloader_container` internal storage details

Public docs can describe the behavior without requiring direct use of those internals.

## 7. Optional Convenience Base Class

If the package ships a base context class, it should be convenience-only:

```python
class SQLAlchemyContextBase:
    dataloaders: Any
    selections: Any
```

Users should never have to subclass it just to be accepted by the library.

## 8. Recommended Schema Example

```python
import strawberry
import strawberry_chemist as sc


class AppContext:
    @asynccontextmanager
    async def get_session(self):
        async with sessionmaker() as session:
            yield session


schema = strawberry.Schema(
    query=Query,
    extensions=sc.extensions(),
)
```

This keeps Chemist focused on SQLAlchemy-aware GraphQL field behavior, not on owning the application's request context model.

## 9. `input()` And `mutation()`

The redesign should not promote the current `input()` and `mutation()` helpers as part of the stable package story.

Until there is a clear model-write contract, the package should keep the public focus on:

- read-side type declaration
- relationships
- computed fields
- filters
- ordering
- connections
- relay/node integration
