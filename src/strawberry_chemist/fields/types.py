import datetime
import decimal
import enum
from typing import Optional, Type, Union

import sqlalchemy
import sqlalchemy.orm
from sqlalchemy.orm import ColumnProperty, InstrumentedAttribute, RelationshipProperty

# @strawberry.input
# class OneInput:
#     set: Optional[strawberry.ID]


# @strawberry.input
# class OneToManyInput:
#     set: Optional[strawberry.ID]


# @strawberry.input
# class ManyInput:
#     add: Optional[List[strawberry.ID]] = UNSET
#     remove: Optional[List[strawberry.ID]] = UNSET
#     set: Optional[List[strawberry.ID]] = UNSET


# @strawberry.input
# class ManyToManyInput:
#     add: Optional[List[strawberry.ID]] = UNSET
#     remove: Optional[List[strawberry.ID]] = UNSET
#     set: Optional[List[strawberry.ID]] = UNSET


# class RelationshipNumber(enum.Enum):
#     ONE = 0
#     MANY = 1


"""
More on conversion info: https://strawberry.rocks/docs/concepts/typings#mapping-to-graphql-types
"""
field_type_map = {
    # sqlalchemy.AutoField: strawberry.ID,
    # sqlalchemy.BigAutoField: strawberry.ID,
    sqlalchemy.BigInteger: int,
    sqlalchemy.Integer: int,
    sqlalchemy.SmallInteger: int,
    sqlalchemy.DECIMAL: decimal.Decimal,
    sqlalchemy.Numeric: decimal.Decimal,
    sqlalchemy.VARCHAR: str,
    sqlalchemy.Text: str,
    sqlalchemy.String: str,
    sqlalchemy.Boolean: bool,
    sqlalchemy.Enum: enum.Enum,
    sqlalchemy.Interval: str,
    sqlalchemy.Date: datetime.date,
    sqlalchemy.DateTime: datetime.datetime,
    sqlalchemy.TIMESTAMP: datetime.datetime,
    sqlalchemy.Float: float,
    sqlalchemy.Time: datetime.time,
    # relationships are considered separately
    sqlalchemy.orm.relationship: None,
    # sqlalchemy.related.ForeignKey: DjangoModelType,
    # sqlalchemy.reverse_related.ManyToOneRel: List[DjangoModelType],
    # sqlalchemy.related.OneToOneField: DjangoModelType,
    # sqlalchemy.reverse_related.OneToOneRel: DjangoModelType,
    # sqlalchemy.related.ManyToManyField: List[DjangoModelType],
    # sqlalchemy.reverse_related.ManyToManyRel: List[DjangoModelType],
}

# relationship_input_field_type_map = {
#     RelationshipNumber.ONE: OneInput,
#     RelationshipNumber.ONE_TO_MANY: OneToManyInput,
#     RelationshipNumber.MANY: ManyInput,
#     RelationshipNumber.MANY_TO_MANY: ManyToManyInput,
# }

STR_SQLA_SCALAR_TYPES = Union[
    int,
    float,
    str,
    bool,
    decimal.Decimal,
    datetime.date,
    datetime.datetime,
    datetime.time,
]
ASSERT_ON_UNKNOWN_SQLA_TYPE = False


def resolve_model_field_type(
    model_field: InstrumentedAttribute,
    container_type: "StrawberrySQLAlchemyType",
) -> Optional[Type[STR_SQLA_SCALAR_TYPES]]:
    # sqlalchemy returns a concrete field type for model_field.type, thus need type(...)
    try:
        if isinstance(model_field.prop, RelationshipProperty):
            model_field_type = sqlalchemy.orm.relationship
        else:
            model_field_type = type(model_field.type)
    except AttributeError as e:
        model_field_type = None

    if ASSERT_ON_UNKNOWN_SQLA_TYPE:
        assert model_field_type in field_type_map.keys(), (
            f"field {model_field} is an unknown scalar type: {model_field_type}"
        )

    # if container_type.is_filter and model_field.is_relation:
    #     field_type = filters_old.DjangoModelFilterInput
    if container_type.is_input:
        # field_type = relationship_input_field_type_map.get(model_field_type, None)
        raise NotImplementedError("Input types are not supported yet")
    field_type = field_type_map.get(model_field_type, None)

    return field_type


# def resolve_relationship_direction(
#         model_field: sqlalchemy.orm.RelationshipProperty,
# ) -> RelationshipNumber:
#     relationship_type = model_field.direction
#     # if reports as 1-to-m, and the other side does not use list, we have 1-to-1
#     if relationship_type == ONETOMANY:
#         return RelationshipNumber.ONE
#     elif relationship_type in (MANYTOONE, MANYTOMANY):
#         return RelationshipNumber.MANY
#     else:
#         raise Exception("Seems like a misconfigured relationship?")
# if relationship_type == ONETOMANY and not model_field._reverse_property.uselist:
#     return RelationshipNumber.ONE
# # in other case, 1-to-m
# elif relationship_type == ONETOMANY:
#     return RelationshipNumber.ONE_TO_MANY
# elif relationship_type == MANYTOONE:
#     return RelationshipNumber.MANY
# elif relationship_type == MANYTOMANY:
#     return RelationshipNumber.MANY_TO_MANY
# else:
#     raise Exception("Seems like a misconfigured relationship?")


# def inspect_relation(
#         model_field: sqlalchemy.orm.RelationshipProperty,
# ) -> Tuple[RelationshipNumber, bool, Optional[Column]]:
#     relationship_type = resolve_relationship_direction(model_field)
#     # these cannot guarantee non-nullability
#     if relationship_type != RelationshipNumber.ONE:
#         return relationship_type, True, None
#     # this one is complicated, if only single column in references,
#     #   then relationship nullability is simply that field's nullability
#     else:  # if relationship_type is RelationshipType.ONE_TO_ONE:
#         fk_columns: List[Column] = model_field.local_columns
#         if len(fk_columns) == 1:
#             nullable_fk = fk_columns[0].nullable
#         else:
#             # don't currently handle multicolumn FKs properly
#             nullable_fk = True
#
#     return relationship_type, nullable_fk, fk_columns[0]


def is_optional(model_field, is_input, partial):
    #     if partial:
    #         return True
    #     if not model_field:
    #         return False
    #     if is_input:
    #         if isinstance(model_field, fields.reverse_related.OneToOneRel):
    #             return model_field.null
    #         if model_field.many_to_many or model_field.one_to_many:
    #             return True
    #         has_default = model_field.default is not fields.NOT_PROVIDED
    #         if model_field.blank or has_default:
    #             return True
    #     if model_field.null:
    #         return True
    #     return False
    if partial:
        return True
    if not model_field:
        return False

    # currently no inputs are supported
    # if is_input:
    #     if isinstance(model_field, Column):
    #         # if default is set, input is likely optional
    #         if (
    #                 model_field.default is not None
    #                 or model_field.server_default is not None
    #         ):
    #             return True
    #     elif isinstance(model_field, sqlalchemy.orm.RelationshipProperty):
    #         t, n, c = inspect_relation(model_field)
    #         # if the field is nullable, nothing to add
    #         if n:
    #             return True
    #         elif c.default is not None or c.server_default is not None:
    #             return True
    # return nullability for a column
    if isinstance(model_field.property, ColumnProperty):
        return model_field.nullable
    return False
