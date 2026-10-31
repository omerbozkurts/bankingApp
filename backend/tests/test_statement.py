"""Date-range filtering of movements and the CSV statement."""

import csv
import io
from datetime import UTC, date, datetime

import pytest
from sqlalchemy import update

from app.banking import make_tr_iban
from app.db import SessionLocal
from app.models import Transaction
from app.statement import MAX_STATEMENT_DAYS, format_tl, safe_cell, statement_csv
from tests.conftest import login

# (UTC time, amount, description); Turkish time is UTC+3, so the second row is already
# 1 November in Turkey and the last one is still 30 November.
MOVEMENTS = [
    (datetime(2026, 10, 31, 12, 0, tzinfo=UTC), 100_000, "Maaş"),
    (datetime(2026, 10, 31, 21, 30, tzinfo=UTC), -25_050, '=HYPERLINK("x")'),
    (datetime(2026, 11, 15, 9, 0, tzinfo=UTC), -1_000, "Market"),
    (datetime(2026, 11, 30, 20, 59, tzinfo=UTC), 500, "+İade"),
]


@pytest.fixture
async def bank(client, create_customer):
    await create_customer(
        accounts=[{"id": 1, "name": "Vadesiz", "iban": make_tr_iban("1".zfill(16))}]
    )
    await create_customer(
        customer_no="987654321",
        password="654321",
        accounts=[{"id": 2, "name": "Vadesiz", "iban": make_tr_iban("2".zfill(16))}],
    )
    async with SessionLocal() as session:
        balance = 0
        for when, amount, description in MOVEMENTS:
            balance += amount
            row = Transaction(
                account_id=1,
                amount_kurus=amount,
                balance_after_kurus=balance,
                description=description,
                counterparty="Al*** Ka***" if amount < 0 else None,
            )
            session.add(row)
            await session.flush()
            await session.execute(
                update(Transaction).where(Transaction.id == row.id).values(created_at=when)
            )
        await session.commit()
    token = (await login(client, "123456789", "123456")).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_format_tl_and_safe_cell():
    assert [format_tl(k) for k in (0, 5, 125_050, -125_050, -7)] == [
        "0,00",
        "0,05",
        "1250,50",
        "-1250,50",
        "-0,07",
    ]
    assert [safe_cell(t) for t in ("=1+1", "+90", "-x", "@a", "\tx", "Kira", "")] == [
        "'=1+1",
        "'+90",
        "'-x",
        "'@a",
        "'\tx",
        "Kira",
        "",
    ]


async def descriptions(client, bank, query: str) -> list[str]:
    response = await client.get(f"/accounts/1/transactions?{query}", headers=bank)
    assert response.status_code == 200, response.text
    return [t["description"] for t in response.json()["items"]]


async def test_filter_uses_turkish_days(client, bank):
    assert await descriptions(client, bank, "from_date=2026-11-01&to_date=2026-11-30") == [
        "+İade",
        "Market",
        '=HYPERLINK("x")',
    ]
    assert await descriptions(client, bank, "to_date=2026-10-31") == ["Maaş"]
    assert await descriptions(client, bank, "from_date=2026-11-30") == ["+İade"]
    assert await descriptions(client, bank, "from_date=2026-12-01") == []


async def test_filter_pages(client, bank):
    query = "from_date=2026-11-01&to_date=2026-11-30&limit=2"
    first = (await client.get(f"/accounts/1/transactions?{query}", headers=bank)).json()
    assert len(first["items"]) == 2 and first["next_before_id"] is not None
    rest = await descriptions(client, bank, f"{query}&before_id={first['next_before_id']}")
    assert rest == ['=HYPERLINK("x")']


@pytest.mark.parametrize(
    "query",
    [
        "from_date=2026-11-02&to_date=2026-11-01",
        "from_date=9999-12-31",
        "to_date=1900-01-01",
        "from_date=31.10.2026",
    ],
)
async def test_invalid_ranges(client, bank, query):
    response = await client.get(f"/accounts/1/transactions?{query}", headers=bank)
    assert response.status_code == 422


