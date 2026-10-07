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


def reader_out(reader: Reader) -> dict:
    return {
        "id": reader.id,
        "full_name": reader.full_name,
        "email": reader.email,
        "phone": reader.phone,
        "registered_on": reader.registered_on,
    }


async def list_readers(session: AsyncSession, page: int, size: int, q: str | None = None) -> dict:
    query = select(Reader)
    if q:
        query = query.where(Reader.full_name.ilike(f"%{q}%"))
    total = await session.scalar(select(func.count()).select_from(query.subquery()))
    readers = await session.scalars(query.order_by(Reader.id).offset((page - 1) * size).limit(size))
    return {"items": [reader_out(r) for r in readers], "total": total, "page": page, "size": size}


async def reader_card(session: AsyncSession, reader_id: int) -> dict:
    on = today()
    reader = await session.get(Reader, reader_id)
    if reader is None:
        raise NotFound("читатель не найден")
    rows = await session.execute(
        _loans_query().where(Loan.reader_id == reader_id).order_by(Loan.issued_on.desc(), Loan.id.desc())
    )
    loans = [loan_out(*row, on) for row in rows]
    return {
        **reader_out(reader),
        "stats": {
            "loans_total": len(loans),
            "on_hands": sum(1 for loan in loans if loan["status"] != "returned"),
            "overdue": sum(1 for loan in loans if loan["status"] == "overdue"),
            "fines_total": sum(loan["fine"] for loan in loans),
        },
        "loans": loans,
    }


def book_out(book: Book) -> dict:
    return {
        "id": book.id,
        "title": book.title,
        "author": book.author,
        "isbn": book.isbn,
        "published_year": book.published_year,
        "genre": book.genre,
    }


async def list_books(session: AsyncSession, page: int, size: int, q: str | None = None) -> dict:
    copies = select(func.count()).where(Copy.book_id == Book.id).scalar_subquery()
    query = select(Book, copies.label("copies"))
    if q:
        query = query.where(Book.title.ilike(f"%{q}%") | Book.author.ilike(f"%{q}%"))
    total = await session.scalar(select(func.count()).select_from(query.subquery()))
    rows = await session.execute(query.order_by(Book.id).offset((page - 1) * size).limit(size))
    return {
        "items": [{**book_out(book), "copies": n} for book, n in rows],
        "total": total,
        "page": page,
        "size": size,
    }


async def book_card(session: AsyncSession, book_id: int) -> dict:
    book = await session.get(Book, book_id)
    if book is None:
        raise NotFound("книга не найдена")
    copies = (await session.scalars(select(Copy).where(Copy.book_id == book_id).order_by(Copy.id))).all()
    copy_ids = [c.id for c in copies]
    open_loans = {}
    if copy_ids:
        rows = await session.execute(
            select(Loan, Reader)
            .join(Reader, Loan.reader_id == Reader.id)
            .where(Loan.copy_id.in_(copy_ids), Loan.returned_on.is_(None))
        )
        open_loans = {loan.copy_id: (loan, reader) for loan, reader in rows}
    loans_total = await session.scalar(
        select(func.count()).select_from(Loan).join(Copy, Loan.copy_id == Copy.id).where(Copy.book_id == book_id)
    )

    def copy_out(copy: Copy) -> dict:
        item = {"id": copy.id, "inventory_no": copy.inventory_no, "shelf": copy.shelf, "status": "free", "loan": None}
        if copy.id in open_loans:
            loan, reader = open_loans[copy.id]
            item["status"] = "on_loan"
            item["loan"] = {
                "id": loan.id,
                "due_on": loan.due_on,
                "reader": {"id": reader.id, "full_name": reader.full_name},
            }
        return item

    return {**book_out(book), "loans_total": loans_total, "copies": [copy_out(c) for c in copies]}


async def summary(session: AsyncSession, top: int = 10) -> dict:
    on = today()
    on_hands = await session.scalar(select(func.count()).where(Loan.returned_on.is_(None)))
    overdue = await session.scalar(
        select(func.count()).where(Loan.returned_on.is_(None), Loan.due_on < on)
    )
    copies_total = await session.scalar(select(func.count()).select_from(Copy))
    loans = func.count(Loan.id).label("loans")
    rows = await session.execute(
        select(Book, loans)
        .join(Copy, Copy.book_id == Book.id)
        .join(Loan, Loan.copy_id == Copy.id)
        .group_by(Book.id)
        .order_by(loans.desc(), Book.id)
        .limit(top)
    )
    return {
        "on_date": on,
        "copies_total": copies_total,
        "on_hands": on_hands,
        "overdue": overdue,
        "overdue_share": round(overdue / on_hands, 4) if on_hands else 0.0,
        "top_books": [{"id": b.id, "title": b.title, "author": b.author, "loans": n} for b, n in rows],
    }
