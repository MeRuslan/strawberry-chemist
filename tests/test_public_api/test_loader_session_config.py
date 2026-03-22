import asyncio
from contextlib import asynccontextmanager
from types import SimpleNamespace

import pytest

import strawberry_chemist as sc
from strawberry_chemist.extensions import DataLoadersExtension
from strawberry_chemist.gql_context import SQLAlchemyContext, get_loader_session


@pytest.fixture(autouse=True)
def reset_sc_config():
    sc.reset_config()
    yield
    sc.reset_config()


class FakeContext(SQLAlchemyContext):
    def __init__(self) -> None:
        super().__init__(request=None)
        self.enter_count = 0
        self.exit_count = 0
        self.sessions = []

    @asynccontextmanager
    async def get_session(self):
        self.enter_count += 1
        session = object()
        self.sessions.append(session)
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


@pytest.mark.asyncio
async def test_shared_loader_session_shutdown_waits_for_active_borrower() -> None:
    sc.configure(use_single_loader_session=True)
    context = FakeContext()
    operation = await _open_operation(context)
    acquired = asyncio.Event()
    release = asyncio.Event()

    async def hold_loader_session() -> None:
        async with get_loader_session(context):
            acquired.set()
            await release.wait()

    holder_task = asyncio.create_task(hold_loader_session())
    await acquired.wait()

    close_task = asyncio.create_task(_close_operation(operation))
    await asyncio.sleep(0)

    assert not close_task.done()
    assert context.enter_count == 1
    assert context.exit_count == 0

    release.set()
    await holder_task
    await close_task

    assert context.exit_count == 1


@pytest.mark.asyncio
async def test_shared_loader_session_shutdown_falls_back_to_new_session(
    caplog: pytest.LogCaptureFixture,
) -> None:
    sc.configure(use_single_loader_session=True)
    context = FakeContext()
    operation = await _open_operation(context)
    acquired = asyncio.Event()
    release = asyncio.Event()
    shared_session_holder = {}

    async def hold_loader_session() -> None:
        async with get_loader_session(context) as session:
            shared_session_holder["session"] = session
            acquired.set()
            await release.wait()

    holder_task = asyncio.create_task(hold_loader_session())
    await acquired.wait()

    manager = context.loader_session_manager
    assert manager is not None

    close_task = asyncio.create_task(_close_operation(operation))
    while not manager.is_closing:
        await asyncio.sleep(0)

    caplog.set_level("ERROR")
    async with get_loader_session(context) as fallback_session:
        assert fallback_session is not shared_session_holder["session"]
        assert context.enter_count == 2
        assert context.exit_count == 0

    async with get_loader_session(context) as second_fallback_session:
        assert second_fallback_session is not shared_session_holder["session"]
        assert second_fallback_session is not fallback_session
        assert context.enter_count == 3
        assert context.exit_count == 1

    error_messages = [record.getMessage() for record in caplog.records]
    assert any(
        [
            "Chemist shared loader session is shutting down; using" in error
            for error in error_messages
        ]
    )

    assert context.exit_count == 2

    release.set()
    await holder_task
    await close_task

    assert context.exit_count == 3
