import datetime
import inspect
from dataclasses import dataclass
from typing import Optional, List

import pytest
import strawberry
from sqlalchemy import ForeignKey, Time, Interval, ARRAY, String
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    composite,
    mapped_column,
    relationship,
)

import strawberry_chemist


def test_raw_type():
    class Base(DeclarativeBase):  # noqa
        pass

    class Class1(Base):
        __tablename__ = "class1"
        int_field: Mapped[int] = mapped_column(primary_key=True)
        str_field: Mapped[str]

    @strawberry_chemist.type(model=Class1)
    class Node:
        int_field: int
        str_field: str

    assert Node.__strawberry_definition__.name == "Node"
    assert Node.__strawberry_definition__.fields[0].python_name == "int_field"
    assert Node.__strawberry_definition__.fields[1].python_name == "str_field"


def test_raw_type_supports_composite_proxy_descriptors():
    class Base(DeclarativeBase):  # noqa
        pass

    @dataclass
    class BirthDateValue:
        year: int
        month: int
        day: int

    class Character(Base):
        __tablename__ = "character_with_composite_birth_date"
        id: Mapped[int] = mapped_column(primary_key=True)
        birth_year: Mapped[int] = mapped_column()
        birth_month: Mapped[int] = mapped_column()
        birth_day: Mapped[int] = mapped_column()
        birth_date: Mapped[BirthDateValue] = composite(
            BirthDateValue,
            birth_year,
            birth_month,
            birth_day,
        )

    @strawberry.type
    class BirthDate:
        year: int
        month: int
        day: int

    @strawberry_chemist.type(model=Character)
    class CharacterNode:
        id: int
        birth_date: BirthDate

    @strawberry.type
    class Query:
        @strawberry.field
        def character(self) -> CharacterNode:
            return Character(
                id=1,
                birth_date=BirthDateValue(year=1980, month=1, day=2),
            )

    schema = strawberry.Schema(query=Query)
    result = schema.execute_sync("{ character { birthDate { year month day } } }")

    assert result.errors is None
    assert result.data == {
        "character": {
            "birthDate": {
                "year": 1980,
                "month": 1,
                "day": 2,
            }
        }
    }


def test_type_mismatch():
    class Base(DeclarativeBase):  # noqa
        pass

    with pytest.warns(UserWarning, match=r"type mismatch .*'str_field'"):

        class Class5(Base):
            __tablename__ = "class5"
            int_field: Mapped[int] = mapped_column(primary_key=True)
            str_field: Mapped[str]

        @strawberry_chemist.type(model=Class5)
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

    @strawberry_chemist.type(model=Class2)
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

    @strawberry_chemist.type(model=Class3)
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

        @strawberry_chemist.type(model=Class4)
        class Node:
            int_field: strawberry.auto
            optional_str_field: strawberry.auto

        @strawberry_chemist.type(model=Class4Child)
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

        @strawberry_chemist.type(model=Class4)
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

    @strawberry_chemist.type(model=Class6)
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

    @strawberry_chemist.type(model=Class4)
    class Node:
        int_field: strawberry.auto
        optional_str_field: List[str]

    assert Node.__strawberry_definition__.fields[1].type == List[str]
