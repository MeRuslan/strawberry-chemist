from collections import defaultdict

from strawberry.extensions import SchemaExtension

from strawberry_sqlalchemy.gql_context import SQLAlchemyContext, context_var
from strawberry_sqlalchemy.loaders import DataLoaderContainer


class DataLoadersExtension(SchemaExtension):
    def on_operation(self):
        context: SQLAlchemyContext = self.execution_context.context
        context.dataloader_container = DataLoaderContainer()
        context_var.set(context)
        yield None


class InfoCacheExtension(SchemaExtension):
    def on_operation(self):
        context: SQLAlchemyContext = self.execution_context.context
        context.field_sub_selections = defaultdict(set)
        yield None
