from contextlib import asynccontextmanager
from contextvars import ContextVar
from typing import Any, Optional, AsyncGenerator, Dict, Set, TYPE_CHECKING

from sqlalchemy.ext.asyncio import AsyncSession


if TYPE_CHECKING:
    from strawberry_chemist.loaders import DataLoaderContainer


@asynccontextmanager
def get_session(*args, **kwargs) -> AsyncGenerator[AsyncSession, None]:
    raise NotImplementedError("You have to define get_session for your context")


class SQLAlchemyContext:
    # gets populated at each context initialization
    dataloader_container: "DataLoaderContainer"
    field_sub_selections: Dict[Any, Set[str]]
    user: Optional[Any]
    get_session = get_session

    def __init__(self, request, *args, **kwargs):
        # each initialization will hereby create DataLoaders needed for the request
        pass


context_var: ContextVar[SQLAlchemyContext] = ContextVar("strawberry_context")
