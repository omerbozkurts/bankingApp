"""Regression tests for gaps found in review: long names in transfers, account cap races."""

import asyncio

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.banking import make_tr_iban
from app.db import SessionLocal, engine
from app.models import Account, Customer
from app.routers import accounts as accounts_router
from app.schemas import OpenAccountRequest
from tests.conftest import login


async def test_registered_name_can_receive_transfer(client, create_customer):
    # 60 one-letter words is a valid 119-character name; masked word by word it used to
    # overflow transactions.counterparty (String(120)) and the transfer failed with 500.
    registered = await client.post("/auth/register", json={
        "national_id": "10000000146", "full_name": " ".join(["A"] * 60),
        "birth_date": "1990-01-01", "password": "582963",
    })
    assert registered.status_code == 201
    async with SessionLocal() as session:
        recipient_iban = (await session.scalar(select(Account))).iban
    sender = await create_customer(accounts=[{
        "name": "Sender", "iban": make_tr_iban("0000000000000002"), "balance_kurus": 1000,
    }])
    token = (await login(client, sender.customer_no, "123456")).json()["access_token"]
    async with SessionLocal() as session:
        source_id = await session.scalar(
            select(Account.id).where(Account.customer_id == sender.id)
        )
    response = await client.post("/transfers", headers={"Authorization": f"Bearer {token}"}, json={
        "from_account_id": source_id, "to_iban": recipient_iban,
        "amount_kurus": 100, "idempotency_key": "review-name-0001",
    })
    assert response.status_code == 201, response.text


async def test_concurrent_account_opening_respects_cap(create_customer, monkeypatch):
    customer = await create_customer(accounts=[{
        "name": f"Account {i}", "iban": make_tr_iban(f"{i:016d}"),
    } for i in range(1, 10)])
    original = AsyncSession.scalars

    async def slow_count(session, statement, *args, **kwargs):
        result = await original(session, statement, *args, **kwargs)
        # Widen the count-to-insert window so unlocked requests would all see nine accounts.
        if str(statement).startswith("SELECT accounts.id"):
            await asyncio.sleep(0.2)
        return result

    monkeypatch.setattr(AsyncSession, "scalars", slow_count)

    # Opening a new connection can take longer than the window above, so the requests would run
    # one after another and never race. Open three pooled connections up front.
    warm = [await engine.connect() for _ in range(3)]
    for conn in warm:
        await conn.close()

    async def open_one() -> int:
        async with SessionLocal() as session:
            owner = await session.get(Customer, customer.id)
            try:
                await accounts_router.open_account(
                    OpenAccountRequest(kind="checking", name="New"), owner, session
                )
            except HTTPException as e:
                return e.status_code
            return 201

    statuses = await asyncio.wait_for(asyncio.gather(*[open_one() for _ in range(3)]), timeout=20)
    assert sorted(statuses) == [201, 409, 409]
    async with SessionLocal() as session:
        count = await session.scalar(
            select(func.count()).select_from(Account).where(Account.customer_id == customer.id)
        )
    assert count == 10


async def test_account_opening_retries_iban_collision(client, create_customer, monkeypatch):
    taken = make_tr_iban("0000000000000005")
    customer = await create_customer(accounts=[{"name": "Main", "iban": taken}])
    token = (await login(client, customer.customer_no, "123456")).json()["access_token"]
    ibans = iter([taken, make_tr_iban("0000000000000006")])
    monkeypatch.setattr(accounts_router, "random_iban", lambda: next(ibans))
    response = await client.post(
        "/accounts", headers={"Authorization": f"Bearer {token}"},
        json={"kind": "checking", "name": "Second"},
    )
    assert response.status_code == 201, response.text
    assert response.json()["iban"] == make_tr_iban("0000000000000006")


async def test_amount_must_be_a_json_integer(client, create_customer):
    customer = await create_customer(accounts=[{
        "name": "Main", "iban": make_tr_iban("0000000000000003"), "balance_kurus": 1000,
    }])
    token = (await login(client, customer.customer_no, "123456")).json()["access_token"]
    for amount in [True, "100"]:
        response = await client.post(
            "/transfers", headers={"Authorization": f"Bearer {token}"}, json={
                "from_account_id": 1, "to_iban": make_tr_iban("0000000000000004"),
                "amount_kurus": amount, "idempotency_key": "review-strict-01",
            },
        )
        assert response.status_code == 422, amount
