import dataclasses
import sys
from typing import Any

from sqlalchemy.orm import DeclarativeMeta
from strawberry import UNSET
from strawberry import auto
from strawberry.annotation import StrawberryAnnotation

from strawberry.types.base import StrawberryContainer
from strawberry.types.field import StrawberryField

from strawberry_chemist.connection.base import SQLAlchemyBaseConnectionField
from strawberry_chemist.fields.field import StrawberrySQLAlchemyField


def get_type_attr(type_: type[Any], field_name: str) -> Any:
    # should probably simply set to
    # attr = getattr(type_, "__dataclass_fields__", {}).get(field_name, UNSET)
    attr = type_.__dict__.get(field_name, UNSET)
    if attr is not UNSET:
        return attr
    if dataclasses.is_dataclass(type_):
        attr = type_.__dataclass_fields__.get(field_name, UNSET)
        if attr is not UNSET:
            return attr
    return getattr(type_, field_name, UNSET)


def get_annotation_namespace(type_: type[Any]) -> dict[str, Any]:
    module = sys.modules.get(type_.__module__)
    if module is None:
        return {}
    return module.__dict__


def get_class_annotations(type_: type[Any]) -> dict[str, Any]:
    annotations = type_.__dict__.get("__annotations__")
    if annotations is None:
        return {}
    return dict(annotations)


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
    namespace = get_annotation_namespace(cls)
    annotations = {}
    for c in reversed(cls.__mro__):
        class_annotations = get_class_annotations(c)
        if class_annotations:
            annotations.update(
                {
                    k: StrawberryAnnotation.from_annotation(v, namespace=namespace)
                    for k, v in class_annotations.items()
                }
            )
            for field_name, annotation in annotations.items():
                if annotation and annotation.namespace is None:
                    annotation.namespace = namespace
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
