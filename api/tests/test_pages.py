"""Тесты страниц: экраны открываются и показывают данные выдачи."""

from tests.conftest import LOGIN, sql


def test_pages_redirect_to_login_without_session(client):
    response = client.get("/loans", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/login"


def test_loans_page_and_card_show_copy_inventory_number(client):
    client.post("/login", data=LOGIN)
    loan_id = sql("SELECT id FROM loans ORDER BY issued_on DESC, id DESC LIMIT 1")
    inventory_no = sql("SELECT c.inventory_no FROM loans l JOIN copies c ON c.id = l.copy_id WHERE l.id = $1", loan_id)

    assert inventory_no in client.get("/loans").text
    assert inventory_no in client.get(f"/loans/{loan_id}").text


def test_summary_page_opens(client):
    client.post("/login", data=LOGIN)
    response = client.get("/summary")
    assert response.status_code == 200
    assert "Чаще всего берут" in response.text
