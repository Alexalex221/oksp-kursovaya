"""Правила выдачи книг.

Чистые функции без обращения к базе: на вход — даты и факты о читателе
и экземпляре, на выход — результат или отказ.
"""

from datetime import date, timedelta

from app.config import settings


class RuleViolation(Exception):
    """Операция запрещена правилами библиотеки."""


def due_date(issued_on: date, loan_days: int = settings.loan_days) -> date:
    """Срок возврата: дата выдачи плюс срок пользования."""
    return issued_on + timedelta(days=loan_days)


def overdue_days(due_on: date, returned_on: date | None, today: date) -> int:
    """Дней просрочки. Для невозвращённой книги считается по сегодняшний день."""
    end = returned_on or today
    return max(0, (end - due_on).days)


def fine(days_overdue: int, per_day: int = settings.fine_per_day) -> int:
    """Штраф в рублях за просрочку."""
    return days_overdue * per_day


def is_overdue(due_on: date, returned_on: date | None, today: date) -> bool:
    """Выдача просрочена: книга не возвращена, а срок уже прошёл."""
    return returned_on is None and due_on < today


def check_issue(copy_on_loan: bool, reader_overdue_loans: int) -> None:
    """Экземпляр выдаётся, только если он свободен и у читателя нет просрочек."""
    if copy_on_loan:
        raise RuleViolation("экземпляр уже выдан")
    if reader_overdue_loans > 0:
        raise RuleViolation(f"у читателя просроченных выдач: {reader_overdue_loans}")


def check_return(issued_on: date, returned_on: date | None, return_date: date, today: date) -> None:
    """Возврат принимается один раз, не раньше даты выдачи и не позже сегодняшнего дня."""
    if returned_on is not None:
        raise RuleViolation("выдача уже закрыта")
    if return_date < issued_on:
        raise RuleViolation("дата возврата раньше даты выдачи")
    if return_date > today:
        raise RuleViolation("дата возврата ещё не наступила")
