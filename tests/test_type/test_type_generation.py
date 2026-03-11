import datetime
import inspect
from typing import Optional, List

import pytest
import strawberry
from sqlalchemy import ForeignKey, Time, Interval, ARRAY, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

import strawberry_sqlalchemy


def test_raw_type():
    class Base(DeclarativeBase):  # noqa
        pass

    class Class1(Base):
        __tablename__ = "class1"
        int_field: Mapped[int] = mapped_column(primary_key=True)
        str_field: Mapped[str]

    @strawberry_sqlalchemy.type(model=Class1)
    class Node:
        int_field: int
        str_field: str

    assert Node.__strawberry_definition__.name == "Node"
    assert Node.__strawberry_definition__.fields[0].python_name == "int_field"
    assert Node.__strawberry_definition__.fields[1].python_name == "str_field"


def test_type_mismatch():
    class Base(DeclarativeBase):  # noqa
        pass

    with pytest.warns(UserWarning, match=r"type mismatch .*'str_field'"):

        class Class5(Base):
            __tablename__ = "class5"
            int_field: Mapped[int] = mapped_column(primary_key=True)
            str_field: Mapped[str]

        @strawberry_sqlalchemy.type(model=Class5)
        class Node:
            int_field: int
            str_field: int


def test_auto_scalars():
    """
    For type conversion info: https://strawberry.rocks/docs/concepts/typings#mapping-to-graphql-types
    :return:
    """

    class Base(DeclarativeBase):  # noqa
        pass

    class Class2(Base):
        __tablename__ = "class2"
        int_field: Mapped[int] = mapped_column(primary_key=True)
        str_field: Mapped[str]
        datetime_field: Mapped[datetime.datetime]
        date_field: Mapped[datetime.date]
        time_field = mapped_column(Time, nullable=False)
        timedelta_field = mapped_column(Interval, nullable=False)

    @strawberry_sqlalchemy.type(model=Class2)
    class Node:
        int_field: strawberry.auto
        str_field: strawberry.auto
        datetime_field: strawberry.auto
        date_field: strawberry.auto
        time_field: strawberry.auto
        timedelta_field: strawberry.auto

    assert Node.__strawberry_definition__.name == "Node"
    assert Node.__strawberry_definition__.fields[0].type == int
    assert Node.__strawberry_definition__.fields[1].type == str
    assert Node.__strawberry_definition__.fields[2].type == datetime.datetime
    assert Node.__strawberry_definition__.fields[3].type == datetime.date
    assert Node.__strawberry_definition__.fields[4].type == datetime.time
    assert Node.__strawberry_definition__.fields[5].type == str


def test_auto_optional():
    class Base(DeclarativeBase):  # noqa
        pass

    class Class3(Base):
        __tablename__ = "class3"
        int_field: Mapped[int] = mapped_column(primary_key=True)
        optional_str_field: Mapped[Optional[str]]

    @strawberry_sqlalchemy.type(model=Class3)
    class Node:
        int_field: strawberry.auto
        optional_str_field: strawberry.auto

    assert Node.__strawberry_definition__.fields[1].type == Optional[str]


def test_auto_nested_raises():
    class Base(DeclarativeBase):  # noqa
        pass

    with pytest.raises(NotImplementedError):

        class Class4(Base):
            __tablename__ = "class4"
            int_field: Mapped[int] = mapped_column(primary_key=True)
            optional_str_field: Mapped[Optional[str]]

        class Class4Child(Base):
            __tablename__ = "class4_child"
            int_field: Mapped[int] = mapped_column(primary_key=True)
            class4_id: Mapped[int] = mapped_column(ForeignKey("class4.int_field"))
            class4: Mapped[Class4] = relationship(Class4)

        @strawberry_sqlalchemy.type(model=Class4)
        class Node:
            int_field: strawberry.auto
            optional_str_field: strawberry.auto

        @strawberry_sqlalchemy.type(model=Class4Child)
        class NodeChild:
            int_field: strawberry.auto
            class4: strawberry.auto

        assert NodeChild.__strawberry_definition__.fields[1].type == Node


def test_auto_array_raises():
    class Base(DeclarativeBase):  # noqa
        pass

    with pytest.raises(NotImplementedError):

        class Class4(Base):
            __tablename__ = "class4"
            int_field: Mapped[int] = mapped_column(primary_key=True)
            optional_str_field: Mapped[List[str]] = mapped_column(ARRAY(String))

        @strawberry_sqlalchemy.type(model=Class4)
        class Node:
            int_field: strawberry.auto
            optional_str_field: strawberry.auto

        assert Node.__strawberry_definition__.fields[1].type == List


def test_scalar_graphql_resolver_is_not_awaitable():
    class Base(DeclarativeBase):  # noqa
        pass

    class Class6(Base):
        __tablename__ = "class6"
        int_field: Mapped[int] = mapped_column(primary_key=True)
        str_field: Mapped[str]

    @strawberry_sqlalchemy.type(model=Class6)
    class Node:
        int_field: int
        str_field: str

    @strawberry.type
    class Query:
        @strawberry.field
        def node(self) -> Node:
            return Class6(int_field=1, str_field="value")

    schema = strawberry.Schema(query=Query)
    gql_node = schema._schema.get_type("Node")
    int_field_resolver = gql_node.fields["intField"].resolve

    result = int_field_resolver(Class6(int_field=1, str_field="value"))

    assert result == 1
    assert not inspect.isawaitable(result)


def test_array_explicit():
    class Base(DeclarativeBase):  # noqa
        pass

    class Class4(Base):
        __tablename__ = "class4"
        int_field: Mapped[int] = mapped_column(primary_key=True)
        optional_str_field: Mapped[List[str]] = mapped_column(ARRAY(String))

    @strawberry_sqlalchemy.type(model=Class4)
    class Node:
        int_field: strawberry.auto
        optional_str_field: List[str]

    assert Node.__strawberry_definition__.fields[1].type == List[str]
