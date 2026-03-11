from abc import ABC, abstractmethod
from typing import Any, TypeVar, Tuple, List

from sqlalchemy.sql import Select
from strawberry import UNSET
from strawberry.annotation import StrawberryAnnotation
from strawberry.arguments import StrawberryArgument
from strawberry.type import StrawberryType
# from strawberry_sqlalchemy.type import StrawberrySQLAlchemyType
from strawberry.types.nodes import SelectedField

GenericPaginationReturnType = TypeVar("GenericPaginationReturnType")


class StrawberrySQLAlchemyPaginationBase(ABC):
    python_name: str
    gql_name: str
    default: StrawberryType
    argument_type: type(StrawberryType)

    def __init__(
        self,
        python_name="pagination",
        gql_name="pagination",
        default=UNSET,
    ):
        self.python_name = python_name
        self.gql_name = gql_name
        self.default = default

    @property
    def argument(self) -> StrawberryArgument:
        return StrawberryArgument(
            default=self.default,
            description=None,
            graphql_name=self.gql_name,
            python_name=self.python_name,
            type_annotation=StrawberryAnnotation(self.argument_type),
        )

    @abstractmethod
    def get_fields_from_typed_request(self, selected_fields: List[SelectedField]):
        pass

    @abstractmethod
    def paginate_query(
        self,
        query: Select,
        page: Tuple,
    ) -> Select:
        pass

    @abstractmethod
    def paginate_result(
        self,
        result: Any,
    ) -> StrawberryType:
        pass

    # @staticmethod
    # async def paginate(
    #     self, connection: Any, select_query: Select, page: Tuple, info: Info
    # ):
    #     return NotImplemented
