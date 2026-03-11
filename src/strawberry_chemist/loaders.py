from abc import ABC
from itertools import groupby
from typing import (
    Callable,
    Any,
    List,
    Optional,
    Tuple,
    Dict,
    Set,
    Type,
    Iterable,
)

import sqlalchemy
from sqlalchemy import (
    select,
    true,
    values,
    column,
    tuple_,
    union_all,
    Select,
    ColumnElement,
    literal,
)
from sqlalchemy.orm import (
    RelationshipProperty,
    aliased,
    Load,
    DeclarativeMeta,
)
from sqlalchemy.sql import Values, visitors
from strawberry.dataloader import DataLoader

from strawberry_chemist.connection.base import SQLAlchemyBaseConnectionField
from strawberry_chemist.fields.field import (
    StrawberrySQLAlchemyField,
    StrawberrySQLAlchemyRelationField,
)
from strawberry_chemist.gql_context import context_var


def generate_via_field_loader_fn(model: Any, field_name: str = "id"):
    async def _via_id_loader(ids: List[int]) -> List[Optional[model]]:
        ctx = context_var.get()

        query = select(model).filter(getattr(model, field_name).in_(ids))
        async with ctx.get_session() as session:
            objs: Iterable[model] = (await session.scalars(query)).all()

        objs: Dict = {getattr(o, field_name): o for o in objs}
        return [objs.get(_id, None) for _id in ids]

    return _via_id_loader


class DataLoaderContainer:
    """
    A class that manages data loaders, which in turn is in the strawberry context, initiated on every request.
    """

    _loaders: Dict[Tuple[StrawberrySQLAlchemyField, Any], DataLoader]
    _named_loaders: Dict[str, DataLoader]

    def __init__(self):
        """
        Purge data loaders on each request, when container is initiated
        """
        self._loaders = {}
        self._named_loaders = {}

    def spawn_function_loader(self, loader_func: Callable, name: Any):
        if name not in self._named_loaders.keys():
            self._named_loaders[name] = DataLoader(
                load_fn=loader_func, max_batch_size=500
            )
        return self._named_loaders[name]

    def get_dataloader(
        self,
        field: StrawberrySQLAlchemyField,
        options: Optional[List[Tuple]] = None,
        loader_options: Optional[List[Tuple]] = None,
    ) -> DataLoader:
        """
        Gets the dataloader given wanted characteristics.
        :param field: the field for which to fetch the dataloader
        :param options: the list of options on the relation which alters results, i.e. pagination, order
        :return: dataloader for the filed with given options
        """
        if (field, options) not in self._loaders.keys():
            # I can cache created callables, although I don't think it matters that much
            if isinstance(field, StrawberrySQLAlchemyRelationField) and not isinstance(
                field, SQLAlchemyBaseConnectionField
            ):
                field: StrawberrySQLAlchemyRelationField
                self._loaders[(field, None)] = DataLoader(
                    RelationshipLoader(
                        field=field, relationship_property=field.relationship_property
                    )
                )
            elif isinstance(field, SQLAlchemyBaseConnectionField):
                order, page, filters = loader_options or options
                self._loaders[(field, options)] = DataLoader(
                    ConnectionLoader(
                        connection=field,
                        page_input=page,
                        order_input=order,
                        filter_input=filters,
                        relationship_property=field.relationship_property,
                    )
                )
        return self._loaders[(field, options)]


def local_key_sql_values(data: List[Any], local_cs: Set[ColumnElement]) -> Values:
    value_expr = values(
        *[column(l_c.name, l_c.type) for l_c in local_cs], name="parent_values"
    ).data(data)
    return value_expr


def restrict_fields(
    target: DeclarativeMeta, fields: List[ColumnElement], query: Select
):
    # TODO: efficiently load inheritance hierarchies
    #   can use selectin_polymorphic, but would have to execute a separate query per model manually
    #   https://docs.sqlalchemy.org/en/20/orm/queryguide/inheritance.html
    #   I'll need to parse fragments and figure out which fields are
    #   needed for which models
    #   UPD: https://github.com/sqlalchemy/sqlalchemy/issues/9373#issuecomment-1445341424
    if target.__mapper__.polymorphic_identity is None:
        return query.options(
            Load(target).load_only(*[getattr(target, field.key) for field in fields])
        )
    return query


