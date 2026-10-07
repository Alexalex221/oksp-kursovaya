from datetime import date

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://library:changeme@localhost:55432/aleksandr_alekseenko"
    db_schema: str = "aleksandr_alekseenko"
    secret_key: str = "changeme"

    # Правила выдачи: срок в днях и штраф в рублях за каждый день просрочки.
    loan_days: int = 14
    fine_per_day: int = 10

    # Дата, относительно которой строится наполнение. Фиксирована, чтобы
    # повторный запуск давал те же данные.
    seed_base_date: date = date(2026, 10, 1)


settings = Settings()
