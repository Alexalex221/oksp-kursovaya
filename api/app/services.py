"""Операции над данными библиотеки. Общие для программного интерфейса и страниц."""

from datetime import date

from sqlalchemy import exists, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app import rules
from app.models import Book, Copy, Loan, Reader

LOAN_STATUSES = ("active", "overdue", "returned")


class NotFound(Exception):
    """Запись не найдена."""


def today() -> date:
    return date.today()


def loan_status(loan: Loan, on: date) -> str:
    if loan.returned_on is not None:
        return "returned"
    return "overdue" if rules.is_overdue(loan.due_on, loan.returned_on, on) else "active"


def loan_out(loan: Loan, copy: Copy, book: Book, reader: Reader, on: date) -> dict:
    days = rules.overdue_days(loan.due_on, loan.returned_on, on)
    return {
        "id": loan.id,
        "issued_on": loan.issued_on,
        "due_on": loan.due_on,
        "returned_on": loan.returned_on,
        "status": loan_status(loan, on),
        "overdue_days": days,
        "fine": rules.fine(days),
        "reader": {"id": reader.id, "full_name": reader.full_name},
        "copy": {"id": copy.id, "inventory_no": copy.inventory_no},
        "book": {"id": book.id, "title": book.title, "author": book.author},
    }


def _loans_query():
    return (
        select(Loan, Copy, Book, Reader)
        .join(Copy, Loan.copy_id == Copy.id)
        .join(Book, Copy.book_id == Book.id)
        .join(Reader, Loan.reader_id == Reader.id)
    )


async def list_loans(
    session: AsyncSession,
    page: int,
    size: int,
    status: str | None = None,
    reader_id: int | None = None,
    book_id: int | None = None,
) -> dict:
    on = today()
    query = _loans_query()
    if status == "active":
        query = query.where(Loan.returned_on.is_(None))
    elif status == "overdue":
        query = query.where(Loan.returned_on.is_(None), Loan.due_on < on)
    elif status == "returned":
        query = query.where(Loan.returned_on.is_not(None))
    if reader_id is not None:
        query = query.where(Loan.reader_id == reader_id)
    if book_id is not None:
        query = query.where(Copy.book_id == book_id)

    total = await session.scalar(select(func.count()).select_from(query.subquery()))
    rows = await session.execute(
        query.order_by(Loan.issued_on.desc(), Loan.id.desc()).offset((page - 1) * size).limit(size)
    )
    return {
        "items": [loan_out(*row, on) for row in rows],
        "total": total,
        "page": page,
        "size": size,
    }


async def get_loan(session: AsyncSession, loan_id: int) -> dict:
    row = (await session.execute(_loans_query().where(Loan.id == loan_id))).first()
    if row is None:
        raise NotFound("выдача не найдена")
    return loan_out(*row, today())


async def issue_loan(session: AsyncSession, copy_id: int, reader_id: int) -> dict:
    on = today()
    # Строка экземпляра блокируется: две одновременные выдачи одного
    # экземпляра выполнятся по очереди, и вторая увидит первую.
    copy = await session.scalar(select(Copy).where(Copy.id == copy_id).with_for_update())
    if copy is None:
        raise NotFound("экземпляр не найден")
    if await session.get(Reader, reader_id) is None:
        raise NotFound("читатель не найден")

    on_loan = await session.scalar(
        select(exists().where(Loan.copy_id == copy_id, Loan.returned_on.is_(None)))
    )
    overdue = await session.scalar(
        select(func.count()).where(
            Loan.reader_id == reader_id, Loan.returned_on.is_(None), Loan.due_on < on
        )
    )
    rules.check_issue(on_loan, overdue)

    loan = Loan(copy_id=copy_id, reader_id=reader_id, issued_on=on, due_on=rules.due_date(on))
    session.add(loan)
    await session.commit()
    return await get_loan(session, loan.id)


async def return_loan(session: AsyncSession, loan_id: int, return_date: date | None = None) -> dict:
    on = today()
    loan = await session.scalar(select(Loan).where(Loan.id == loan_id).with_for_update())
    if loan is None:
        raise NotFound("выдача не найдена")
    return_date = return_date or on
    rules.check_return(loan.issued_on, loan.returned_on, return_date, on)
    loan.returned_on = return_date
    await session.commit()
    return await get_loan(session, loan_id)
