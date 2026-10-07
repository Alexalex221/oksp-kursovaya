from datetime import date
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app import services
from app.auth import authenticate, current_account
from app.db import get_session
from app.models import Account

router = APIRouter(prefix="/api")


class LoginIn(BaseModel):
    login: str
    password: str


class IssueIn(BaseModel):
    copy_id: int
    reader_id: int


class ReturnIn(BaseModel):
    returned_on: date | None = None


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


@router.get("/loans")
async def list_loans(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    status: Literal["active", "overdue", "returned"] | None = None,
    reader_id: int | None = None,
    book_id: int | None = None,
    session: AsyncSession = Depends(get_session),
    _: Account = Depends(current_account),
):
    return await services.list_loans(session, page, size, status, reader_id, book_id)


@router.get("/loans/{loan_id}")
async def get_loan(
    loan_id: int,
    session: AsyncSession = Depends(get_session),
    _: Account = Depends(current_account),
):
    return await services.get_loan(session, loan_id)


@router.post("/loans", status_code=201)
async def issue_loan(
    body: IssueIn,
    session: AsyncSession = Depends(get_session),
    _: Account = Depends(current_account),
):
    return await services.issue_loan(session, body.copy_id, body.reader_id)


@router.post("/loans/{loan_id}/return")
async def return_loan(
    loan_id: int,
    body: ReturnIn | None = None,
    session: AsyncSession = Depends(get_session),
    _: Account = Depends(current_account),
):
    return await services.return_loan(session, loan_id, body.returned_on if body else None)


@router.get("/readers")
async def list_readers(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    q: str | None = None,
    session: AsyncSession = Depends(get_session),
    _: Account = Depends(current_account),
):
    return await services.list_readers(session, page, size, q)


@router.get("/readers/{reader_id}")
async def reader_card(
    reader_id: int,
    session: AsyncSession = Depends(get_session),
    _: Account = Depends(current_account),
):
    return await services.reader_card(session, reader_id)


@router.get("/books")
async def list_books(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    q: str | None = None,
    session: AsyncSession = Depends(get_session),
    _: Account = Depends(current_account),
):
    return await services.list_books(session, page, size, q)


@router.get("/books/{book_id}")
async def book_card(
    book_id: int,
    session: AsyncSession = Depends(get_session),
    _: Account = Depends(current_account),
):
    return await services.book_card(session, book_id)


@router.get("/summary")
async def summary(
    session: AsyncSession = Depends(get_session),
    _: Account = Depends(current_account),
):
    return await services.summary(session)
