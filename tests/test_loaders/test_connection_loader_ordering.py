from typing import Optional, Sequence

from sqlalchemy import Integer, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from strawberry_sqlalchemy.loaders import ConnectionLoader


class Base(DeclarativeBase):
    pass


class SinglePkModel(Base):
    __tablename__ = "single_pk_model"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100))


class CompositePkModel(Base):
    __tablename__ = "composite_pk_model"

    left_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    right_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    label: Mapped[str] = mapped_column(String(100))


class DummyPagination:
    @staticmethod
    def paginate_query(query, _page):
        return query


class DummyConnection:
    def __init__(self, model, default_order_by: Optional[Sequence] = None):
        self.sqlalchemy_model = model
        self.default_order_by = default_order_by
        self.pre_filter = None
        self.order = None
        self.filter = None
        self.pagination = DummyPagination()


def build_query(model, default_order_by: Optional[Sequence] = None):
    loader = ConnectionLoader(
        connection=DummyConnection(model=model, default_order_by=default_order_by),
        relationship_property=None,
        page_input=(5, None),
        order_input=None,
        filter_input=None,
    )
    return loader.filtered_ordered_paginated_query()


def test_connection_loader_falls_back_to_primary_key_ordering():
    query = build_query(SinglePkModel)
    assert [str(c) for c in query._order_by_clauses] == ["single_pk_model.id"]


def test_connection_loader_uses_all_primary_key_columns_for_composite_pk():
    query = build_query(CompositePkModel)
    assert [str(c) for c in query._order_by_clauses] == [
        "composite_pk_model.left_id",
        "composite_pk_model.right_id",
    ]


def test_connection_loader_keeps_explicit_default_ordering():
    query = build_query(SinglePkModel, default_order_by=(SinglePkModel.name.desc(),))
    assert [str(c) for c in query._order_by_clauses] == [
        "single_pk_model.name DESC",
        "single_pk_model.id",
    ]


def test_connection_loader_keeps_explicit_multi_column_default_ordering():
    query = build_query(
        SinglePkModel,
        default_order_by=(SinglePkModel.name.asc(), SinglePkModel.id.desc()),
    )
    assert [str(c) for c in query._order_by_clauses] == [
        "single_pk_model.name ASC",
        "single_pk_model.id DESC",
    ]


def test_connection_loader_without_pk_and_without_explicit_order(monkeypatch):
    monkeypatch.setattr(SinglePkModel.__mapper__, "primary_key", ())

    query = build_query(SinglePkModel)
    assert [str(c) for c in query._order_by_clauses] == []
