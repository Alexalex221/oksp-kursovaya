from fastapi import Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.models import Account
from app.security import verify_password


class LoginRequired(Exception):
    """Страница интерфейса открыта без входа: нужно перенаправить на форму."""


async def authenticate(session: AsyncSession, login: str, password: str) -> Account | None:
    account = await session.scalar(select(Account).where(Account.login == login))
    if account is None or not verify_password(password, account.password_hash):
        return None
    return account


async def _account_from_session(request: Request, session: AsyncSession) -> Account | None:
    account_id = request.session.get("account_id")
    if account_id is None:
        return None
    account = await session.get(Account, account_id)
    if account is None:
        request.session.clear()
    return account


async def current_account(request: Request, session: AsyncSession = Depends(get_session)) -> Account:
    """Учётная запись для операций программного интерфейса: без входа — 401."""
    account = await _account_from_session(request, session)
    if account is None:
        raise HTTPException(status_code=401, detail="требуется вход")
    return account


async def page_account(request: Request, session: AsyncSession = Depends(get_session)) -> Account:
    """Учётная запись для страниц: без входа — переход на форму входа."""
    account = await _account_from_session(request, session)
    if account is None:
        raise LoginRequired()
    return account
