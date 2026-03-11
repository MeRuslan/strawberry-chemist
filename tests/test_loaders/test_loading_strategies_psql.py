from contextvars import ContextVar
from typing import Optional, List, Type

import pytest
from sqlalchemy import ForeignKey, select, or_
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, joinedload

from strawberry_sqlalchemy import relation_field
from strawberry_sqlalchemy.filters.pre_filter import RuntimeFilter
from strawberry_sqlalchemy.loaders import (
    UnionLoadingStrategy,
    LoadViaParents,
    process_orm_results_for_dataload,
    RelationshipLoader,
    ValuesLoadingStrategy,
    ChildrenLoadingStrategy,
)

pytestmark = pytest.mark.psql


class Base(DeclarativeBase): # noqa
    pass


class Association(Base):
    __tablename__ = "association_table"
    left_id: Mapped[int] = mapped_column(ForeignKey("parent.id"), primary_key=True)
    right_id: Mapped[int] = mapped_column(ForeignKey("child.id"), primary_key=True)


class Parent(Base):
    __tablename__ = "parent"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str]
    children: Mapped[List["Child"]] = relationship(
        secondary="association_table", back_populates="parents"
    )

    def __str__(self):
        return f"Parent: {self.name}"


class Child(Base):
    __tablename__ = "child"
    id: Mapped[int] = mapped_column(primary_key=True)
    child_name: Mapped[str]
    age: Mapped[Optional[int]]
    # parents_ass: Mapped[List["BookRole"]] = relationship(back_populates="child")
    parents: Mapped[List["Parent"]] = relationship(
        secondary="association_table", back_populates="children"
    )

    def __str__(self):
        return f"Child: {self.child_name}"


new_ctx = ContextVar("strawberry_context")


@pytest.fixture
async def data_session(mock_psql_sqla_session):
    async with mock_psql_sqla_session as session:
        async with session.begin():
            await (await session.connection()).run_sync(Base.metadata.create_all)

    async with mock_psql_sqla_session as session:
        async with session.begin():
            p1 = Parent(name="Victor")
            p2 = Parent(name="Victoria")
            p3 = Parent(name="Alex")
            p4 = Parent(name="Alice")
            p5 = Parent(name="Jack")
            p6 = Parent(name="Jane")
            p7 = Parent(name="Kate")
            p8 = Parent(name="Kamil")
            session.add_all([
                p1, p2, p3, p4, p5, p6, p7, p8
            ])
            session.add_all([
                Child(child_name="V1", age=12, parents=[p1, p2]),
                Child(child_name="V2", age=13, parents=[p1, p2]),
                Child(child_name="V3", age=14, parents=[p1, p2]),
                Child(child_name="V4", age=15, parents=[p1, p2]),
                Child(child_name="A1", age=9, parents=[p3, p4]),
                Child(child_name="A2", age=11, parents=[p3, p4]),
                Child(child_name="J2", age=11, parents=[p5, p6]),
            ])
    yield mock_psql_sqla_session


@pytest.fixture
def field_and_relation():
    field = relation_field()
    field.load_full = True
    field.relationship_property = Parent.children.prop
    rel_load = RelationshipLoader(relationship_property=Parent.children.prop, field=field)
    return rel_load


def strat_gen(strat: Type[ChildrenLoadingStrategy]):
    @pytest.mark.asyncio
    async def test_load_children_for_many_using_strategy(data_session):
        async with data_session as session: # noqa
            parents: List[Parent] = (await session.execute(select(Parent).where(
                or_(Parent.name == "Victor", Parent.name == "Jack", Parent.name == "Kamil", Parent.name == "Victoria")
            ).options(joinedload(Parent.children)))).unique().scalars().all()

        fake_load = LoadViaParents()
        fake_load.relationship_property = Parent.children.prop
        # victor, jack, kamil, victoria
        parent_c_name, parent_c_data = fake_load.extract_parents_keys(parents=parents)
        query, _ = strat.construct_query(
            Parent.children.prop, parent_columns=parent_c_name, parent_data=parent_c_data, query=select(Child)
        )
        async with data_session as session:
            data = await session.execute(query)
            data = process_orm_results_for_dataload(
                data, 1, parent_c_data, default=[]
            )

        for i, res in enumerate(data):
            # victor, jack, kamil, victoria
            cur_orm_parent = parents[i]
            cur_str_parent_children = res
            assert len(cur_orm_parent.children) == len(cur_str_parent_children)
            assert set([c.id for c in cur_orm_parent.children]) == set([c.id for c in cur_str_parent_children])
    return test_load_children_for_many_using_strategy


test_load_children_for_many_using_strategy_union = strat_gen(UnionLoadingStrategy)
test_load_children_for_many_using_strategy_values = strat_gen(ValuesLoadingStrategy)


def strat_gen_t2(strat: Type[ChildrenLoadingStrategy]):
    @pytest.mark.asyncio # noqa
    async def test_load_children_for_many_using_loader(data_session, mock_context_var, field_and_relation):
        rel_load = field_and_relation
        rel_load.loading_strategy = strat
        async with data_session as session: # noqa
            parents_only: List[Parent] = (await session.execute(select(Parent).where(
                or_(Parent.name == "Jack", Parent.name == "Kamil")
            ).options(joinedload(Parent.children)))).unique().scalars().all()
            parents_with_kids: List[Parent] = (await session.execute(select(Parent).where(
                or_(Parent.name == "Jack", Parent.name == "Kamil")
            ))).unique().scalars().all()

        list_of_children_by_parent = await rel_load.__call__(parents_only)

        pairs = {p1: p2 for p1 in parents_only for p2 in parents_with_kids if p1.id == p2.id}
        for i, children in enumerate(list_of_children_by_parent):
            orm_kids = pairs[parents_only[i]].children
            assert set(k.id for k in orm_kids) == set(c.id for c in children)
    return test_load_children_for_many_using_loader


test_load_children_for_many_using_loader_union = strat_gen_t2(UnionLoadingStrategy)
test_load_children_for_many_using_loader_values = strat_gen_t2(ValuesLoadingStrategy)


def strat_gen_t3(strat: Type[ChildrenLoadingStrategy]):
    @pytest.mark.asyncio
    async def test_load_children_for_many_using_loader_with_pre_filter(
            data_session, mock_context_var, field_and_relation, monkeypatch):
        field_and_relation.loading_strategy = strat
        async with data_session as session: # noqa
            alice: Parent = (await session.execute(select(Parent).where(Parent.name == "Alice"))).scalar_one()
            victor: Parent = (await session.execute(select(Parent).where(Parent.name == "Victor"))).scalar_one()
        with monkeypatch.context() as m:
            m.setattr(field_and_relation.field, "pre_filter", RuntimeFilter(filters=[
                lambda: Child.child_name.like("A2"),
            ]))
            list_of_children_by_parent = await field_and_relation.__call__([alice, victor])

        assert len(list_of_children_by_parent) == 2
        kids = list_of_children_by_parent[0]
        assert len(kids) == 1
        assert kids[0].child_name == "A2"
        kids = list_of_children_by_parent[1]
        assert len(kids) == 0

    return test_load_children_for_many_using_loader_with_pre_filter


test_load_children_for_many_using_loader_with_pre_filter_union = strat_gen_t3(UnionLoadingStrategy)
test_load_children_for_many_using_loader_with_pre_filter_values = strat_gen_t3(ValuesLoadingStrategy)
