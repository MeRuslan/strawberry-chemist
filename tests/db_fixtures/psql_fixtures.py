import logging
from asyncio import current_task
from typing import AsyncIterator

import pytest
from pytest_postgresql import factories
from pytest_postgresql.janitor import DatabaseJanitor
from sqlalchemy.ext.asyncio import (
    create_async_engine,
    async_sessionmaker,
    async_scoped_session,
    AsyncSession,
)

from strawberry_chemist.gql_context import SQLAlchemyContext

logging.basicConfig()
logger = logging.getLogger("custom logger")
logger.setLevel(logging.DEBUG)

postgresql_in_docker = factories.postgresql_noproc()
# postgresql = factories.postgresql("postgresql_in_docker")


@pytest.fixture(scope="function")
def psql_session(postgresql_in_docker):
    pg_host = postgresql_in_docker.host
    pg_port = postgresql_in_docker.port
    pg_user = postgresql_in_docker.user
    pg_password = postgresql_in_docker.password
    pg_db = postgresql_in_docker.dbname

    with DatabaseJanitor(
        pg_user, pg_host, pg_port, pg_db, postgresql_in_docker.version, pg_password
    ):
        connection_str = (
            f"postgresql+psycopg://{pg_user}:{pg_password}@{pg_host}:{pg_port}/{pg_db}"
        )
        engine = create_async_engine(
            connection_str,
            # echo=True
        )
        async_session = async_scoped_session(
            async_sessionmaker(engine),
            scopefunc=current_task,
        )
        yield async_session
        logger.debug("psql_session: closing")
    logger.debug("psql_session: closed")


@pytest.fixture(scope="function")
async def mock_psql_sqla_session(
    psql_session, monkeypatch
) -> AsyncIterator[AsyncSession]:
    with monkeypatch.context() as m:
        m.setattr(SQLAlchemyContext, "get_session", psql_session)
        async with psql_session() as session:
            yield session
