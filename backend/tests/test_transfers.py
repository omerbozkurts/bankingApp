import asyncio
from datetime import UTC, datetime, timedelta

import httpx
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.banking import make_tr_iban
from app.config import get_settings
from app.db import SessionLocal
from app.main import app
from app.models import Account, Transaction, Transfer
from tests.conftest import login


@pytest.fixture
async def bank(client, create_customer):
    for i, no, name, balance in [
        (1, "123456789", "Deniz Yılmaz", 30_000_000),
        (2, "987654321", "Ömer Can", 1000),
    ]:
        await create_customer(
            customer_no=no,
            full_name=name,
            accounts=[
                {
                    "id": i,
                    "name": "Hesap",
                    "iban": make_tr_iban(f"{i:016}"),
                    "balance_kurus": balance,
                }
            ],
        )
    response = await login(client, "123456789", "123456")
    return (
        {"Authorization": f"Bearer {response.json()['access_token']}"},
        dict(
            from_account_id=1,
            to_iban=make_tr_iban("0000000000000002"),
            amount_kurus=1000,
            idempotency_key="transfer-0001",
        ),
    )


async def balances():
    async with SessionLocal() as session:
        return list(await session.scalars(select(Account.balance_kurus).order_by(Account.id)))


async def test_success(client, bank):
    headers, body = bank
    response = await client.post("/transfers", json=body, headers=headers)
    assert response.status_code == 201, response.text
    data = response.json()
    assert data["description"] == "Para transferi"
    assert data["recipient"] == "Öm*** Ca***"
    assert data["from_balance_after_kurus"] == 29_999_000
    assert await balances() == [29_999_000, 2000]
    async with SessionLocal() as session:
        rows = list(await session.scalars(select(Transaction).order_by(Transaction.account_id)))
        assert len(rows) == 2
        assert [r.amount_kurus for r in rows] == [-1000, 1000]
        assert [r.balance_after_kurus for r in rows] == [29_999_000, 2000]
        assert [r.counterparty for r in rows] == ["Öm*** Ca***", "De*** Yı***"]
        assert all(r.transfer_id == data["id"] for r in rows)
        assert all(r.description == "Para transferi" for r in rows)


async def test_idempotency_and_spaces(client, bank):
    headers, body = bank
    body["to_iban"] = " ".join(body["to_iban"][i : i + 4] for i in range(0, 26, 4)).lower()
    first = await client.post("/transfers", json=body, headers=headers)
    again = await client.post("/transfers", json=body, headers=headers)
    assert first.status_code == again.status_code == 201
    assert first.json() == again.json()
    assert await balances() == [29_999_000, 2000]
    body["amount_kurus"] += 1
    assert (await client.post("/transfers", json=body, headers=headers)).status_code == 409


@pytest.mark.parametrize(
    ("patch", "status"),
    [
        ({"amount_kurus": 5_000_001}, 400),
        ({"from_account_id": 2}, 404),
        ({"to_iban": make_tr_iban("0000000000000003")}, 404),
        ({"to_iban": "invalid"}, 422),
        ({"to_iban": make_tr_iban("0000000000000001")}, 400),
        ({"amount_kurus": 0}, 422),
        ({"amount_kurus": -1}, 422),
    ],
)
async def test_rejections(client, bank, patch, status):
    headers, body = bank
    response = await client.post("/transfers", json={**body, **patch}, headers=headers)
    assert response.status_code == status, response.text
    if status == 422:
        assert response.json()["detail"] == (
            "Geçerli bir TR IBAN girin." if "to_iban" in patch else "Gönderilen bilgiler geçersiz."
        )
        assert response.json()["errors"]
    assert await balances() == [30_000_000, 1000]


async def test_insufficient(client, bank):
    headers, body = bank
    async with SessionLocal() as session:
        (await session.get(Account, 1)).balance_kurus = 999
        await session.commit()
    response = await client.post("/transfers", json=body, headers=headers)
    assert response.status_code == 400
    assert response.json()["detail"] == "Yetersiz bakiye."
    assert await balances() == [999, 1000]


async def test_daily_limit(client, bank):
    headers, body = bank
    for i, amount in enumerate([5_000_000, 5_000_000, 1]):
        response = await client.post(
            "/transfers",
            headers=headers,
            json={**body, "amount_kurus": amount, "idempotency_key": f"daily-key-{i}"},
        )
        assert response.status_code == (201 if i < 2 else 400), response.text
    assert await balances() == [20_000_000, 10_001_000]


async def test_lookup_and_auth(client, bank):
    headers, body = bank
    assert (await client.post("/transfers", json=body)).status_code == 401
    path = "/recipients/lookup"
    assert (await client.get(path, params={"iban": body["to_iban"]})).status_code == 401
    response = await client.get(path, headers=headers, params={"iban": body["to_iban"].lower()})
    assert response.status_code == 200
    assert response.json() == {"iban": body["to_iban"], "masked_name": "Öm*** Ca***"}
    for iban, status in [("bad", 422), (make_tr_iban("0000000000000003"), 404)]:
        assert (
            await client.get(path, headers=headers, params={"iban": iban})
        ).status_code == status


