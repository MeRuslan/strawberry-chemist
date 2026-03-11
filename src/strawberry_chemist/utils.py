import dataclasses

from sqlalchemy.orm import DeclarativeMeta
from strawberry import auto
from strawberry.annotation import StrawberryAnnotation
from strawberry import UNSET

from strawberry.field import StrawberryField
from strawberry.type import StrawberryContainer

from strawberry_chemist.connection.base import SQLAlchemyBaseConnectionField
from strawberry_chemist.fields.field import StrawberrySQLAlchemyField


def get_type_attr(type_, field_name):
    # should probably simply set to
    # attr = getattr(type_, "__dataclass_fields__", {}).get(field_name, UNSET)
    attr = getattr(type_, field_name, UNSET)
    if attr is UNSET:
        attr = getattr(type_, "__dataclass_fields__", {}).get(field_name, UNSET)
    return attr


def unwrap_type(type_):
    while isinstance(type_, StrawberryContainer):
        type_ = type_.of_type

    return type_


def is_sqlalchemy_model(obj):
    return isinstance(obj, DeclarativeMeta)


def is_container_type(obj):
    return hasattr(obj, "_container_type")


# def get_sqlalchemy_model(type_):
#     if not is_container_type(type_):
#         return
#     return type_._container_type.model


def get_annotations(cls):
    annotations = {}
    for c in reversed(cls.__mro__):
        if "__annotations__" in c.__dict__:
            annotations.update(
                {k: StrawberryAnnotation(v) for k, v in c.__annotations__.items()}
            )
    return annotations


def is_field(obj):
    return isinstance(obj, dataclasses.Field)


def is_strawberry_field(obj):
    return isinstance(obj, StrawberryField)


def is_sqlalchemy_field(obj):
    return isinstance(obj, StrawberrySQLAlchemyField)


def is_auto(type_):
    return (
        type_.annotation if isinstance(type_, StrawberryAnnotation) else type_
    ) is auto


def get_sqlalchemy_model(type_):
    if not is_container_type(type_):
        return
    return type_._container_type.model


def is_connection(field):
    return issubclass(type(field), SQLAlchemyBaseConnectionField)