async def test_statement_csv(client, bank):
    response = await client.get(
        "/accounts/1/statement?from_date=2026-11-01&to_date=2026-11-30", headers=bank
    )
    assert response.status_code == 200, response.text
    assert response.headers["content-type"] == "text/csv; charset=utf-8"
    assert response.headers["cache-control"] == "no-store"
    iban_tail = make_tr_iban("1".zfill(16))[-4:]
    assert response.headers["content-disposition"] == (
        f'attachment; filename="ABBank-ekstre-{iban_tail}-20261101-20261130.csv"'
    )
    text = response.content.decode("utf-8")
    assert text.startswith("﻿")
    rows = list(csv.reader(io.StringIO(text.lstrip("﻿")), delimiter=";"))
    assert rows == [
        ["Tarih", "Açıklama", "Karşı taraf", "Tutar (TL)", "Bakiye (TL)"],
        # Oldest first, times in Turkish time, formula-like text defused.
        ["01.11.2026 00:30", '\'=HYPERLINK("x")', "Al*** Ka***", "-250,50", "749,50"],
        ["15.11.2026 12:00", "Market", "Al*** Ka***", "-10,00", "739,50"],
        ["30.11.2026 23:59", "'+İade", "", "5,00", "744,50"],
    ]


async def test_empty_statement_has_only_the_header(client, bank):
    response = await client.get(
        "/accounts/1/statement?from_date=2025-01-01&to_date=2025-01-31", headers=bank
    )
    assert response.status_code == 200
    assert response.text.strip().lstrip("﻿") == "Tarih;Açıklama;Karşı taraf;Tutar (TL);Bakiye (TL)"


@pytest.mark.parametrize(
    ("query", "status"),
    [
        ("from_date=2026-11-01", 422),
        ("to_date=2026-11-01", 422),
        ("from_date=2026-11-02&to_date=2026-11-01", 422),
        (f"from_date=2025-01-01&to_date={date(2025, 1, 1).replace(year=2026)}", 200),
        ("from_date=2025-01-01&to_date=2026-01-02", 422),
    ],
)
async def test_statement_range_rules(client, bank, query, status):
    response = await client.get(f"/accounts/1/statement?{query}", headers=bank)
    assert response.status_code == status, response.text
    if status == 422 and "2026-01-02" in query:
        assert str(MAX_STATEMENT_DAYS) in response.json()["detail"]


async def test_statement_row_cap(client, bank, monkeypatch):
    monkeypatch.setattr("app.routers.accounts.MAX_STATEMENT_ROWS", 2)
    too_many = await client.get(
        "/accounts/1/statement?from_date=2026-10-01&to_date=2026-11-30", headers=bank
    )
    assert too_many.status_code == 422
    fits = await client.get(
        "/accounts/1/statement?from_date=2026-11-02&to_date=2026-11-30", headers=bank
    )
    assert fits.status_code == 200


async def test_statement_is_private(client, bank):
    ali = (await login(client, "987654321", "654321")).json()["access_token"]
    query = "from_date=2026-10-01&to_date=2026-11-30"
    other = await client.get(
        f"/accounts/1/statement?{query}", headers={"Authorization": f"Bearer {ali}"}
    )
    assert other.status_code == 404
    assert (await client.get(f"/accounts/1/statement?{query}")).status_code == 401


async def test_cors_exposes_the_file_name(client, bank):
    response = await client.get(
        "/accounts/1/statement?from_date=2026-11-01&to_date=2026-11-30",
        headers={**bank, "Origin": "http://localhost:8081"},
    )
    assert "content-disposition" in response.headers["access-control-expose-headers"].lower()


def test_csv_quotes_separators_newlines_and_carriage_returns():
    rows = [
        Transaction(
            account_id=1,
            amount_kurus=-100,
            balance_after_kurus=None,
            description='a;b "c"\nsatır=2',
            counterparty="\r=cmd",
            created_at=datetime(2026, 11, 1, 9, 0, tzinfo=UTC),
        )
    ]
    text = statement_csv(rows)
    parsed = list(csv.reader(io.StringIO(text.lstrip("﻿"), newline=""), delimiter=";"))
    assert parsed[1] == ["01.11.2026 12:00", 'a;b "c"\nsatır=2', "'\r=cmd", "-1,00", ""]


@pytest.mark.parametrize(
    ("query", "status"),
    [
        ("from_date=2024-01-01&to_date=2024-12-31", 200),  # leap year: exactly 366 days
        ("from_date=2024-01-01&to_date=2025-01-01", 422),  # 367 days
    ],
)
async def test_statement_leap_year_limit(client, bank, query, status):
    response = await client.get(f"/accounts/1/statement?{query}", headers=bank)
    assert response.status_code == status, response.text


async def test_filtered_transactions_are_private(client, bank):
    ali = (await login(client, "987654321", "654321")).json()["access_token"]
    response = await client.get(
        "/accounts/1/transactions?from_date=2026-10-01&to_date=2026-11-30",
        headers={"Authorization": f"Bearer {ali}"},
    )
    assert response.status_code == 404
