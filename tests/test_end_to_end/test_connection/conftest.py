import pytest
from starlette.testclient import TestClient

from tests.app import create_app
from tests.test_end_to_end.test_connection.schema import schema


@pytest.fixture
def test_connection_client():
    app = create_app(schema=schema)
    return TestClient(app)
