from contextvars import ContextVar
from typing import Optional, List

import pytest
from sqlalchemy import ForeignKey, select, or_
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    mapped_column,
    relationship,
    joinedload,
)

from strawberry_chemist import relationship as chemist_relationship
from strawberry_chemist.gql_context import context_var
from strawberry_chemist.loaders import (
    UnionLoadingStrategy,
    LoadViaParents,
    process_orm_results_for_dataload,
    RelationshipLoader,
)


class Base(DeclarativeBase):  # noqa need the same code in psql tests
    pass


class Association(Base):
    __tablename__ = "association_table"
    left_id: Mapped[int] = mapped_column(
        ForeignKey("parent_through.id"), primary_key=True
    )
    right_id: Mapped[int] = mapped_column(
        ForeignKey("child_through.id"), primary_key=True
    )


class OneOrManyThrough(Base):
    __tablename__ = "parent_through"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str]
    children: Mapped[List["ManyThrough"]] = relationship(
        secondary="association_table", back_populates="parents"
    )

    def __str__(self):
        return f"Parent through: {self.name}"


class ManyThrough(Base):
    __tablename__ = "child_through"
    id: Mapped[int] = mapped_column(primary_key=True)
    child_name: Mapped[str]
    age: Mapped[Optional[int]]
    # parents_ass: Mapped[List["BookRole"]] = relationship(back_populates="child")
    parents: Mapped[List["OneOrManyThrough"]] = relationship(
        secondary="association_table", back_populates="children"
    )

    def __str__(self):
        return f"Child through: {self.child_name}"


new_ctx = ContextVar("strawberry_context")


@pytest.fixture
async def data_session(mock_sqlite_sqla_session):
    async with mock_sqlite_sqla_session as session:  # noqa need the same code in psql tests
        async with session.begin():
            await (await session.connection()).run_sync(Base.metadata.create_all)

    async with mock_sqlite_sqla_session as session:
        async with session.begin():
            p1 = OneOrManyThrough(name="Victor")
            p2 = OneOrManyThrough(name="Victoria")
            p3 = OneOrManyThrough(name="Alex")
            p4 = OneOrManyThrough(name="Alice")
            p5 = OneOrManyThrough(name="Jack")
            p6 = OneOrManyThrough(name="Jane")
            p7 = OneOrManyThrough(name="Kate")
            p8 = OneOrManyThrough(name="Kamil")
            session.add_all([p1, p2, p3, p4, p5, p6, p7, p8])
            session.add_all(
                [
                    ManyThrough(child_name="V1", age=12, parents=[p1, p2]),
                    ManyThrough(child_name="V2", age=13, parents=[p1, p2]),
                    ManyThrough(child_name="V3", age=14, parents=[p1, p2]),
                    ManyThrough(child_name="V4", age=15, parents=[p1, p2]),
                    ManyThrough(child_name="A1", age=9, parents=[p3, p4]),
                    ManyThrough(child_name="A2", age=11, parents=[p3, p4]),
                    ManyThrough(child_name="J2", age=11, parents=[p5, p6]),
                ]
            )
    yield mock_sqlite_sqla_session


@pytest.fixture
def field_and_relation(mock_sqlite_sqla_session):
    field = chemist_relationship(load="full")
    field.relationship_property = OneOrManyThrough.children.prop
    rel_load = RelationshipLoader(
        relationship_property=OneOrManyThrough.children.prop, field=field
    )
    return rel_load


@pytest.mark.asyncio
async def test_load_children_for_many_using_union_strategy_directly(data_session):
    async with data_session as session:  # noqa need the same code in psql tests
        parents: List[OneOrManyThrough] = (
            (
                await session.execute(
                    select(OneOrManyThrough)
                    .where(
                        or_(
                            OneOrManyThrough.name == "Victor",
                            OneOrManyThrough.name == "Jack",
                            OneOrManyThrough.name == "Kamil",
                            OneOrManyThrough.name == "Victoria",
                        )
                    )
                    .options(joinedload(OneOrManyThrough.children))
                )
            )
            .unique()
            .scalars()
            .all()
        )

    fake_load = LoadViaParents()
    fake_load.relationship_property = OneOrManyThrough.children.prop
    # victor, jack, kamil, victoria
    parent_c_names, parent_c_data = fake_load.extract_parents_keys(parents=parents)
    query, _ = UnionLoadingStrategy.construct_query(
        OneOrManyThrough.children.prop,
        parent_columns=parent_c_names,
        parent_data=parent_c_data,
        query=select(ManyThrough),
    )
    async with data_session as session:
        data = await session.execute(query)
        data = process_orm_results_for_dataload(data, 1, parent_c_data, default=[])

    for i, res in enumerate(data):
        # victor, jack, kamil, victoria
        cur_orm_parent = parents[i]
        cur_str_parent_children = res
        assert len(cur_orm_parent.children) == len(cur_str_parent_children)
        assert set([c.id for c in cur_orm_parent.children]) == set(
            [c.id for c in cur_str_parent_children]
        )


