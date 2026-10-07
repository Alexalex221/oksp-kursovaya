from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import authenticate, current_account
from app.db import get_session
from app.models import Account

router = APIRouter(prefix="/api")


class LoginIn(BaseModel):
    login: str
    password: str


def account_out(account: Account) -> dict:
    return {"id": account.id, "login": account.login, "full_name": account.full_name}


@router.post("/login")
async def login(body: LoginIn, request: Request, session: AsyncSession = Depends(get_session)):
    account = await authenticate(session, body.login, body.password)
    if account is None:
        raise HTTPException(status_code=401, detail="неверный логин или пароль")
    request.session["account_id"] = account.id
    return account_out(account)


@router.post("/logout", status_code=204)
async def logout(request: Request):
    request.session.clear()
    return Response(status_code=204)


@router.get("/me")
async def me(account: Account = Depends(current_account)):
    return account_out(account)