def process_orm_results_for_dataload(
    results: List[Tuple], key_len: int, parent_keys: List[Tuple], default: Any = None
) -> List[Any]:
    # filter out results with all keys = None
    results = [
        result for result in results if any(el is not None for el in result[0:key_len])
    ]
    results = sorted(results, key=lambda x: x[0:key_len])
    grouped_results = groupby(results, lambda x: x[0:key_len])
    res_dict = {
        key: [result[key_len] for result in group] for key, group in grouped_results
    }
    flat = [res_dict.get(parent_key, default) for parent_key in parent_keys]
    # get rid of "[None]" results, they are possible when loading with values
    return [r_list if r_list != [None] else [] for r_list in flat]


def _extract_ordered_columns(
    order_by_clauses: Tuple[ColumnElement, ...],
) -> Set[ColumnElement]:
    ordered_columns: Set[ColumnElement] = set()

    def _collect_column(column):
        ordered_columns.add(column)
        ordered_columns.update(getattr(column, "proxy_set", (column,)))

    for clause in order_by_clauses:
        visitors.traverse(clause, {}, {"column": _collect_column})

    return ordered_columns


def add_primary_key_tie_breaker(query: Select, model: DeclarativeMeta) -> Select:
    pk_columns = tuple(model.__mapper__.primary_key)
    if not pk_columns:
        return query

    ordered_columns = _extract_ordered_columns(tuple(query._order_by_clauses))
    missing_pk_columns = [
        pk
        for pk in pk_columns
        if not any(
            proxy in ordered_columns for proxy in getattr(pk, "proxy_set", (pk,))
        )
    ]
    if missing_pk_columns:
        query = query.order_by(*missing_pk_columns)
    return query


class ChildrenLoadingStrategy:
    @staticmethod
    def construct_query(
        relationship_property: RelationshipProperty,
        parent_columns: Tuple[str, ...],
        parent_data: List[Tuple],
        query: Select,
    ):
        raise NotImplementedError

    @staticmethod
    def filter_all_nones(parent_data: List[Tuple]):
        return list(
            filter(lambda data: any(el is not None for el in data), parent_data)
        )

    @staticmethod
    def apply_secondary(
        query: Select,
        relationship_property: RelationshipProperty,
        remote_keys: Tuple[ColumnElement],
    ):
        # aliased_sec_join = relationship_property.secondaryjoin
        # fake_left = getattr(model, aliased_sec_join.left.key)
        assert len(relationship_property.secondary_synchronize_pairs) == 1, (
            "raise on composites, just to check"
        )
        remote_keys = list(
            filter(
                lambda x: x != relationship_property.secondaryjoin.right, remote_keys
            )
        )
        return query.join(
            relationship_property.secondary, relationship_property.secondaryjoin
        ), remote_keys


class ValuesLoadingStrategy(ChildrenLoadingStrategy):
    """
    Loads children using VALUES expression
    Supports secondaryjoin, supports composite keys, but!!
    Doesn't support arbitrary expressions in join conditions
    A composite primaryjoin is handled no problem
    """

    @staticmethod
    def construct_query(
        relationship_property: RelationshipProperty,
        parent_columns: Tuple[str, ...],
        parent_data: List[Tuple],
        query: Select,
    ):
        parent_data_local = ValuesLoadingStrategy.filter_all_nones(parent_data)
        if not parent_data_local:
            return query.where(sqlalchemy.false()), relationship_property.entity.entity

        model = relationship_property.entity.entity
        local_keys, remote_keys = zip(*relationship_property.local_remote_pairs)

        if relationship_property.secondary is not None:
            query, remote_keys = ValuesLoadingStrategy.apply_secondary(
                query, relationship_property, remote_keys
            )
            # limit local_keys len to match remote_keys len
            local_keys = local_keys[: len(remote_keys)]

        # reorder local keys to match parent data order
        local_keys, remote_keys = zip(
            *sorted(
                zip(local_keys, remote_keys),
                key=lambda x: parent_columns.index(x[0].key),
            )
        )
        value_expr = local_key_sql_values(parent_data_local, local_keys)

        # assert len(remote_keys) == 1, "raise on composites, second guard"
        for r, v in zip(list(remote_keys), list(value_expr.c)):
            query = query.filter(r == v)
        query = query.lateral()
        # alias the related model from lateral query to return it
        related_alias = aliased(model, query)
        result_q = select(value_expr, related_alias).select_from(
            value_expr.outerjoin(query, true())
        )
        return result_q, related_alias