@pytest.mark.asyncio
async def test_load_children_for_many_using_loader(
    data_session, mock_context_var, field_and_relation
):
    rel_load = field_and_relation
    async with data_session as session:  # noqa need the same code in psql tests
        parents_only: List[OneOrManyThrough] = (
            (
                await session.execute(
                    select(OneOrManyThrough)
                    .where(
                        or_(
                            OneOrManyThrough.name == "Jack",
                            OneOrManyThrough.name == "Kamil",
                        )
                    )
                    .options(joinedload(OneOrManyThrough.children))
                )
            )
            .unique()
            .scalars()
            .all()
        )
        parents_with_kids: List[OneOrManyThrough] = (
            (
                await session.execute(
                    select(OneOrManyThrough).where(
                        or_(
                            OneOrManyThrough.name == "Jack",
                            OneOrManyThrough.name == "Kamil",
                        )
                    )
                )
            )
            .unique()
            .scalars()
            .all()
        )

    list_of_children_by_parent = await rel_load.__call__(parents_only)

    pairs = {
        p1: p2 for p1 in parents_only for p2 in parents_with_kids if p1.id == p2.id
    }
    for i, children in enumerate(list_of_children_by_parent):
        orm_kids = pairs[parents_only[i]].children
        assert set(k.id for k in orm_kids) == set(c.id for c in children)


@pytest.mark.asyncio
async def test_load_children_for_many_using_loader_with_where_clause(
    data_session, mock_context_var
):
    field = chemist_relationship(
        load="full",
        where=lambda: ManyThrough.child_name.like("A2"),
    )
    field.relationship_property = OneOrManyThrough.children.prop
    rel_load = RelationshipLoader(
        relationship_property=OneOrManyThrough.children.prop, field=field
    )
    async with data_session as session:  # noqa need the same code in psql tests
        alice: OneOrManyThrough = (
            await session.execute(
                select(OneOrManyThrough).where(OneOrManyThrough.name == "Alice")
            )
        ).scalar_one()
        victor: OneOrManyThrough = (
            await session.execute(
                select(OneOrManyThrough).where(OneOrManyThrough.name == "Victor")
            )
        ).scalar_one()
    list_of_children_by_parent = await rel_load.__call__([alice, victor])

    assert len(list_of_children_by_parent) == 2
    kids = list_of_children_by_parent[0]
    assert len(kids) == 1
    assert kids[0].child_name == "A2"
    kids = list_of_children_by_parent[1]
    assert len(kids) == 0


@pytest.mark.asyncio
async def test_load_children_for_many_using_loader_with_callable_where_clauses(
    data_session, mock_context_var
):
    context_var.get().user = type("User", (), {"id": 11})()

    field = chemist_relationship(
        load="full",
        where=[
            lambda: (
                ManyThrough.age == context_var.get().user.id
                if context_var.get().user
                else False
            ),
            lambda: ManyThrough.child_name.like("A%"),
        ],
    )
    field.relationship_property = OneOrManyThrough.children.prop
    rel_load = RelationshipLoader(
        relationship_property=OneOrManyThrough.children.prop, field=field
    )

    async with data_session as session:
        alice: OneOrManyThrough = (
            await session.execute(
                select(OneOrManyThrough).where(OneOrManyThrough.name == "Alice")
            )
        ).scalar_one()
        victor: OneOrManyThrough = (
            await session.execute(
                select(OneOrManyThrough).where(OneOrManyThrough.name == "Victor")
            )
        ).scalar_one()

    list_of_children_by_parent = await rel_load.__call__([alice, victor])

    assert len(list_of_children_by_parent) == 2
    kids = list_of_children_by_parent[0]
    assert len(kids) == 1
    assert kids[0].child_name == "A2"
    kids = list_of_children_by_parent[1]
    assert len(kids) == 0
