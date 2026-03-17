import dataclasses
import enum
import warnings
from typing import Any, Optional, Type

import strawberry
from sqlalchemy.engine import Row
from sqlalchemy.orm import (
    InstrumentedAttribute,
    RelationshipProperty,
    ColumnProperty,
    CompositeProperty,
)
from strawberry import auto
from strawberry.annotation import StrawberryAnnotation
from strawberry.types.base import get_object_definition
from strawberry.types.field import StrawberryField
from strawberry.types.object_type import _process_type, _wrap_dataclass

from . import utils
from .fields.field import StrawberrySQLAlchemyField, StrawberrySQLAlchemyRelationField
from .fields.types import resolve_model_field_type, is_optional
from .relay import Node, build_node_id_field, register_node_type

WARN_ON_TYPE_MISMATCH: bool = True


@dataclasses.dataclass
class StrawberrySQLAlchemyType:
    origin: Any
    model: Any
    is_input: bool
    is_partial: bool
    is_filter: bool


def get_model_field(
    container: StrawberrySQLAlchemyType, field_name: str
) -> InstrumentedAttribute:
    if not hasattr(container.model, field_name):
        raise AttributeError(
            f"Got error while preparing strawberry type {container.origin} at field '{field_name}'. \n"
            f"Cause: model {container.model} has no field '{field_name}'"
        )
    return getattr(container.model, field_name)


def maybe_get_model_field(
    container: StrawberrySQLAlchemyType, field_name: Optional[str]
) -> Optional[InstrumentedAttribute]:
    if not field_name or not hasattr(container.model, field_name):
        return None
    return getattr(container.model, field_name)


def enums(
    ann: Optional[Type],
    model_type: Optional[Type],
):
    # ignore enums, complicated to introspect in sqlalchemy
    if model_type == enum.Enum:
        return True


def warn_on_type_mismatch(
    container_type: StrawberrySQLAlchemyType,
    model_field: Optional[InstrumentedAttribute],
    field_annotation: StrawberryAnnotation,
    initial_field: StrawberrySQLAlchemyField,
):
    if model_field is None:
        return
    if utils.is_auto(field_annotation):
        return
    if (
        field_annotation.annotation == strawberry.ID
        or field_annotation.annotation == Optional[strawberry.ID]
    ):
        # do not warn on ID
        return

    try:
        model_field_type = resolve_model_field_type(model_field, container_type)
    except AssertionError as e:
        warnings.warn(f"{e} in {container_type.origin}")
        return
    if model_field_type is None:
        return
    field_ann = utils.unwrap_type(field_annotation)
    if enums(field_ann.annotation, model_field_type):
        return
    if (
        field_ann.annotation == model_field_type
        or field_ann.annotation == Optional[model_field_type]
    ):
        return
    # resolver-backed fields intentionally decouple model-column typing from the
    # GraphQL field annotation, so they should not warn here.
    is_str_f = isinstance(initial_field, StrawberryField)

    be_warned = True
    # do not warn when there is a resolver
    if is_str_f and initial_field.base_resolver:
        be_warned = False

    if be_warned:
        warnings.warn(
            f"A type mismatch was found in {container_type.origin.__name__} at field '{model_field.key}'.\n"
            f"Annotation: {field_ann.annotation}, Found model field type: {model_field_type}.\n"
        )


def get_field(
    container_type: StrawberrySQLAlchemyType,
    field_name: str,
    field_annotation: Optional[StrawberryAnnotation] = None,
) -> StrawberryField:
    if field_annotation is None:
        field_annotation = StrawberryAnnotation(None)
    initial_field = utils.get_type_attr(container_type.origin, field_name)
    if not isinstance(initial_field, StrawberryField):
        wrapped_field = StrawberrySQLAlchemyField(
            python_name=field_name,
            graphql_name=None,
            type_annotation=field_annotation,
        )
        wrapped_field._field_type = getattr(initial_field, "_field_type", None)
        initial_field = wrapped_field

    # Every connection, custom relation, proper annotation will fall here
    #   since they are properly defined fields in schema.
    sqla_name: str = getattr(initial_field, "sqlalchemy_name", None) or field_name
    model_field = maybe_get_model_field(container_type, sqla_name)

    if isinstance(initial_field, StrawberrySQLAlchemyRelationField):
        model_field = get_model_field(container_type, sqla_name)
        if WARN_ON_TYPE_MISMATCH:
            warn_on_type_mismatch(
                container_type, model_field, field_annotation, initial_field
            )
        field = StrawberrySQLAlchemyRelationField.from_field(
            initial_field, container_type
        )
        field.relationship_property = model_field.property
    elif model_field and isinstance(
        model_field.property, (ColumnProperty, CompositeProperty)
    ):
        if WARN_ON_TYPE_MISMATCH:
            warn_on_type_mismatch(
                container_type, model_field, field_annotation, initial_field
            )
        field = StrawberrySQLAlchemyField.from_field(initial_field, container_type)
    elif model_field and isinstance(model_field.property, RelationshipProperty):
        if WARN_ON_TYPE_MISMATCH:
            warn_on_type_mismatch(
                container_type, model_field, field_annotation, initial_field
            )
        field = StrawberrySQLAlchemyRelationField.from_field(
            initial_field, container_type
        )
        field.relationship_property = model_field.property
    elif isinstance(initial_field, StrawberrySQLAlchemyField):
        field = StrawberrySQLAlchemyField.from_field(initial_field, container_type)
    else:
        exc_text = (
            f"no 'model_field' for {container_type.origin}"
            if not model_field
            else f"Unknown SQLalchemy field type: {model_field.property=}"
        )
        raise Exception(exc_text)
    field.sqlalchemy_name = sqla_name
    field.python_name = field_name

    # store origin container type for further usage
    field.origin_container_type = container_type

    if field_annotation:
        # annotation of field is used as a class type
        field.type_annotation = field_annotation
        field.is_auto = utils.is_auto(field_annotation)

    if field.is_auto:
        if model_field is None:
            raise NotImplementedError(
                f"Could not resolve type automatically for field '{field_name}' in {container_type.origin}.\n"
                "This field does not map directly to a SQLAlchemy model attribute, "
                "so it needs an explicit return annotation."
            )
        field_type: Any = resolve_model_field_type(model_field, container_type)
        if not field_type:
            raise NotImplementedError(
                f"Could not resolve type automatically for field '{field_name}' in {container_type.origin} \n"
                f"Please add a type annotation to the field. \n"
                f"SQLAlchemy model field: {model_field}."
            )
        field.is_auto = False

        # only generate optionality for auto fields
        if is_optional(model_field, container_type.is_input, container_type.is_partial):
            field_type = Optional[field_type]
        field.type_annotation = StrawberryAnnotation(field_type)

    return field