class UnionLoadingStrategy(ChildrenLoadingStrategy):
    literal_value_name = "parent_keys"

    @staticmethod
    def construct_query(
        relationship_property: RelationshipProperty,
        parent_columns: Tuple[str, ...],
        parent_data: List[Tuple],
        query: Select,
    ):
        parent_data_local = UnionLoadingStrategy.filter_all_nones(parent_data)
        if not parent_data_local:
            return query.where(sqlalchemy.false()), relationship_property.entity.entity

        model = relationship_property.entity.entity
        local_keys, remote_keys = zip(*relationship_property.local_remote_pairs)

        if relationship_property.secondary is not None:
            query, remote_keys = UnionLoadingStrategy.apply_secondary(
                query, relationship_property, remote_keys
            )

        assert len(remote_keys) == 1, "raise on composites, second guard"
        q_list = []
        for parent_keys in parent_data_local:
            labeled_parent_value = literal(list(parent_keys)[0]).label(
                UnionLoadingStrategy.literal_value_name
            )
            query_with_key_field = query.add_columns(labeled_parent_value)
            union_item_s = query_with_key_field.filter(
                tuple_(*list(remote_keys)) == tuple_(*[labeled_parent_value])
            ).subquery()
            q_list.append(select(union_item_s))
        union = union_all(*q_list)
        union_sub = union.subquery()
        related_alias = aliased(model, union_sub)
        parent_keys = getattr(union_sub.c, UnionLoadingStrategy.literal_value_name)

        f_sq = select(parent_keys, related_alias).select_from(union_sub)
        return f_sq, related_alias


class LoadViaParents(ABC):
    relationship_property: RelationshipProperty
    loading_strategy: Type[ChildrenLoadingStrategy] = ValuesLoadingStrategy

    @staticmethod
    def resolve_loading_strategy(
        dialect_name: Optional[str],
        loading_strategy: Type[ChildrenLoadingStrategy],
    ) -> Type[ChildrenLoadingStrategy]:
        if dialect_name == "sqlite" and loading_strategy is ValuesLoadingStrategy:
            return UnionLoadingStrategy
        return loading_strategy

    def extract_parents_keys(
        self, parents: List[Any]
    ) -> Tuple[Tuple[str, ...], List[Tuple]]:
        local_columns_names: tuple[str, ...] = tuple(
            l_c.key for l_c in self.relationship_property.local_columns
        )
        return local_columns_names, [
            tuple(obj.__getattribute__(key) for key in local_columns_names)
            for obj in parents
        ]

    async def load(
        self,
        parents: List[Any],
        fields_to_load: List[ColumnElement],
        children_query: Select,
    ) -> List[Any]:
        if self.relationship_property.distinct_target_key:
            children_query = children_query.distinct()

        ctx = context_var.get()
        local_columns = self.relationship_property.local_columns
        local_columns_len = len(local_columns)
        parent_c_names, parent_c_data = self.extract_parents_keys(parents)
        async with ctx.get_session() as asession:
            bind = asession.get_bind()
            loading_strategy = self.resolve_loading_strategy(
                bind.dialect.name if bind is not None else None,
                self.loading_strategy,
            )
            result_q, res_alias = loading_strategy.construct_query(
                self.relationship_property,
                parent_c_names,
                parent_c_data,
                children_query,
            )
            result_q = restrict_fields(res_alias, fields_to_load, result_q)
            results = await asession.execute(result_q)

        return process_orm_results_for_dataload(
            results, local_columns_len, parent_c_data, default=[]
        )


