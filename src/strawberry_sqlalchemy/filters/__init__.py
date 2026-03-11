from abc import ABC, abstractmethod
from typing import Callable, Any, Optional, Tuple, Dict

from sqlalchemy.sql import Select
from strawberry import UNSET
from strawberry.annotation import StrawberryAnnotation
from strawberry.arguments import StrawberryArgument
from strawberry.type import StrawberryType


class StrawberrySQLAlchemyFilterBase(ABC):
    """
    Base class for all SQLAlchemy filters.
    Any descendant of this class should implement the `validate_input`, `filter_query` methods,
        and have `argument_type` field defined.
    """

    python_name: str
    gql_name: str
    argument_type: type(StrawberryType)

    def __init__(
        self,
        python_name="filter",
        gql_name="filter",
        description=None,
        required=False,
        default=UNSET,
    ):
        self.python_name = python_name
        self.gql_name = gql_name
        self.required = required
        self.description = description
        self.default = default

    @property
    def argument(self) -> StrawberryArgument:
        ann = self.argument_type if self.required else Optional[self.argument_type]
        return StrawberryArgument(
            default=self.default,
            description=None,
            graphql_name=self.gql_name,
            python_name=self.python_name,
            type_annotation=StrawberryAnnotation(ann),
        )

    @abstractmethod
    def validate_input(self, input: StrawberryType) -> StrawberryType:
        raise NotImplemented

    @abstractmethod
    def filter_query(
        self,
        query: Select,
        filters: Tuple,
    ) -> Select:
        raise NotImplemented


class StrawberrySQLAlchemyFilter(StrawberrySQLAlchemyFilterBase):
    def __init__(
        self,
        input_type: type(StrawberryType),
        input_filter_map: Dict[str, Callable],
        input_validator: Callable[[Any], Any] = None,
        python_name="filter",
        gql_name="filter",
        required=False,
        **kwargs,
    ):
        self.argument_type = input_type
        self.input_filter_map: Dict[str, Callable] = input_filter_map
        self.input_validator = input_validator
        self.sanity_check()
        super().__init__(python_name, gql_name, required=required, **kwargs)

    def sanity_check(self):
        for name, field in self.argument_type.__dataclass_fields__.items():
            if name not in self.input_filter_map:
                raise ValueError(
                    f"No filter for input field '{name}'. \n"
                    "Please provide a complete map for input_filter_map."
                )

    def validate_input(self, input: StrawberryType) -> StrawberryType:
        if self.input_validator:
            return self.validate_input(input)
        else:
            return input

    def filter_query(self, query: Select, filters: Tuple) -> Select:
        for k, v in filters:
            if v != UNSET:
                query = self.input_filter_map[k](query=query, value=v)

        return query