@pytest.mark.parametrize("same_key", [False, True])
async def test_parallel_source(client, bank, same_key):
    # get_session is not overridden: each ASGI request opens its own database session.
    headers, body = bank
    async with SessionLocal() as session:
        (await session.get(Account, 1)).balance_kurus = 1500
        await session.commit()
    responses = await asyncio.wait_for(
        asyncio.gather(
            *[
                client.post(
                    "/transfers",
                    headers=headers,
                    json={
                        **body,
                        "idempotency_key": "parallel-key" if same_key else f"parallel-key-{i}",
                    },
                )
                for i in range(5)
            ]
        ),
        timeout=20,
    )
    assert all(r.status_code in (201, 400) for r in responses)
    assert sum(r.status_code == 201 for r in responses) == (5 if same_key else 1)
    assert await balances() == [500, 2000]
    async with SessionLocal() as session:
        assert len(list(await session.scalars(select(Transfer)))) == 1
    if same_key:
        assert len({r.json()["id"] for r in responses}) == 1


async def test_opposite_parallel(client, bank, monkeypatch):
    headers, body = bank
    response = await login(client, "987654321", "123456")
    other = {"Authorization": f"Bearer {response.json()['access_token']}"}
    # Synchronize after both requests have read accounts, before either takes row locks.
    # Keep real PostgreSQL queries and a distinct production session per request.
    barrier = asyncio.Barrier(2)
    sessions = []
    original = AsyncSession.scalars

    async def synchronized_scalars(session, statement, *args, **kwargs):
        if statement.column_descriptions[0].get("entity") is Account:
            sessions.append(session)
            await barrier.wait()
        return await original(session, statement, *args, **kwargs)

    monkeypatch.setattr(AsyncSession, "scalars", synchronized_scalars)
    responses = await asyncio.wait_for(
        asyncio.gather(
            client.post("/transfers", headers=headers, json=body),
            client.post(
                "/transfers",
                headers=other,
                json={**body, "from_account_id": 2, "to_iban": make_tr_iban("0000000000000001")},
            ),
        ),
        timeout=20,
    )
    assert [r.status_code for r in responses] == [201, 201]
    assert len(sessions) == 2 and sessions[0] is not sessions[1]
    monkeypatch.setattr(AsyncSession, "scalars", original)
    assert await balances() == [30_000_000, 1000]


async def test_daily_limit_parallel_across_accounts(client, bank):
    headers, body = bank
    async with SessionLocal() as session:
        session.add(
            Account(
                id=3,
                customer_id=1,
                name="Diğer hesap",
                iban=make_tr_iban("0000000000000003"),
                balance_kurus=20_000_000,
            )
        )
        await session.commit()
    responses = await asyncio.wait_for(
        asyncio.gather(
            *[
                client.post(
                    "/transfers",
                    headers=headers,
                    json={
                        **body,
                        "from_account_id": 1 if i % 2 else 3,
                        "amount_kurus": 4_000_000,
                        "idempotency_key": f"daily-parallel-{i}",
                    },
                )
                for i in range(3)
            ]
        ),
        timeout=20,
    )
    assert sorted(r.status_code for r in responses) == [201, 201, 400]
    async with SessionLocal() as session:
        assert sum(await session.scalars(select(Transfer.amount_kurus))) == 8_000_000


async def test_rolling_24_hour_limit(client, bank):
    headers, body = bank
    for i in range(2):
        assert (
            await client.post(
                "/transfers",
                headers=headers,
                json={**body, "amount_kurus": 5_000_000, "idempotency_key": f"rolling-key-{i}"},
            )
        ).status_code == 201
    async with SessionLocal() as session:
        for transfer in await session.scalars(select(Transfer)):
            transfer.created_at = datetime.now(UTC) - timedelta(hours=25)
        await session.commit()
    response = await client.post("/transfers", headers=headers, json=body)
    assert response.status_code == 201


async def test_changed_description_conflicts(client, bank):
    headers, body = bank
    assert (await client.post("/transfers", headers=headers, json=body)).status_code == 201
    response = await client.post(
        "/transfers", headers=headers, json={**body, "description": "Farklı ödeme"}
    )
    assert response.status_code == 409


async def test_huge_amount_rejected_without_overflow(client, bank):
    headers, body = bank
    response = await client.post(
        "/transfers", headers=headers, json={**body, "amount_kurus": 2**100}
    )
    assert response.status_code == 400
    assert await balances() == [30_000_000, 1000]


async def test_account_id_overflow_is_client_error(bank):
    headers, body = bank
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app, raise_app_exceptions=False),
        base_url="http://test",
    ) as client:
        response = await client.post(
            "/transfers", headers=headers, json={**body, "from_account_id": 2**63}
        )
    assert response.status_code in (404, 422), response.text


async def test_recipient_lookup_is_rate_limited_per_customer(client, create_customer):
    await create_customer(accounts=[{"name": "V", "iban": make_tr_iban("0" * 15 + "9")}])
    token = (await login(client, "123456789", "123456")).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    params = {"iban": make_tr_iban("1" * 16)}  # valid but unknown: a 404 still counts
    for _ in range(get_settings().lookup_rate_limit):
        response = await client.get("/recipients/lookup", params=params, headers=headers)
        assert response.status_code == 404
    limited = await client.get("/recipients/lookup", params=params, headers=headers)
    assert limited.status_code == 429
