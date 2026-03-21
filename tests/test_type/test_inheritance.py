import strawberry
from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

import strawberry_chemist as sc
from strawberry_chemist.fields.field import (
    StrawberrySQLAlchemyField,
    StrawberrySQLAlchemyRelationField,
)


def test_interface_simple_fields_become_chemist_fields_on_subclasses() -> None:
    class Base(DeclarativeBase):
        pass

    class BookModel(Base):
        __tablename__ = "book_inherited_simple_field"

        id: Mapped[int] = mapped_column(Integer, primary_key=True)
        title: Mapped[str] = mapped_column(String)

    @strawberry.interface
    class Named:
        title: str

    @sc.type(model=BookModel)
    class Book(Named):
        pass

    assert isinstance(Book.title, StrawberrySQLAlchemyField)
    assert [
        interface.name for interface in Book.__strawberry_definition__.interfaces
    ] == ["Named"]


def test_interface_simple_fields_retain_permissions() -> None:
    class Base(DeclarativeBase):
        pass

    class BookModel(Base):
        __tablename__ = "book_inherited_simple_field"

        id: Mapped[int] = mapped_column(Integer, primary_key=True)
        title: Mapped[str] = mapped_column(String)

    class Deny(strawberry.BasePermission):
        message = "denied"

        def has_permission(self, source, info, **kwargs) -> bool:
            return False

    @strawberry.interface
    class Named:
        title: str = sc.field(permission_classes=[Deny])

    @sc.type(model=BookModel)
    class Book(Named):
        pass

    assert isinstance(Book.title, StrawberrySQLAlchemyField)
    assert Book.title.permission_classes == [Deny]
    assert [
        interface.name for interface in Book.__strawberry_definition__.interfaces
    ] == ["Named"]


def test_interface_field_upgrade_to_relation_field_retains_permissions() -> None:
    class Base(DeclarativeBase):
        pass

    class AuthorModel(Base):
        __tablename__ = "author_inherited_relation_field"

        id: Mapped[int] = mapped_column(Integer, primary_key=True)
        name: Mapped[str] = mapped_column(String)

    class BookModel(Base):
        __tablename__ = "book_inherited_relation_field"

        id: Mapped[int] = mapped_column(Integer, primary_key=True)
        author_id: Mapped[int | None] = mapped_column(
            ForeignKey("author_inherited_relation_field.id")
        )
        author: Mapped[AuthorModel | None] = relationship()

    class Deny(strawberry.BasePermission):
        message = "denied"

        def has_permission(self, source, info, **kwargs) -> bool:
            return False

    @sc.type(model=AuthorModel)
    class Author:
        name: str

    @strawberry.interface
    class HasAuthor:
        author: Author | None = sc.field(permission_classes=[Deny])

    @sc.type(model=BookModel)
    class Book(HasAuthor):
        pass

    assert isinstance(Book.author, StrawberrySQLAlchemyRelationField)
    assert [
        interface.name for interface in Book.__strawberry_definition__.interfaces
    ] == ["HasAuthor"]
    assert Book.author.permission_classes == [Deny]
