"""Transfers between a customer's own accounts: no transfer limits, account names as parties."""

import pytest
from sqlalchemy import select

from app.banking import make_tr_iban
from app.db import SessionLocal
from app.models import Account, Transaction, Transfer
from tests.conftest import login

CHECKING = make_tr_iban("0000000000000001")
SAVINGS = make_tr_iban("0000000000000002")
OTHER = make_tr_iban("0000000000000003")


@pytest.fixture
async def own(client, create_customer):
    await create_customer(
        accounts=[
            {"id": 1, "name": "Vadesiz", "iban": CHECKING, "balance_kurus": 30_000_000},
            {"id": 2, "name": "Birikim", "iban": SAVINGS, "balance_kurus": 0},
        ]
    )
    await create_customer(
        customer_no="987654321",
        full_name="Ömer Can",
        accounts=[{"id": 3, "name": "Hesap", "iban": OTHER, "balance_kurus": 0}],
    )
    token = (await login(client, "123456789", "123456")).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def body(amount: int, key: str, to_iban: str = SAVINGS, **extra) -> dict:
    return {
        "from_account_id": 1, "to_iban": to_iban, "amount_kurus": amount,
        "idempotency_key": key, **extra,
    }


async def test_own_transfer_shows_account_names(client, own):
    response = await client.post("/transfers", headers=own, json=body(10_000, "own-key-0001"))
    assert response.status_code == 201, response.text
    data = response.json()
    assert data["recipient"] == "Birikim"
    assert data["description"] == "Hesaplar arası transfer"
    async with SessionLocal() as session:
        rows = {
            t.account_id: t.counterparty for t in await session.scalars(select(Transaction))
        }
    assert rows == {1: "Birikim", 2: "Vadesiz"}


async def test_own_transfer_ignores_limits(client, own):
    # 150.000 TL in one go: over both the per-transfer (50.000) and 24-hour (100.000) limits.
    response = await client.post("/transfers", headers=own, json=body(15_000_000, "own-key-0002"))
    assert response.status_code == 201, response.text
    async with SessionLocal() as session:
        assert (await session.get(Account, 2)).balance_kurus == 15_000_000


async def test_own_transfers_dont_use_daily_limit(client, own):
    assert (await client.post(
        "/transfers", headers=own, json=body(9_000_000, "own-key-0003")
    )).status_code == 201
    # The full 100.000 TL daily allowance is still available for other customers.
    for i in range(2):
        response = await client.post(
            "/transfers", headers=own, json=body(5_000_000, f"other-key-{i}", to_iban=OTHER)
        )
        assert response.status_code == 201, response.text
    response = await client.post(
        "/transfers", headers=own, json=body(1, "other-key-2", to_iban=OTHER)
    )
    assert response.status_code == 400


async def test_own_transfer_replay_uses_own_default_description(client, own):
    first = await client.post("/transfers", headers=own, json=body(500, "own-key-0004"))
    again = await client.post("/transfers", headers=own, json=body(500, "own-key-0004"))
    assert first.status_code == again.status_code == 201
    assert first.json()["id"] == again.json()["id"]


async def test_other_customer_transfer_keeps_limit(client, own):
    response = await client.post(
        "/transfers", headers=own, json=body(5_000_001, "other-key-9", to_iban=OTHER)
    )
    assert response.status_code == 400


async def test_legacy_own_transfer_blank_description_replay(client, own):
    payload = body(500, "legacy-own-key")
    first = await client.post("/transfers", headers=own, json=payload)
    assert first.status_code == 201, first.text
    # Before own-account support, this identical blank-description request stored
    # "Para transferi". Reproduce that persisted state across an application upgrade.
    async with SessionLocal() as session:
        transfer = await session.get(Transfer, first.json()["id"])
        transfer.description = "Para transferi"
        for transaction in await session.scalars(
            select(Transaction).where(Transaction.transfer_id == transfer.id)
        ):
            transaction.description = "Para transferi"
        await session.commit()

    replay = await client.post("/transfers", headers=own, json=payload)
    assert replay.status_code == 201, replay.text
    assert replay.json()["id"] == first.json()["id"]


async def test_external_transfer_own_description_is_not_a_blank_default(client, own):
    payload = body(500, "external-description-key", to_iban=OTHER)
    first = await client.post(
        "/transfers", headers=own,
        json={**payload, "description": "Hesaplar arası transfer"},
    )
    assert first.status_code == 201, first.text

    # For an external recipient, blank means "Para transferi". The own-account
    # compatibility exception must not hide a changed external description.
    replay = await client.post("/transfers", headers=own, json=payload)
    assert replay.status_code == 409, replay.text
