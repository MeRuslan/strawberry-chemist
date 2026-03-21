from contextlib import asynccontextmanager
from types import SimpleNamespace

import pytest

import strawberry_chemist as sc
from strawberry_chemist.extensions import DataLoadersExtension
from strawberry_chemist.gql_context import SQLAlchemyContext, get_loader_session


class FakeContext(SQLAlchemyContext):
    def __init__(self) -> None:
        super().__init__(request=None)
        self.enter_count = 0
        self.exit_count = 0

    @asynccontextmanager
    async def get_session(self):
        self.enter_count += 1
        session = object()
        try:
            yield session
        finally:
            self.exit_count += 1


async def _open_operation(context: FakeContext):
    extension = DataLoadersExtension()
    extension.execution_context = SimpleNamespace(context=context)
    operation = extension.on_operation()
    await operation.__anext__()
    return operation


async def _close_operation(operation) -> None:
    with pytest.raises(StopAsyncIteration):
        await operation.__anext__()


@pytest.mark.asyncio
async def test_loader_sessions_open_per_use_by_default() -> None:
    context = FakeContext()
    operation = await _open_operation(context)

    try:
        async with get_loader_session(context) as first_session:
            pass
        async with get_loader_session(context) as second_session:
            pass
    finally:
        await _close_operation(operation)

    assert first_session is not second_session
    assert context.enter_count == 2
    assert context.exit_count == 2


@pytest.mark.asyncio
async def test_configured_loader_sessions_reuse_one_session_per_operation() -> None:
    sc.configure(use_single_loader_session=True)
    context = FakeContext()
    operation = await _open_operation(context)

    try:
        async with get_loader_session(context) as first_session:
            pass
        async with get_loader_session(context) as second_session:
            pass

        assert first_session is second_session
        assert context.enter_count == 1
        assert context.exit_count == 0
    finally:
        await _close_operation(operation)

    assert context.exit_count == 1
