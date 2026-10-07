"""Тесты операций программного интерфейса: коды ответа, состав полей, ошибки."""

from datetime import timedelta

import pytest

from app import services
from tests.conftest import LOGIN, sql

FREE_COPY = """
    SELECT id FROM copies c
    WHERE NOT EXISTS (SELECT 1 FROM loans l WHERE l.copy_id = c.id AND l.returned_on IS NULL)
    ORDER BY id LIMIT 1 OFFSET $1
"""
CLEAN_READER = """
    SELECT id FROM readers r
    WHERE NOT EXISTS (SELECT 1 FROM loans l
                      WHERE l.reader_id = r.id AND l.returned_on IS NULL AND l.due_on < current_date)
    ORDER BY id LIMIT 1 OFFSET $1
"""

LOAN_FIELDS = {"id", "issued_on", "due_on", "returned_on", "status", "overdue_days", "fine",
               "reader", "copy", "book"}


# --- авторизация ------------------------------------------------------------

def test_login_returns_account(client):
    response = client.post("/api/login", json=LOGIN)
    assert response.status_code == 200
    assert response.json()["login"] == LOGIN["login"]
    assert "library_session" in response.cookies


def test_login_with_wrong_password_is_401(client):
    response = client.post("/api/login", json={**LOGIN, "password": "wrong"})
    assert response.status_code == 401


def test_login_without_fields_is_422(client):
    assert client.post("/api/login", json={}).status_code == 422


@pytest.mark.parametrize("path", [
    "/api/me", "/api/loans", "/api/loans/1", "/api/readers", "/api/readers/1",
    "/api/books", "/api/books/1", "/api/summary",
])
def test_operations_require_authorization(client, path):
    assert client.get(path).status_code == 401


def test_issue_requires_authorization(client):
    assert client.post("/api/loans", json={"copy_id": 1, "reader_id": 1}).status_code == 401


# --- список выдач -------------------------------------------------------------

def test_loans_list_returns_requested_page(authorized):
    response = authorized.get("/api/loans", params={"page": 2, "size": 7})
    assert response.status_code == 200
    body = response.json()
    assert len(body["items"]) == 7
    assert body["page"] == 2 and body["size"] == 7
    assert body["total"] >= 300
    assert set(body["items"][0]) == LOAN_FIELDS


@pytest.mark.parametrize("params", [{"size": 0}, {"size": 101}, {"page": 0}, {"status": "lost"},
                                    {"reader_id": "abc"}])
def test_loans_list_rejects_bad_parameters(authorized, params):
    assert authorized.get("/api/loans", params=params).status_code == 422


def test_overdue_filter_returns_only_overdue_loans(authorized):
    body = authorized.get("/api/loans", params={"status": "overdue", "size": 100}).json()
    assert body["total"] > 0
    assert all(item["status"] == "overdue" and item["fine"] > 0 for item in body["items"])


def test_reader_filter_returns_only_that_reader(authorized):
    body = authorized.get("/api/loans", params={"reader_id": 3, "size": 100}).json()
    assert all(item["reader"]["id"] == 3 for item in body["items"])


def test_missing_loan_is_404(authorized):
    assert authorized.get("/api/loans/999999").status_code == 404


# --- выдача и возврат --------------------------------------------------------

def test_issue_and_return_late_charges_fine(authorized, monkeypatch):
    copy_id, reader_id = sql(FREE_COPY, 0), sql(CLEAN_READER, 0)

    response = authorized.post("/api/loans", json={"copy_id": copy_id, "reader_id": reader_id})
    assert response.status_code == 201
    loan = response.json()
    assert loan["status"] == "active" and loan["returned_on"] is None
    assert set(loan) == LOAN_FIELDS

    # Возврат через пять дней после срока.
    late = services.today() + timedelta(days=19)
    monkeypatch.setattr(services, "today", lambda: late)
    returned = authorized.post(f"/api/loans/{loan['id']}/return").json()
    assert returned["status"] == "returned"
    assert returned["overdue_days"] == 5
    assert returned["fine"] == 50


def test_copy_on_loan_is_not_issued_again(authorized):
    copy_id, reader_id = sql(FREE_COPY, 1), sql(CLEAN_READER, 1)
    assert authorized.post("/api/loans", json={"copy_id": copy_id, "reader_id": reader_id}).status_code == 201

    other = sql(CLEAN_READER, 2)
    response = authorized.post("/api/loans", json={"copy_id": copy_id, "reader_id": other})
    assert response.status_code == 409


def test_reader_with_overdue_loan_is_refused(authorized):
    debtor = sql("SELECT reader_id FROM loans WHERE returned_on IS NULL AND due_on < current_date LIMIT 1")
    response = authorized.post("/api/loans", json={"copy_id": sql(FREE_COPY, 2), "reader_id": debtor})
    assert response.status_code == 409
    assert "просроченных" in response.json()["detail"]


def test_issue_of_missing_copy_is_404(authorized):
    response = authorized.post("/api/loans", json={"copy_id": 999999, "reader_id": 1})
    assert response.status_code == 404


def test_loan_cannot_be_returned_twice(authorized):
    loan_id = sql("SELECT id FROM loans WHERE returned_on IS NOT NULL LIMIT 1")
    assert authorized.post(f"/api/loans/{loan_id}/return").status_code == 409


def test_return_in_future_is_409(authorized):
    loan_id = sql("SELECT id FROM loans WHERE returned_on IS NULL LIMIT 1")
    future = (services.today() + timedelta(days=3)).isoformat()
    response = authorized.post(f"/api/loans/{loan_id}/return", json={"returned_on": future})
    assert response.status_code == 409


# --- карточки и сводка -------------------------------------------------------

def test_reader_card_contains_loans_and_stats(authorized):
    body = authorized.get("/api/readers/1").json()
    assert body["id"] == 1
    assert body["stats"]["loans_total"] == len(body["loans"])
    assert body["stats"]["fines_total"] == sum(loan["fine"] for loan in body["loans"])


def test_book_card_lists_copies_with_status(authorized):
    book_id = sql("SELECT book_id FROM copies GROUP BY book_id HAVING count(*) > 1 LIMIT 1")
    body = authorized.get(f"/api/books/{book_id}").json()
    assert len(body["copies"]) > 1
    for copy in body["copies"]:
        assert copy["status"] in ("free", "on_loan")
        assert (copy["loan"] is None) == (copy["status"] == "free")


def test_summary_matches_loan_list(authorized):
    summary = authorized.get("/api/summary").json()
    active = authorized.get("/api/loans", params={"status": "active", "size": 1}).json()["total"]
    overdue = authorized.get("/api/loans", params={"status": "overdue", "size": 1}).json()["total"]
    assert summary["on_hands"] == active
    assert summary["overdue"] == overdue
    loans = [b["loans"] for b in summary["top_books"]]
    assert len(loans) == 10 and loans == sorted(loans, reverse=True)
