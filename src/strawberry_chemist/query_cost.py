from __future__ import annotations

import logging
from collections.abc import Callable, Generator, Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Final

from graphql import (
    DocumentNode,
    FieldNode,
    FragmentDefinitionNode,
    FragmentSpreadNode,
    GraphQLError,
    GraphQLField,
    GraphQLNamedType,
    GraphQLObjectType,
    GraphQLSchema,
    InlineFragmentNode,
    ListValueNode,
    ObjectValueNode,
    OperationDefinitionNode,
    SelectionNode,
    ValueNode,
    VariableNode,
    get_named_type,
    get_nullable_type,
    is_abstract_type,
    is_composite_type,
    is_list_type,
    parse,
)
from graphql import (
    ExecutionResult as GraphQLExecutionResult,
)
from graphql.utilities import value_from_ast_untyped
from strawberry.extensions import SchemaExtension

from strawberry_chemist.connection.base import SQLAlchemyBaseConnectionField

logger = logging.getLogger(__name__)

COST_METADATA_KEY: Final = "strawberry_chemist.cost"
STRAWBERRY_DEFINITION_KEY: Final = "strawberry-definition"
QUERY_COST_EXCEEDED: Final = "QUERY_COST_EXCEEDED"


@dataclass(frozen=True)
class QueryCost:
    """Worst case of one operation: `objects` is how many GraphQL objects
    (every `{...}` in the response, list items one by one) it may return,
    `fields` how many fields it may resolve."""

    objects: int
    fields: int


@dataclass(frozen=True)
class CostHint:
    list_size: int | None = None
    pagination: Any = None


def cost(*, list_size: int | None = None, pagination: Any = None) -> dict[str, Any]:
    """Field metadata telling the cost estimate how long a list field can be.

    `list_size`: the most items a plain list field returns.
    `pagination`: a pagination policy (`CursorPagination(...)`, `OffsetPagination(...)`)
    for a field that pages by itself (a resolver returning `sc.Connection`):
    its page size comes from the field's arguments like a `sc.connection`'s.

        @strawberry.field(metadata=sc.cost(list_size=5))
    """
    if (list_size is None) == (pagination is None):
        raise ValueError("sc.cost() takes either list_size or pagination")
    if list_size is not None and list_size < 0:
        raise ValueError("sc.cost() list_size must not be negative")
    return {COST_METADATA_KEY: CostHint(list_size=list_size, pagination=pagination)}


class QueryCostExceeded(Exception):
    def __init__(
        self, cost: QueryCost, max_objects: int | None, max_fields: int | None
    ):
        self.cost = cost
        self.max_objects = max_objects
        self.max_fields = max_fields
        over = []
        if max_objects is not None and cost.objects > max_objects:
            over.append(f"up to {cost.objects} objects (limit {max_objects})")
        if max_fields is not None and cost.fields > max_fields:
            over.append(f"up to {cost.fields} fields (limit {max_fields})")
        super().__init__(f"Query is too expensive: {', '.join(over)}")


class _Unknown:
    """A variable whose value the estimate doesn't have: the worst case is assumed."""


_UNKNOWN: Final = _Unknown()
_ABSENT: Final = object()


def _page_size(pagination: Any, arguments: Mapping[str, Any]) -> int | None:
    if hasattr(pagination, "page_size"):
        return pagination.page_size(arguments)
    return getattr(pagination, "max_limit", None)


