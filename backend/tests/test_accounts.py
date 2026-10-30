import pytest
from sqlalchemy import select

from app.banking import is_valid_tr_iban, make_tr_iban
from app.db import SessionLocal
from app.models import Account, Transaction
from tests.conftest import login


@pytest.fixture
async def owner(client, create_customer):
    customer = await create_customer(
        accounts=[{"name": "İlk hesap", "iban": make_tr_iban("0000000000000001")}]
    )
    response = await login(client, customer.customer_no, "123456")
    return customer, {"Authorization": f"Bearer {response.json()['access_token']}"}


@pytest.mark.parametrize("kind", ["checking", "savings"])
async def test_open_account(client, owner, kind):
    _, headers = owner
    response = await client.post("/accounts", headers=headers, json={"kind": kind, "name": "Yeni"})
    assert response.status_code == 201
    data = response.json()
    assert data["kind"] == kind
    assert data["balance_kurus"] == 0
    assert is_valid_tr_iban(data["iban"])


async def test_checking_goal(client, owner):
    _, headers = owner
    response = await client.post(
        "/accounts", headers=headers, json={"kind": "checking", "name": "Yeni", "goal_kurus": 100}
    )
    assert response.status_code == 422
    assert response.json()["detail"] == (
        "Birikim hedefi yalnızca birikim hesaplarında belirlenebilir."
    )


async def test_account_limit(client, owner):
    _, headers = owner
    for _ in range(9):
        assert (
            await client.post(
                "/accounts", headers=headers, json={"kind": "checking", "name": "Yeni"}
            )
        ).status_code == 201
    assert (
        await client.post("/accounts", headers=headers, json={"kind": "checking", "name": "Fazla"})
    ).status_code == 409
    assert len((await client.get("/accounts", headers=headers)).json()) == 10


async def test_pagination(client, owner):
    customer, headers = owner
    async with SessionLocal() as session:
        account_id = await session.scalar(
            select(Account.id).where(Account.customer_id == customer.id)
        )
        session.add_all(
            [
                Transaction(account_id=account_id, amount_kurus=i + 1, description=f"Hareket {i}")
                for i in range(25)
            ]
        )
        await session.commit()
        expected = list(
            await session.scalars(select(Transaction.id).order_by(Transaction.id.desc()))
        )
    ids = []
    before = None
    for size in [10, 10, 5]:
        params = {"limit": 10}
        if before is not None:
            params["before_id"] = before
        response = await client.get(
            f"/accounts/{account_id}/transactions", headers=headers, params=params
        )
        assert response.status_code == 200
        page = response.json()
        assert len(page["items"]) == size
        ids.extend(row["id"] for row in page["items"])
        before = page["next_before_id"]
        assert before == (page["items"][-1]["id"] if size == 10 else None)
    assert ids == expected


async def test_foreign_transactions(client, owner, create_customer):
    _, headers = owner
    other = await create_customer(
        customer_no="987654321",
        accounts=[{"name": "Başka", "iban": make_tr_iban("0000000000000002")}],
    )
    async with SessionLocal() as session:
        account_id = await session.scalar(select(Account.id).where(Account.customer_id == other.id))
    assert (
        await client.get(f"/accounts/{account_id}/transactions", headers=headers)
    ).status_code == 404
