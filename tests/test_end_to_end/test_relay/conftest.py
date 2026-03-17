import pytest
from starlette.testclient import TestClient

from strawberry_chemist.relay import get_node_definition, register_node_type
from tests.app import create_app
from tests.test_end_to_end.test_relay.schema import Book, BookType, schema


@pytest.fixture
def test_relay_client():
    if get_node_definition(BookType) is None:
        register_node_type(BookType, model=Book)
    app = create_app(schema=schema)
    return TestClient(app)
