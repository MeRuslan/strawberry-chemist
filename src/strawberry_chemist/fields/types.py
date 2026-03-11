import datetime
import decimal
import enum
from typing import TYPE_CHECKING, Optional, Type, Union

import sqlalchemy
import sqlalchemy.orm
from sqlalchemy.orm import ColumnProperty, InstrumentedAttribute, RelationshipProperty

if TYPE_CHECKING:
    from strawberry_chemist.type import StrawberrySQLAlchemyType


field_type_map = {
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
}


STR_SQLA_SCALAR_TYPES = Union[
    int,
    float,
    str,
    bool,
    decimal.Decimal,
    datetime.date,
    datetime.datetime,
    datetime.time,
    enum.Enum,
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
    except AttributeError:
        model_field_type = None

    if ASSERT_ON_UNKNOWN_SQLA_TYPE:
        assert model_field_type in field_type_map.keys(), (
            f"field {model_field} is an unknown scalar type: {model_field_type}"
        )

    if container_type.is_input:
        raise NotImplementedError("Input types are not supported yet")
    field_type = field_type_map.get(model_field_type, None)

    return field_type


def is_optional(model_field, is_input, partial):
    if partial:
        return True
    if not model_field:
        return False
    if isinstance(model_field.property, ColumnProperty):
        return model_field.nullable
    return False
