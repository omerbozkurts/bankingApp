"""Credit accounts: one per customer, interest-free revolving limit, own-account use only."""

import asyncio

import pytest

from app.banking import make_tr_iban
from app.db import SessionLocal
from app.models import Account
from tests.conftest import login

CHECKING = make_tr_iban("0000000000000001")
OTHER = make_tr_iban("0000000000000003")
LIMIT = 2_000_000


@pytest.fixture
async def bank(client, create_customer):
    await create_customer(
        accounts=[{"id": 1, "name": "Vadesiz", "iban": CHECKING, "balance_kurus": 100_000}]
    )
    await create_customer(
        customer_no="987654321",
        full_name="Ömer Can",
        accounts=[{"id": 3, "name": "Hesap", "iban": OTHER, "balance_kurus": 100_000}],
    )
    token = (await login(client, "123456789", "123456")).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    response = await client.post(
        "/accounts", headers=headers, json={"kind": "credit", "name": "Kredili Hesap"}
    )
    assert response.status_code == 201, response.text
    return headers, response.json()


async def send(client, headers, from_id, to_iban, amount, key):
    return await client.post("/transfers", headers=headers, json={
        "from_account_id": from_id, "to_iban": to_iban, "amount_kurus": amount,
        "idempotency_key": key,
    })


async def balance(account_id: int) -> int:
    async with SessionLocal() as session:
        return (await session.get(Account, account_id)).balance_kurus


async def test_open_credit_account(client, bank):
    headers, credit = bank
    assert credit["kind"] == "credit"
    assert credit["balance_kurus"] == 0
    assert credit["credit_limit_kurus"] == LIMIT
    assert credit["goal_kurus"] is None
    again = await client.post(
        "/accounts", headers=headers, json={"kind": "credit", "name": "İkinci"}
    )
    assert again.status_code == 409


async def test_credit_account_rejects_goal(client, bank):
    headers, _ = bank
    response = await client.post(
        "/accounts", headers=headers,
        json={"kind": "credit", "name": "Hedefli", "goal_kurus": 1000},
    )
    assert response.status_code == 422


async def test_draw_and_repay(client, bank):
    headers, credit = bank
    drawn = await send(client, headers, credit["id"], CHECKING, 500_000, "credit-draw-01")
    assert drawn.status_code == 201, drawn.text
    assert drawn.json()["from_balance_after_kurus"] == -500_000
    assert await balance(credit["id"]) == -500_000
    assert await balance(1) == 600_000

    repaid = await send(client, headers, 1, credit["iban"], 200_000, "credit-repay-01")
    assert repaid.status_code == 201, repaid.text
    assert await balance(credit["id"]) == -300_000


async def test_draw_up_to_limit_only(client, bank):
    headers, credit = bank
    over = await send(client, headers, credit["id"], CHECKING, LIMIT + 1, "credit-over-01")
    assert over.status_code == 400
    assert over.json()["detail"] == "Kullanılabilir limit yetersiz."
    full = await send(client, headers, credit["id"], CHECKING, LIMIT, "credit-full-01")
    assert full.status_code == 201, full.text
    assert await balance(credit["id"]) == -LIMIT


async def test_repayment_capped_at_debt(client, bank):
    headers, credit = bank
    no_debt = await send(client, headers, 1, credit["iban"], 1, "credit-repay-02")
    assert no_debt.status_code == 400
    await send(client, headers, credit["id"], CHECKING, 1000, "credit-draw-02")
    over = await send(client, headers, 1, credit["iban"], 1001, "credit-repay-03")
    assert over.status_code == 400
    exact = await send(client, headers, 1, credit["iban"], 1000, "credit-repay-04")
    assert exact.status_code == 201
    assert await balance(credit["id"]) == 0


async def test_credit_cannot_pay_other_customers(client, bank):
    headers, credit = bank
    response = await send(client, headers, credit["id"], OTHER, 1000, "credit-other-01")
    assert response.status_code == 400
    assert await balance(credit["id"]) == 0