class _Estimate:
    def __init__(
        self,
        schema: GraphQLSchema,
        fragments: Mapping[str, FragmentDefinitionNode],
        variables: Mapping[str, Any] | None,
        default_list_size: int,
    ):
        self.schema = schema
        self.fragments = fragments
        self.variables = variables
        self.default_list_size = default_list_size
        self.memo: dict[tuple[Any, ...], tuple[int, int]] = {}

    def value(self, node: ValueNode) -> Any:
        if isinstance(node, VariableNode):
            if self.variables is None:
                return _UNKNOWN
            return self.variables.get(node.name.value, _ABSENT)
        if isinstance(node, ObjectValueNode):
            fields = {f.name.value: self.value(f.value) for f in node.fields}
            return {k: v for k, v in fields.items() if v is not _ABSENT}
        if isinstance(node, ListValueNode):
            return [self.value(v) for v in node.values]
        return value_from_ast_untyped(node)

    def arguments(self, node: FieldNode) -> dict[str, Any]:
        values = {a.name.value: self.value(a.value) for a in node.arguments or ()}
        return {k: v for k, v in values.items() if v is not _ABSENT}

    def included(self, node: SelectionNode) -> bool:
        for directive in node.directives or ():
            name = directive.name.value
            if name not in ("skip", "include"):
                continue
            condition = next(
                (
                    self.value(a.value)
                    for a in directive.arguments or ()
                    if a.name.value == "if"
                ),
                _UNKNOWN,
            )
            if not isinstance(condition, bool):
                continue
            if condition == (name == "skip"):
                return False
        return True

    def applies(self, type_condition: str | None, concrete: GraphQLObjectType) -> bool:
        if type_condition is None or type_condition == concrete.name:
            return True
        condition = self.schema.get_type(type_condition)
        return is_abstract_type(condition) and self.schema.is_sub_type(
            condition, concrete
        )

    def collect(
        self,
        selections: Sequence[SelectionNode],
        concrete: GraphQLObjectType,
        out: dict[str, list[FieldNode]],
    ) -> dict[str, list[FieldNode]]:
        for selection in selections:
            if not self.included(selection):
                continue
            if isinstance(selection, FieldNode):
                key = selection.alias.value if selection.alias else selection.name.value
                out.setdefault(key, []).append(selection)
            elif isinstance(selection, InlineFragmentNode):
                condition = selection.type_condition
                if self.applies(condition.name.value if condition else None, concrete):
                    self.collect(selection.selection_set.selections, concrete, out)
            elif isinstance(selection, FragmentSpreadNode):
                fragment = self.fragments.get(selection.name.value)
                if fragment is not None and self.applies(
                    fragment.type_condition.name.value, concrete
                ):
                    self.collect(fragment.selection_set.selections, concrete, out)
        return out

    def page_size(
        self, field: GraphQLField, node: FieldNode
    ) -> tuple[int | None, int | None]:
        """(page size the field's list children get, size of the field's own list)"""
        definition = (field.extensions or {}).get(STRAWBERRY_DEFINITION_KEY)
        hint = (getattr(definition, "metadata", None) or {}).get(COST_METADATA_KEY)
        if isinstance(hint, CostHint):
            if hint.pagination is not None:
                return _page_size(hint.pagination, self.arguments(node)), None
            return None, hint.list_size
        if isinstance(definition, SQLAlchemyBaseConnectionField):
            return _page_size(definition.pagination, self.arguments(node)), None
        return None, None

    def unit(
        self,
        selections: Sequence[SelectionNode],
        type_: GraphQLNamedType,
        page: int | None,
    ) -> tuple[int, int]:
        """(objects, fields) under one object of `type_`; `page` is the page
        size of the connection `type_` is, taken by its list fields."""
        key = (tuple(map(id, selections)), type_.name, page)
        if key in self.memo:
            return self.memo[key]
        if is_abstract_type(type_):
            concretes = self.schema.get_possible_types(type_)
        else:
            concretes = [type_]  # type: ignore[list-item]
        worst_objects = worst_fields = 0
        for concrete in concretes:
            objects = fields = 0
            for nodes in self.collect(selections, concrete, {}).values():
                name = nodes[0].name.value
                if name.startswith("__"):
                    continue
                field = concrete.fields.get(name)
                if field is None:
                    continue
                fields += 1
                named = get_named_type(field.type)
                if not is_composite_type(named):
                    continue
                child_page, list_size = self.page_size(field, nodes[0])
                count = 1
                if is_list_type(get_nullable_type(field.type)):
                    if list_size is not None:
                        count = list_size
                    elif child_page is not None:
                        # a list paged by its own arguments, no connection type around it
                        count, child_page = child_page, None
                    elif page is not None:
                        count = page
                    else:
                        count = self.default_list_size
                subselections = [
                    s
                    for n in nodes
                    if n.selection_set
                    for s in n.selection_set.selections
                ]
                sub_objects, sub_fields = self.unit(subselections, named, child_page)
                objects += count * (1 + sub_objects)
                fields += count * sub_fields
            worst_objects = max(worst_objects, objects)
            worst_fields = max(worst_fields, fields)
        self.memo[key] = (worst_objects, worst_fields)
        return self.memo[key]


