from typing import List, Any, Callable, Union, TYPE_CHECKING

from sqlalchemy.sql.elements import OperatorExpression, SQLColumnExpression

if TYPE_CHECKING:
    from strawberry_sqlalchemy.loaders import ConnectionLoader

SQLAExpressionOrBool = Union[SQLColumnExpression, OperatorExpression, bool]


class RuntimeFilter:
    def __init__(
        self,
        filters: List[Callable[[], SQLAExpressionOrBool]],
        needs_connection: bool = False,
    ):
        self.filters: List[Callable] = filters
        self.needs_connection = needs_connection

    def eval(self, connection_loader: "ConnectionLoader" = None) -> List[Any]:
        filters = []
        assert not self.needs_connection or connection_loader is not None
        for f in self.filters:
            if self.needs_connection:
                filters.append(f(connection_loader))
            else:
                filters.append(f())
        return filters
