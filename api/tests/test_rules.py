"""Тесты правил выдачи: без базы и без работающего сервиса."""

from datetime import date

import pytest

from app import rules

ISSUED = date(2026, 9, 1)
DUE = date(2026, 9, 15)


def test_due_date_is_issue_date_plus_loan_period():
    assert rules.due_date(ISSUED, loan_days=14) == DUE


def test_returned_on_time_has_no_overdue_and_no_fine():
    days = rules.overdue_days(DUE, returned_on=date(2026, 9, 15), today=date(2026, 10, 1))
    assert days == 0
    assert rules.fine(days) == 0


def test_late_return_counts_days_after_due_date():
    days = rules.overdue_days(DUE, returned_on=date(2026, 9, 20), today=date(2026, 10, 1))
    assert days == 5


def test_fine_is_days_times_daily_rate():
    assert rules.fine(5, per_day=10) == 50


def test_unreturned_book_is_overdue_until_today():
    today = date(2026, 9, 18)
    assert rules.overdue_days(DUE, returned_on=None, today=today) == 3
    assert rules.is_overdue(DUE, returned_on=None, today=today)


def test_returned_book_is_not_overdue_even_if_returned_late():
    assert not rules.is_overdue(DUE, returned_on=date(2026, 9, 20), today=date(2026, 10, 1))


def test_free_copy_is_issued_to_reader_without_debts():
    rules.check_issue(copy_on_loan=False, reader_overdue_loans=0)


def test_copy_on_loan_is_not_issued():
    with pytest.raises(rules.RuleViolation, match="уже выдан"):
        rules.check_issue(copy_on_loan=True, reader_overdue_loans=0)


def test_reader_with_overdue_loan_is_refused():
    with pytest.raises(rules.RuleViolation, match="просроченных"):
        rules.check_issue(copy_on_loan=False, reader_overdue_loans=1)


def test_loan_cannot_be_returned_twice():
    with pytest.raises(rules.RuleViolation, match="уже закрыта"):
        rules.check_return(ISSUED, returned_on=DUE, return_date=DUE, today=DUE)


def test_return_date_cannot_precede_issue_or_be_in_future():
    with pytest.raises(rules.RuleViolation):
        rules.check_return(ISSUED, None, return_date=date(2026, 8, 31), today=DUE)
    with pytest.raises(rules.RuleViolation):
        rules.check_return(ISSUED, None, return_date=date(2026, 9, 16), today=DUE)
