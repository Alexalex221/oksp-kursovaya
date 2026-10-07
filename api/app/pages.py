"""Страницы интерфейса: формируются на сервере из тех же операций, что и программный интерфейс."""

from datetime import date
from pathlib import Path
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession

from app import services
from app.auth import authenticate, page_account
from app.db import get_session
from app.models import Account
from app.rules import RuleViolation

router = APIRouter()
templates = Jinja2Templates(directory=Path(__file__).parent / "templates")

PAGE_SIZE = 20


def render(request: Request, name: str, account: Account | None, status_code: int = 200, **context):
    return templates.TemplateResponse(
        request, name, {"account": account, **context}, status_code=status_code
    )


def to_int(value: str | None) -> int | None:
    """Пустое или нечисловое поле формы — как будто фильтр не задан."""
    try:
        return int(value) if value else None
    except ValueError:
        return None


def page_number(value: str | None) -> int:
    n = to_int(value)
    return n if n and n > 0 else 1


def see_other(url: str) -> RedirectResponse:
    return RedirectResponse(url, status_code=303)


@router.get("/login")
async def login_form(request: Request):
    return render(request, "login.html", None)


@router.post("/login")
async def login(
    request: Request,
    login: str = Form(""),
    password: str = Form(""),
    session: AsyncSession = Depends(get_session),
):
    account = await authenticate(session, login, password)
    if account is None:
        return render(request, "login.html", None, 401, login=login, error="Неверный логин или пароль")
    request.session["account_id"] = account.id
    return see_other("/loans")


@router.post("/logout")
async def logout(request: Request):
    request.session.clear()
    return see_other("/login")


@router.get("/")
async def index():
    return see_other("/loans")


@router.get("/loans")
async def loans(
    request: Request,
    status: str | None = None,
    reader_id: str | None = None,
    book_id: str | None = None,
    page: str | None = None,
    session: AsyncSession = Depends(get_session),
    account: Account = Depends(page_account),
):
    status = status if status in services.LOAN_STATUSES else None
    filters = {"status": status, "reader_id": to_int(reader_id), "book_id": to_int(book_id)}
    data = await services.list_loans(session, page_number(page), PAGE_SIZE, **filters)
    query = urlencode({k: v for k, v in filters.items() if v is not None})
    return render(request, "loans.html", account, data=data, query=query, **filters)


@router.post("/loans/issue")
async def issue(
    request: Request,
    copy_id: str = Form(""),
    reader_id: str = Form(""),
    session: AsyncSession = Depends(get_session),
    account: Account = Depends(page_account),
):
    copy, reader = to_int(copy_id), to_int(reader_id)
    try:
        if copy is None or reader is None:
            raise RuleViolation("укажите номер экземпляра и номер читателя")
        loan = await services.issue_loan(session, copy, reader)
    except (RuleViolation, services.NotFound) as exc:
        data = await services.list_loans(session, 1, PAGE_SIZE)
        return render(request, "loans.html", account, 409, data=data, query="",
                      error=f"Выдача отклонена: {exc}")
    return see_other(f"/loans/{loan['id']}")


@router.get("/loans/{loan_id}")
async def loan_card(
    request: Request,
    loan_id: int,
    session: AsyncSession = Depends(get_session),
    account: Account = Depends(page_account),
):
    loan = await services.get_loan(session, loan_id)
    return render(request, "loan.html", account, loan=loan, today=services.today())


@router.post("/loans/{loan_id}/return")
async def return_loan(
    request: Request,
    loan_id: int,
    returned_on: str = Form(""),
    session: AsyncSession = Depends(get_session),
    account: Account = Depends(page_account),
):
    try:
        return_date = date.fromisoformat(returned_on) if returned_on else None
        await services.return_loan(session, loan_id, return_date)
    except (ValueError, RuleViolation) as exc:
        loan = await services.get_loan(session, loan_id)
        return render(request, "loan.html", account, 409, loan=loan, today=services.today(),
                      error=f"Возврат не принят: {exc}")
    return see_other(f"/loans/{loan_id}")


@router.get("/readers")
async def readers(
    request: Request,
    q: str | None = None,
    page: str | None = None,
    session: AsyncSession = Depends(get_session),
    account: Account = Depends(page_account),
):
    data = await services.list_readers(session, page_number(page), PAGE_SIZE, q or None)
    return render(request, "readers.html", account, data=data, q=q, query=urlencode({"q": q or ""}))


@router.get("/readers/{reader_id}")
async def reader_card(
    request: Request,
    reader_id: int,
    session: AsyncSession = Depends(get_session),
    account: Account = Depends(page_account),
):
    reader = await services.reader_card(session, reader_id)
    return render(request, "reader.html", account, reader=reader)


@router.get("/books")
async def books(
    request: Request,
    q: str | None = None,
    page: str | None = None,
    session: AsyncSession = Depends(get_session),
    account: Account = Depends(page_account),
):
    data = await services.list_books(session, page_number(page), PAGE_SIZE, q or None)
    return render(request, "books.html", account, data=data, q=q, query=urlencode({"q": q or ""}))


@router.get("/books/{book_id}")
async def book_card(
    request: Request,
    book_id: int,
    session: AsyncSession = Depends(get_session),
    account: Account = Depends(page_account),
):
    book = await services.book_card(session, book_id)
    return render(request, "book.html", account, book=book)


@router.get("/summary")
async def summary(
    request: Request,
    session: AsyncSession = Depends(get_session),
    account: Account = Depends(page_account),
):
    return render(request, "summary.html", account, s=await services.summary(session))
