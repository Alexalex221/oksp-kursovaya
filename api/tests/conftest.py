"""Тесты операций интерфейса идут на отдельной схеме базы.

Перед запуском схема создаётся заново и наполняется малым объёмом, поэтому
ручная подготовка базы не нужна, а рабочие данные тесты не трогают.
"""

import asyncio
import os

os.environ["DB_SCHEMA"] = os.environ.get("DB_SCHEMA", "aleksandr_alekseenko") + "_test"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.config import settings  # noqa: E402
from db import manage, seed  # noqa: E402

LOGIN = {"login": seed.ACCOUNT[0], "password": seed.ACCOUNT[1]}


async def _prepare() -> None:
    conn = await manage.connect()
    try:
        await conn.execute(f"DROP SCHEMA IF EXISTS {manage.schema_name()} CASCADE")
        await manage.apply_schema(conn)
        await seed.load(conn, "small")
    finally:
        await conn.close()


def sql(query: str, *args):
    """Одно значение из тестовой схемы: для подбора данных под проверку."""

    async def run():
        conn = await manage.connect()
        try:
            return await conn.fetchval(query, *args)
        finally:
            await conn.close()

    return asyncio.run(run())


@pytest.fixture(scope="session")
def app_client():
    assert settings.db_schema.endswith("_test")
    asyncio.run(_prepare())
    from app.main import app

    with TestClient(app) as client:
        yield client


@pytest.fixture
def client(app_client):
    """Клиент без входа."""
    app_client.cookies.clear()
    return app_client


@pytest.fixture
def authorized(app_client):
    """Клиент, вошедший под учётной записью библиотекаря."""
    app_client.cookies.clear()
    response = app_client.post("/api/login", json=LOGIN)
    assert response.status_code == 200
    return app_client
