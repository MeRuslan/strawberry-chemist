import asyncio
import logging
from contextlib import asynccontextmanager
from contextvars import ContextVar
from typing import Any, Optional, AsyncGenerator, Dict, Set, TYPE_CHECKING

from sqlalchemy.ext.asyncio import AsyncSession


if TYPE_CHECKING:
    from strawberry_chemist.loaders import DataLoaderContainer


logger = logging.getLogger(__name__)


class _LoaderSessionManager:
    # Shared loader sessions need two separate coordination paths:
    # serialize normal use, then drain current borrowers before teardown closes.
    def __init__(self, context: "SQLAlchemyContext", session: AsyncSession) -> None:
        self._context = context
        self._session = session
        self._borrow_lock = asyncio.Lock()
        self._state_condition = asyncio.Condition()
        self._active_borrowers = 0
        self._closing = False

    @property
    def borrow_lock(self) -> asyncio.Lock:
        return self._borrow_lock

    @property
    def is_closing(self) -> bool:
        return self._closing

    async def begin_shutdown(self) -> None:
        async with self._state_condition:
            self._closing = True
            while self._active_borrowers > 0:
                await self._state_condition.wait()

    @asynccontextmanager
    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        async with self._state_condition:
            use_shared_session = not self._closing
            if use_shared_session:
                self._active_borrowers += 1

        if not use_shared_session:
            logger.error(
                "Chemist shared loader session is shutting down; using a unique "
                "short-lived AsyncSession for late internal loader work."
            )
            async with self._context.get_session() as session:
                yield session
            return

        try:
            async with self._borrow_lock:
                yield self._session
        finally:
            async with self._state_condition:
                self._active_borrowers -= 1
                self._state_condition.notify_all()


@asynccontextmanager
def get_session(*args, **kwargs) -> AsyncGenerator[AsyncSession, None]:
    raise NotImplementedError("You have to define get_session for your context")


@asynccontextmanager
async def get_loader_session(
    context: "SQLAlchemyContext",
) -> AsyncGenerator[AsyncSession, None]:
    manager = context.loader_session_manager
    if manager is None:
        async with context.get_session() as session:
            yield session
        return

    async with manager.get_session() as session:
        yield session


class SQLAlchemyContext:
    # gets populated at each context initialization
    dataloader_container: "DataLoaderContainer"
    field_sub_selections: Dict[Any, Set[str]]
    # (field, query node) pairs whose sub-selections are already collected
    selection_nodes_seen: Set[Any]
    user: Optional[Any]
    loader_session: AsyncSession | None = None
    loader_session_lock: asyncio.Lock | None = None
    loader_session_manager: _LoaderSessionManager | None = None
    get_session = get_session

    def __init__(self, request, *args, **kwargs):
        # each initialization will hereby create DataLoaders needed for the request
        self.loader_session = None
        self.loader_session_lock = None
        self.loader_session_manager = None


context_var: ContextVar[SQLAlchemyContext] = ContextVar("strawberry_context")