def _graphql_schema(schema: Any) -> GraphQLSchema:
    return schema if isinstance(schema, GraphQLSchema) else schema._schema


def estimate_query_cost(
    schema: Any,
    document: DocumentNode | str,
    operation_name: str | None = None,
    variables: Mapping[str, Any] | None = None,
    *,
    default_list_size: int = 1,
) -> QueryCost:
    """Worst-case cost of an operation, before running it.

    Pages are as large as the arguments ask, capped by the field's pagination
    policy; a plain list field counts `default_list_size` items unless it has
    `sc.cost(...)` metadata. Union and interface selections cost as much as
    the most expensive member type. `variables=None` assumes every variable
    at its worst (pages at `max_limit`), for checking documents ahead of time.
    """
    graphql_schema = _graphql_schema(schema)
    if isinstance(document, str):
        document = parse(document)
    operations = [
        d for d in document.definitions if isinstance(d, OperationDefinitionNode)
    ]
    if operation_name is not None:
        operations = [
            o for o in operations if o.name and o.name.value == operation_name
        ]
    if len(operations) != 1:
        raise ValueError("estimate_query_cost needs exactly one operation to estimate")
    operation = operations[0]
    if variables is not None:
        defaults = {
            d.variable.name.value: value_from_ast_untyped(d.default_value)
            for d in operation.variable_definitions or ()
            if d.default_value is not None
        }
        variables = {**defaults, **variables}
    fragments = {
        d.name.value: d
        for d in document.definitions
        if isinstance(d, FragmentDefinitionNode)
    }
    root = graphql_schema.get_root_type(operation.operation)
    if root is None:
        return QueryCost(objects=0, fields=0)
    estimate = _Estimate(graphql_schema, fragments, variables, default_list_size)
    objects, fields = estimate.unit(operation.selection_set.selections, root, None)
    return QueryCost(objects=objects, fields=fields)


class QueryCostLimiter(SchemaExtension):
    """Rejects operations whose worst case (see `estimate_query_cost`) is over
    `max_objects` or `max_fields`, before they run. `dry_run=True` only logs
    them; `callback` gets every operation's cost."""

    def __init__(
        self,
        *,
        max_objects: int | None = None,
        max_fields: int | None = None,
        default_list_size: int = 1,
        dry_run: bool = False,
        callback: Callable[[QueryCost, Any], None] | None = None,
        execution_context: Any = None,
    ):
        # older strawberry-graphql (0.311) builds extensions with execution_context=None;
        # the runner sets the real one either way
        del execution_context
        self.max_objects = max_objects
        self.max_fields = max_fields
        self.default_list_size = default_list_size
        self.dry_run = dry_run
        self.callback = callback

    def exceeds(self, cost: QueryCost) -> bool:
        return (self.max_objects is not None and cost.objects > self.max_objects) or (
            self.max_fields is not None and cost.fields > self.max_fields
        )

    def on_execute(self) -> Generator[None, None, None]:
        execution_context = self.execution_context
        document = execution_context.graphql_document
        if document is None or execution_context.result is not None:
            yield None
            return
        try:
            cost = estimate_query_cost(
                execution_context.schema,
                document,
                execution_context.operation_name,
                execution_context.variables or {},
                default_list_size=self.default_list_size,
            )
        except ValueError:
            # no single operation to run: execution reports that itself
            yield None
            return
        if self.callback is not None:
            self.callback(cost, execution_context)
        if self.exceeds(cost):
            error = QueryCostExceeded(cost, self.max_objects, self.max_fields)
            if self.dry_run:
                logger.warning(
                    "%s (operation %s, dry run)",
                    error,
                    execution_context.operation_name,
                )
            else:
                execution_context.result = GraphQLExecutionResult(
                    data=None,
                    errors=[
                        GraphQLError(
                            str(error),
                            original_error=error,
                            extensions={
                                "code": QUERY_COST_EXCEEDED,
                                "objects": cost.objects,
                                "fields": cost.fields,
                                "maxObjects": self.max_objects,
                                "maxFields": self.max_fields,
                            },
                        )
                    ],
                )
        yield None


__all__ = [
    "COST_METADATA_KEY",
    "QUERY_COST_EXCEEDED",
    "CostHint",
    "QueryCost",
    "QueryCostExceeded",
    "QueryCostLimiter",
    "cost",
    "estimate_query_cost",
]
