from typing import List

from sqlalchemy import ForeignKey, select
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from strawberry_chemist.loaders import (
    LoadViaParents,
    UnionLoadingStrategy,
    UnnestLoadingStrategy,
    ValuesLoadingStrategy,
)


class Base(DeclarativeBase):  # noqa
    pass


class Author(Base):
    __tablename__ = "unnest_author"
    id: Mapped[int] = mapped_column(primary_key=True)
    books: Mapped[List["Book"]] = relationship(back_populates="author")


class Book(Base):
    __tablename__ = "unnest_book"
    id: Mapped[int] = mapped_column(primary_key=True)
    author_id: Mapped[int] = mapped_column(ForeignKey("unnest_author.id"))
    author: Mapped[Author] = relationship(back_populates="books")


def build_children_query(parent_data):
    query, _ = UnnestLoadingStrategy.construct_query(
        Author.books.prop,
        parent_columns=("id",),
        parent_data=parent_data,
        query=select(Book),
    )
    return query


def build_parent_query(parent_data):
    query, _ = UnnestLoadingStrategy.construct_query(
        Book.author.prop,
        parent_columns=("author_id",),
        parent_data=parent_data,
        query=select(Author),
    )
    return query


def test_unnest_cache_key_does_not_depend_on_parent_keys():
    for build in (build_children_query, build_parent_query):
        small_key = build([(1,), (2,)])._generate_cache_key()
        large_key = build([(i,) for i in range(1, 50)])._generate_cache_key()

        assert small_key is not None
        assert large_key is not None
        assert small_key.key == large_key.key


def test_unnest_passes_parent_keys_as_one_array_parameter():
    compiled = build_children_query([(1,), (2,), (3,)]).compile(
        dialect=postgresql.dialect()
    )

    assert "unnest(" in str(compiled)
    assert [1, 2, 3] in compiled.params.values()


def test_loading_strategy_is_resolved_by_dialect():
    resolve = LoadViaParents.resolve_loading_strategy

    assert LoadViaParents.loading_strategy is UnnestLoadingStrategy
    assert resolve("postgresql", UnnestLoadingStrategy) is UnnestLoadingStrategy
    assert resolve("postgresql", ValuesLoadingStrategy) is ValuesLoadingStrategy
    assert resolve("sqlite", UnnestLoadingStrategy) is UnionLoadingStrategy
    assert resolve("sqlite", ValuesLoadingStrategy) is UnionLoadingStrategy
    assert resolve("mysql", UnnestLoadingStrategy) is ValuesLoadingStrategy
    assert resolve(None, UnnestLoadingStrategy) is ValuesLoadingStrategy
