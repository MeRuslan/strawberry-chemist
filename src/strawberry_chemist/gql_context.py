import asyncio
from contextlib import asynccontextmanager
from contextvars import ContextVar
from typing import Any, Optional, AsyncGenerator, Dict, Set, TYPE_CHECKING

from sqlalchemy.ext.asyncio import AsyncSession


if TYPE_CHECKING:
    from strawberry_chemist.loaders import DataLoaderContainer


@asynccontextmanager
def get_session(*args, **kwargs) -> AsyncGenerator[AsyncSession, None]:
    raise NotImplementedError("You have to define get_session for your context")


@asynccontextmanager
async def get_loader_session(
    context: "SQLAlchemyContext",
) -> AsyncGenerator[AsyncSession, None]:
    if context.loader_session is None:
        async with context.get_session() as session:
            yield session
        return

    # AsyncSession is not safe for concurrent use, so shared loader access
    # must serialize around the request-local session.
    if context.loader_session_lock is None:
        yield context.loader_session
        return

    async with context.loader_session_lock:
        yield context.loader_session


class SQLAlchemyContext:
    # gets populated at each context initialization
    dataloader_container: "DataLoaderContainer"
    field_sub_selections: Dict[Any, Set[str]]
    user: Optional[Any]
    loader_session: AsyncSession | None = None
    loader_session_lock: asyncio.Lock | None = None
    get_session = get_session

    def __init__(self, request, *args, **kwargs):
        # each initialization will hereby create DataLoaders needed for the request
        self.loader_session = None
        self.loader_session_lock = None


context_var: ContextVar[SQLAlchemyContext] = ContextVar("strawberry_context")
