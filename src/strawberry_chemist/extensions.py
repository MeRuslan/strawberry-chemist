from __future__ import annotations

from collections import defaultdict
from collections.abc import AsyncGenerator, Generator

from strawberry.extensions import SchemaExtension

from .gql_context import SQLAlchemyContext, _LoaderSessionManager, context_var
from .loaders import DataLoaderContainer
from .settings import get_use_single_loader_session


class DataLoadersExtension(SchemaExtension):
    async def on_operation(self) -> AsyncGenerator[None, None]:
        context: SQLAlchemyContext = self.execution_context.context
        context.dataloader_container = DataLoaderContainer()
        context_var.set(context)
        context.loader_session = None
        context.loader_session_manager = None

        if not get_use_single_loader_session():
            yield None
            return

        async with context.get_session() as session:
            manager = _LoaderSessionManager(context=context, session=session)
            context.loader_session = session
            context.loader_session_manager = manager
            try:
                yield None
            finally:
                await manager.begin_shutdown()
                context.loader_session = None
                context.loader_session_manager = None


class SelectionCacheExtension(SchemaExtension):
    def on_operation(self) -> Generator[None, None, None]:
        context: SQLAlchemyContext = self.execution_context.context
        context.field_sub_selections = defaultdict(set)
        context.selection_nodes_seen = set()
        yield None


# Backwards-compatible name kept for the pre-redesign surface.
InfoCacheExtension = SelectionCacheExtension


def extensions() -> list[type[SchemaExtension]]:
    return [DataLoadersExtension, SelectionCacheExtension]


__all__ = [
    "DataLoadersExtension",
    "SelectionCacheExtension",
    "InfoCacheExtension",
    "extensions",
]
