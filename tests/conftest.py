import pytest

from strawberry_sqlalchemy.gql_context import SQLAlchemyContext, context_var
from tests.db_fixtures.sqlite_fixtures import (
    mock_sqlite_sqla_session,
    sqlite_db_engine,
    sqlite_db_url,
    sqlite_session,
)  # noqa

_PSQL_IMPORT_ERROR = None

try:
    from tests.db_fixtures.psql_fixtures import (
        mock_psql_sqla_session,
        psql_session,
        postgresql_in_docker,
    )  # ignore UnusedImport
except ModuleNotFoundError as exc:
    _PSQL_IMPORT_ERROR = exc

    def _skip_psql_fixture():
        pytest.skip(
            "PostgreSQL test dependencies are unavailable: "
            f"{_PSQL_IMPORT_ERROR.name}"
        )

    @pytest.fixture(scope="function")
    def postgresql_in_docker():
        _skip_psql_fixture()

    @pytest.fixture(scope="function")
    def psql_session():
        _skip_psql_fixture()

    @pytest.fixture(scope="function")
    async def mock_psql_sqla_session():
        _skip_psql_fixture()


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
