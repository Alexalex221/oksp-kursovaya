"""Обслуживание базы данных.

    python db/manage.py schema        создать схему и таблицы
    python db/manage.py counts        число записей по таблицам
"""

import asyncio
import re
import sys
from pathlib import Path

import asyncpg

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import settings  # noqa: E402

TABLES = ["accounts", "readers", "books", "copies", "loans"]


def schema_name() -> str:
    name = settings.db_schema
    if not re.fullmatch(r"[a-z_][a-z0-9_]*", name):
        raise SystemExit(f"недопустимое имя схемы: {name!r}")
    return name


async def connect() -> asyncpg.Connection:
    dsn = settings.database_url.replace("postgresql+asyncpg://", "postgresql://")
    return await asyncpg.connect(dsn, server_settings={"search_path": schema_name()})


async def apply_schema(conn: asyncpg.Connection) -> None:
    sql = (Path(__file__).parent / "schema.sql").read_text()
    await conn.execute(sql.replace(":schema", schema_name()))


async def counts(conn: asyncpg.Connection) -> dict[str, int]:
    return {t: await conn.fetchval(f"SELECT count(*) FROM {t}") for t in TABLES}


async def main(argv: list[str]) -> None:
    if not argv:
        raise SystemExit(__doc__)
    conn = await connect()
    try:
        if argv[0] == "schema":
            await apply_schema(conn)
            print(f"схема {schema_name()} готова")
        elif argv[0] == "counts":
            for table, n in (await counts(conn)).items():
                print(f"{table:<10}{n:>10}")
        else:
            raise SystemExit(__doc__)
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1:]))
