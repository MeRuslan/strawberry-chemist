from strawberry_sqlalchemy.connection.base import SQLAlchemyBaseConnectionField
from strawberry_sqlalchemy.pagination.cursor import StrawberrySQLAlchemyCursorPagination

default_max_limit = 20


class SQLAlchemyRelayConnectionField(SQLAlchemyBaseConnectionField):
    pagination: StrawberrySQLAlchemyCursorPagination

    def __init__(self, max_limit=default_max_limit, *args, **kwargs):
        self.pagination = StrawberrySQLAlchemyCursorPagination(max_limit=max_limit)
        super().__init__(*args, **kwargs)


def field(
    post_processor=None,
    max_limit=default_max_limit,
    order=None,
    filter=None,
    *,
    name=None,
    sqlalchemy_name=None,
    **kwargs
):
    field_ = SQLAlchemyRelayConnectionField(
        post_processor=post_processor,
        python_name=None,
        graphql_name=name,
        type_annotation=None,
        sqlalchemy_name=sqlalchemy_name,
        max_limit=max_limit,
        order=order,
        filter=filter,
        **kwargs
    )

    return field_
