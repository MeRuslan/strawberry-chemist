from __future__ import annotations

from collections import defaultdict
from collections.abc import Generator

from strawberry.extensions import SchemaExtension

from .gql_context import SQLAlchemyContext, context_var
from .loaders import DataLoaderContainer


class DataLoadersExtension(SchemaExtension):
    def on_operation(self) -> Generator[None, None, None]:
        context: SQLAlchemyContext = self.execution_context.context
        context.dataloader_container = DataLoaderContainer()
        context_var.set(context)
        yield None


class SelectionCacheExtension(SchemaExtension):
    def on_operation(self) -> Generator[None, None, None]:
        context: SQLAlchemyContext = self.execution_context.context
        context.field_sub_selections = defaultdict(set)
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