async def test_others_cannot_pay_into_credit_account(client, bank):
    _, credit = bank
    token = (await login(client, "987654321", "123456")).json()["access_token"]
    other = {"Authorization": f"Bearer {token}"}
    # Give the owner a debt first, so the only reason to refuse is who is paying.
    await send(client, bank[0], credit["id"], CHECKING, 1000, "credit-draw-03")
    lookup = await client.get("/recipients/lookup", headers=other, params={"iban": credit["iban"]})
    assert lookup.status_code == 404
    response = await send(client, other, 3, credit["iban"], 500, "credit-foreign-01")
    assert response.status_code == 404
    assert await balance(credit["id"]) == -1000
    assert await balance(3) == 100_000


async def test_concurrent_draws_cannot_exceed_limit(client, bank):
    headers, credit = bank
    responses = await asyncio.gather(*(
        send(client, headers, credit["id"], CHECKING, 1_500_000, f"draw-race-{i}")
        for i in range(2)
    ))
    assert sorted(r.status_code for r in responses) == [201, 400]
    assert await balance(credit["id"]) == -1_500_000
    assert await balance(1) == 1_600_000


async def test_concurrent_repayments_cannot_overpay(client, bank):
    headers, credit = bank
    assert (await send(
        client, headers, credit["id"], CHECKING, 1000, "repay-race-draw"
    )).status_code == 201
    responses = await asyncio.gather(*(
        send(client, headers, 1, credit["iban"], 750, f"repay-race-{i}")
        for i in range(2)
    ))
    assert sorted(r.status_code for r in responses) == [201, 400]
    assert await balance(credit["id"]) == -250
    assert await balance(1) == 100_250


async def test_concurrent_credit_opening(client, create_customer):
    await create_customer()
    token = (await login(client, "123456789", "123456")).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    responses = await asyncio.gather(*(
        client.post("/accounts", headers=headers, json={"kind": "credit", "name": "Credit"})
        for _ in range(2)
    ))
    assert sorted(r.status_code for r in responses) == [201, 409]
    accounts = (await client.get("/accounts", headers=headers)).json()
    assert len(accounts) == 1


async def test_draw_replay_when_limit_exhausted(client, bank):
    headers, credit = bank
    first = await send(client, headers, credit["id"], CHECKING, LIMIT, "draw-replay-full")
    replay = await send(client, headers, credit["id"], CHECKING, LIMIT, "draw-replay-full")
    assert first.status_code == replay.status_code == 201
    assert first.json() == replay.json()
    assert await balance(credit["id"]) == -LIMIT
    assert await balance(1) == LIMIT + 100_000
    changed = await send(client, headers, credit["id"], CHECKING, 1, "draw-replay-full")
    assert changed.status_code == 409


async def test_repay_replay_after_debt_cleared(client, bank):
    headers, credit = bank
    assert (await send(
        client, headers, credit["id"], CHECKING, 1000, "repay-replay-draw"
    )).status_code == 201
    first = await send(client, headers, 1, credit["iban"], 1000, "repay-replay-full")
    replay = await send(client, headers, 1, credit["iban"], 1000, "repay-replay-full")
    assert first.status_code == replay.status_code == 201
    assert first.json() == replay.json()
    assert await balance(credit["id"]) == 0
    assert await balance(1) == 100_000


async def test_credit_cycles_exempt_but_external_spending_still_limited(client, bank, monkeypatch):
    from app.config import get_settings

    headers, credit = bank
    settings = get_settings()
    monkeypatch.setattr(settings, "transfer_max_kurus", 1000)
    monkeypatch.setattr(settings, "transfer_daily_max_kurus", 1000)
    for i in range(2):
        assert (await send(
            client, headers, credit["id"], CHECKING, 2000, f"cycle-draw-{i}"
        )).status_code == 201
        assert (await send(
            client, headers, 1, credit["iban"], 2000, f"cycle-repay-{i}"
        )).status_code == 201
    assert (await send(client, headers, 1, OTHER, 1000, "cycle-external")).status_code == 201
    assert (await send(
        client, headers, credit["id"], CHECKING, 2000, "cycle-final-draw"
    )).status_code == 201
    assert (await send(client, headers, 1, OTHER, 1, "cycle-over-daily")).status_code == 400
