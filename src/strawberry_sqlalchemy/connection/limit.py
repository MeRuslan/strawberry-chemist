from strawberry_sqlalchemy.connection.base import SQLAlchemyBaseConnectionField
from strawberry_sqlalchemy.pagination import StrawberrySQLAlchemyLimitOffsetPagination

default_max_limit = 20


class SQLAlchemyLimitOffsetConnectionField(SQLAlchemyBaseConnectionField):
    pagination: StrawberrySQLAlchemyLimitOffsetPagination

    def __init__(self, max_limit=default_max_limit, *args, **kwargs):
        self.pagination = StrawberrySQLAlchemyLimitOffsetPagination(max_limit=max_limit)
        super(SQLAlchemyLimitOffsetConnectionField, self).__init__(*args, **kwargs)


def field(post_processor=None, *, name=None, sqlalchemy_name=None, **kwargs):
    field_ = SQLAlchemyLimitOffsetConnectionField(
        post_processor=post_processor,
        python_name=None,
        graphql_name=name,
        type_annotation=None,
        sqlalchemy_name=sqlalchemy_name,
        **kwargs,
    )

    return field_
