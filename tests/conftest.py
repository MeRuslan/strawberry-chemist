# need to expose fixtures to other packages
import pytest

from strawberry_sqlalchemy.gql_context import SQLAlchemyContext, context_var
from tests.db_fixtures.psql_fixtures import (
    mock_psql_sqla_session,
    psql_session,
    postgresql_in_docker
)  # ignore UnusedImport
from tests.db_fixtures.sqlite_fixtures import (
    mock_sqlite_sqla_session,
    sqlite_db_engine,
    sqlite_db_url,
    sqlite_session,
)  # noqa


@pytest.fixture
def mock_context_var(monkeypatch):
    with monkeypatch.context() as m:
        ctx = SQLAlchemyContext(None)
        token = context_var.set(ctx)
        yield
        context_var.reset(token)


def pytest_addoption(parser):
    parser.addoption(
        "--dburl",
        action="store",
        default='sqlite+aiosqlite:///:memory:',
        help="Database URL for testing",
    )
