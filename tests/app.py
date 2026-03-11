from typing import Optional, Union

from starlette.requests import Request
from starlette.responses import Response
from starlette.websockets import WebSocket
from strawberry.asgi import GraphQL as BaseGraphQL
from strawberry.http import GraphQLHTTPResponse
from strawberry.types import ExecutionResult

from strawberry_chemist.gql_context import SQLAlchemyContext


class GraphQL(BaseGraphQL):
    async def get_context(
        self,
        request: Union[Request, WebSocket],
        response: Optional[Response] = None,
    ):
        return SQLAlchemyContext(
            request=request,
            response=response,
        )

    async def process_result(
        self, request: Request, result: ExecutionResult
    ) -> GraphQLHTTPResponse:
        # do not hide errors, show them for testing purposes
        if result.errors:
            raise result.errors[0].original_error
        data: GraphQLHTTPResponse = {"data": result.data}
        # no tests that check extensions yet
        # if result.extensions:
        #     data["extensions"] = result.extensions
        return data


def create_app(schema):
    return GraphQL(schema)
