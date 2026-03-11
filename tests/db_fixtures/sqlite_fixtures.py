from asyncio import current_task
from typing import AsyncIterator

import pytest
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    create_async_engine,
    async_sessionmaker,
    async_scoped_session,
)

from strawberry_sqlalchemy.gql_context import SQLAlchemyContext
from strawberry_sqlalchemy.loaders import LoadViaParents, UnionLoadingStrategy


@pytest.fixture(scope="session")
def sqlite_db_url(request):
    return request.config.getoption("--dburl")


@pytest.fixture(scope="function")
async def sqlite_db_engine(sqlite_db_url):
    """yields a SQLAlchemy engine which is suppressed after the test session"""
    engine = create_async_engine(
        sqlite_db_url,
        # echo=True
    )
    yield engine

    await engine.dispose()


@pytest.fixture(scope="function")
def sqlite_session(sqlite_db_engine) -> async_scoped_session[AsyncSession]:
    async_session = async_scoped_session(
        async_sessionmaker(sqlite_db_engine),
        scopefunc=current_task,
    )
    yield async_session


@pytest.fixture(scope="function")
async def mock_sqlite_sqla_session(
    sqlite_session, monkeypatch
) -> AsyncIterator[AsyncSession]:
    with monkeypatch.context() as m:
        m.setattr(SQLAlchemyContext, "get_session", sqlite_session)
        # sqlite doesn't support values, have to do through unions
        m.setattr(LoadViaParents, "loading_strategy", UnionLoadingStrategy)
        async with sqlite_session() as session:
            yield session