def get_annotations(cls):
    namespace = utils.get_annotation_namespace(cls)
    annotations = {}
    for c in reversed(cls.__mro__):
        class_annotations = getattr(c, "__annotations__", None)
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


def get_fields(container_type: StrawberrySQLAlchemyType) -> list[StrawberryField]:
    annotations = get_annotations(container_type.origin)
    fields = {}

    # collect and preserve pure strawberry fields
    for dataclass_field in dataclasses.fields(container_type.origin):
        if isinstance(dataclass_field, StrawberryField) and not isinstance(
            dataclass_field, StrawberrySQLAlchemyField
        ):
            fields[dataclass_field.name] = dataclass_field

    # collect annotated fields - process our fields and implicit mappings
    for field_name, field_annotation in annotations.items():
        if field_name in fields:
            continue
        field = get_field(container_type, field_name, field_annotation)
        fields[field_name] = field

    # collect non-annotated fields defined by decorators
    for field_name in dir(container_type.origin):
        if field_name in fields:
            continue
        attr = getattr(container_type.origin, field_name)
        if utils.is_sqlalchemy_field(attr):
            field = get_field(container_type, field_name)
            fields[field_name] = field
            continue
        if isinstance(attr, StrawberryField):
            fields[field_name] = attr
            continue

    return list(fields.values())


def is_type_of(cls, obj, _info) -> bool:
    # TODO: maybe write a custom type resolver, although does not seem to be a problem
    container: StrawberrySQLAlchemyType = cls._container_type
    if isinstance(obj, container.origin):
        return True
    elif isinstance(obj, container.model):
        return True
    elif isinstance(obj, Row):
        return True
    else:
        return False


def process_type(cls, model, *args, **kwargs):
    original_annotations = cls.__dict__.get("__annotations__", {})

    container_type = StrawberrySQLAlchemyType(
        origin=cls,
        model=model,
        is_input=kwargs.get("is_input", False),
        is_partial=kwargs.pop("partial", False),
        is_filter=kwargs.pop("is_filter", False),
    )

    fields = get_fields(container_type)

    # update annotations and fields
    cls.__annotations__ = cls_annotations = {}
    for field in fields:
        field_name = field.python_name or field.name
        annotation = (
            field.type
            if field.type_annotation is None
            else field.type_annotation.annotation
        )
        if annotation is None:
            annotation = StrawberryAnnotation(auto)
        cls_annotations[field_name] = annotation
        setattr(cls, field_name, field)
        if field_name in getattr(cls, "__dataclass_fields__", {}):
            cls.__dataclass_fields__[field_name] = field

    # override is_type_of classmethod to resolve sqlalchemy types in unions and interfaces
    if not hasattr(cls, "is_type_of") or not cls.is_type_of:
        cls.is_type_of = classmethod(is_type_of)
    _process_type(cls, original_type_annotations={}, **kwargs)

    # restore original annotations for further use
    cls.__annotations__ = original_annotations
    cls._container_type = container_type

    return cls


def type(model, *args, **kwargs):
    def wrapper(cls):
        wrapped = _wrap_dataclass(cls)
        return process_type(wrapped, model, **kwargs)

    return wrapper


def node(model, *args, ids=None, codec=None, name=None, **kwargs):
    def wrapper(cls):
        if "id" not in cls.__dict__:
            annotations = dict(getattr(cls, "__annotations__", {}))
            annotations.setdefault("id", strawberry.ID)
            cls.__annotations__ = annotations
            setattr(
                cls,
                "id",
                build_node_id_field(
                    model=model,
                    node_name=name or cls.__name__,
                    ids=ids,
                    codec=codec,
                ),
            )

        wrapped = _wrap_dataclass(cls)
        processed = process_type(
            wrapped,
            model,
            name=name,
            **kwargs,
        )
        register_node_type(
            processed,
            model=model,
            ids=ids,
            codec=codec,
            node_name=name or processed.__strawberry_definition__.name,
        )
        node_interface = get_object_definition(Node, strict=True)
        if all(
            interface.origin is not Node
            for interface in processed.__strawberry_definition__.interfaces
        ):
            processed.__strawberry_definition__.interfaces.append(node_interface)
        return processed

    return wrapper


def input(model, *, partial=False, **kwargs):
    return type(model, partial=partial, is_input=True, **kwargs)


def mutation(model, **kwargs):
    return type(model, **kwargs)