class RelationshipLoader(LoadViaParents, Callable):
    """
    The loader class that handles case of a sqlalchemy-defined relationship.
    """

    def __init__(
        self,
        field: StrawberrySQLAlchemyRelationField,
        relationship_property: RelationshipProperty,
        default: Optional[Any] = None,
    ):
        self.field = field
        self.default = default
        self.relationship_property = relationship_property

    def filtered_ordered_query(self):
        query = select(self.relationship_property.mapper)
        if self.field.where:
            for f in self.field.where:
                query = query.filter(f)
        elif self.relationship_property and self.relationship_property.order_by:
            query = query.order_by(*self.relationship_property.order_by)
        return query

    async def __call__(self, parents: List) -> List:
        query_base = self.filtered_ordered_query()
        fields_to_load = self.field.get_select_fields()
        res_flat = await self.load(
            parents=parents, fields_to_load=fields_to_load, children_query=query_base
        )

        if not self.relationship_property.uselist:
            res_flat = [r[0] if r else None for r in res_flat]

        return res_flat


class ConnectionLoader(LoadViaParents, Callable):
    """
    The loader class that handles a complex connections.
    """

    def __init__(
        self,
        connection: SQLAlchemyBaseConnectionField,
        relationship_property: RelationshipProperty,
        page_input: Optional[Tuple],
        order_input: Optional[Tuple],
        filter_input: Optional[Tuple],
        default: Optional[Any] = None,
    ):
        self.default = default
        self.connection = connection
        self.relationship_property = relationship_property
        self.page_input = page_input
        self.order_input = order_input
        self.filter_input = filter_input

    def filtered_ordered_query(self):
        model = self.connection.sqlalchemy_model
        # form target model query
        query = select(model)

        if self.connection.where:
            for f in self.connection.where:
                query = query.filter(f)
        # order using user input or defaults provided by relationship/connection.
        if self.order_input:
            query = self.connection.order.order_query(query, self.order_input)
        elif self.relationship_property and self.relationship_property.order_by:
            query = query.order_by(*self.relationship_property.order_by)
        elif self.connection.default_order_by is not None:
            query = query.order_by(*self.connection.default_order_by)

        if self.filter_input:
            query = self.connection.filter.filter_query(query, self.filter_input)

        # always append PK columns as final tiebreakers to keep pagination deterministic.
        query = add_primary_key_tie_breaker(query, model=model)

        return query

    def filtered_ordered_paginated_query(self):
        return self.connection.pagination.paginate_query(
            self.filtered_ordered_query(), self.page_input
        )

    def paginate_result(self, result, *, total_count: int = 0):
        if getattr(self.connection.pagination, "include_total_count", False):
            return self.connection.pagination.paginate_result(
                result,
                total_count=total_count,
            )
        return self.connection.pagination.paginate_result(result)

    async def load_root_connection(self, fields: List[ColumnElement], query: Select):
        # just a simple connection; a root query, no need to data load
        ctx = context_var.get()
        model = self.connection.sqlalchemy_model
        result_q = restrict_fields(
            model,
            fields,
            self.connection.pagination.paginate_query(query, self.page_input),
        )
        async with ctx.get_session() as asession:
            total_count = 0
            if getattr(self.connection.pagination, "include_total_count", False):
                total_count = (
                    await asession.execute(
                        self.connection.pagination.count_query(query)
                    )
                ).scalar_one()
            results = await asession.execute(result_q)
            result = self.paginate_result(
                results.scalars().all(), total_count=total_count
            )
            return [result]

    async def __call__(self, parents: List[Any]):
        fields = self.connection.get_select_fields()
        query = self.filtered_ordered_query()
        paginated_query = self.connection.pagination.paginate_query(
            query, self.page_input
        )

        assert self.relationship_property or not any(parents), (
            "Impossible: raise on to_load if no relationship"
        )

        if not self.relationship_property:
            return await self.load_root_connection(fields=fields, query=query)

        res_flat = await self.load(
            parents=parents, fields_to_load=fields, children_query=paginated_query
        )

        for i in range(len(res_flat)):
            res_flat[i] = self.paginate_result(
                res_flat[i],
                total_count=len(res_flat[i]),
            )

        return res_flat
