from typing import Optional, Type

import pytest
from sqlalchemy import ForeignKey, select
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from strawberry_sqlalchemy import relation_field
from strawberry_sqlalchemy.loaders import (
    UnionLoadingStrategy,
    RelationshipLoader,
    ValuesLoadingStrategy, ChildrenLoadingStrategy
)


class Base(DeclarativeBase): # noqa
    pass


class Parent(Base):
    __tablename__ = "parent"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str]
    child_id: Mapped[Optional[int]] = mapped_column(ForeignKey("child.id"))
    child: Mapped["Child"] = relationship("Child")

    def __str__(self):
        return f"Parent: {self.name}"


class Child(Base):
    __tablename__ = "child"
    id: Mapped[int] = mapped_column(primary_key=True)
    child_name: Mapped[str]
    parent: Mapped["Parent"] = relationship("Parent", back_populates='child')

    def __str__(self):
        return f"Child: {self.child_name}"


@pytest.fixture
async def data_session(mock_psql_sqla_session):
    async with mock_psql_sqla_session as session:
        async with session.begin():
            await (await session.connection()).run_sync(Base.metadata.create_all)

    async with mock_psql_sqla_session as session:
        async with session.begin():
            c1 = Child(child_name="c1")
            c2 = Child(child_name="c2")

            p1 = Parent(name="p1", child=c1)
            p2 = Parent(name="p2", child=c2)
            p3 = Parent(name="p3")
            p4 = Parent(name="p4")
            p5 = Parent(name="p5")
            session.add_all([
                c1, c2, p1, p2, p3, p4, p5
            ])

    yield mock_psql_sqla_session


@pytest.fixture
def field_and_relation():
    field = relation_field()
    field.load_full = True
    field.relationship_property = Parent.child.prop
    rel_load = RelationshipLoader(relationship_property=Parent.child.prop, field=field)
    return rel_load


def strat_gen_t3(strat: Type[ChildrenLoadingStrategy]):
    @pytest.mark.asyncio
    async def test_load_children_for_one_empty_link(
            data_session, mock_context_var, field_and_relation):
        # fails union strat if there's no cleaning nulls up
        field_and_relation.loading_strategy = strat
        async with data_session as session: # noqa
            p2: Parent = (await session.execute(select(Parent).where(Parent.name == "p2"))).scalar_one()
            p3: Parent = (await session.execute(select(Parent).where(Parent.name == "p3"))).scalar_one()
            c2: Child = (await session.execute(select(Child).where(Child.child_name == "c2"))).scalar_one()
        list_of_children_by_parent = await field_and_relation.__call__([p3, p2])

        assert len(list_of_children_by_parent) == 2
        kid_p3 = list_of_children_by_parent[0]
        assert kid_p3 is None
        kids_p2 = list_of_children_by_parent[1]
        assert kids_p2.id == c2.id

    return test_load_children_for_one_empty_link


test_load_children_for_one_none_key_union = strat_gen_t3(UnionLoadingStrategy)
test_load_children_for_one_none_key_values = strat_gen_t3(ValuesLoadingStrategy)


def strat_gen_t4(strat: Type[ChildrenLoadingStrategy]):
    @pytest.mark.asyncio
    async def test_load_children_empty_all(
            data_session, mock_context_var, field_and_relation):
        # fails values strat if there's no cleaning nulls up
        field_and_relation.loading_strategy = strat
        async with data_session as session:  # noqa
            p4: Parent = (await session.execute(select(Parent).where(Parent.name == "p4"))).scalar_one()
            p3: Parent = (await session.execute(select(Parent).where(Parent.name == "p3"))).scalar_one()
            # p2: Parent = (await session.execute(select(Parent).where(Parent.name == "p2"))).scalar_one()
        list_of_children_by_parent = await field_and_relation.__call__([p3, p4])

        assert len(list_of_children_by_parent) == 2
        kid_p3 = list_of_children_by_parent[0]
        assert kid_p3 is None
        kids_p2 = list_of_children_by_parent[1]
        assert kids_p2 is None
        # kids_p2 = list_of_children_by_parent[2]
        # assert kids_p2 is not None
    return test_load_children_empty_all


test_load_children_all_keys_none_union = strat_gen_t4(UnionLoadingStrategy)
test_load_children_all_keys_none_values = strat_gen_t4(ValuesLoadingStrategy)
