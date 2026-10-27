import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.db import SessionLocal
from app.models import Account, Transaction
from tests.conftest import login


async def test_accounts_are_owned_ordered_and_integer_kurus(client, create_customer):
    owner = await create_customer(
        accounts=[
            {"id": 30, "name": "Savings", "iban": "TR001", "balance_kurus": 12345,
             "goal_kurus": 100001},
            {"id": 10, "name": "Current", "iban": "TR002", "balance_kurus": 0},
        ]
    )
    other = await create_customer(
        customer_no="987654321",
        accounts=[{"id": 20, "name": "Other", "iban": "TR003", "balance_kurus": 999}],
    )
    for customer, expected_ids in ((owner, [10, 30]), (other, [20])):
        response = await login(client, customer.customer_no, "123456")
        assert response.status_code == 200
        headers = {"Authorization": f"Bearer {response.json()['access_token']}"}
        response = await client.get("/accounts", headers=headers)
        assert response.status_code == 200
        accounts = response.json()
        assert [account["id"] for account in accounts] == expected_ids
        for account in accounts:
            assert isinstance(account["balance_kurus"], int)
            assert not isinstance(account["balance_kurus"], float)
            if account["goal_kurus"] is not None:
                assert isinstance(account["goal_kurus"], int)
                assert not isinstance(account["goal_kurus"], float)
        if customer.id == owner.id:
            assert [account["balance_kurus"] for account in accounts] == [0, 12345]
            assert accounts[1]["goal_kurus"] == 100001


async def test_customer_without_accounts(client, create_customer):
    customer = await create_customer()
    response = await login(client, customer.customer_no, "123456")
    assert response.status_code == 200
    response = await client.get(
        "/accounts", headers={"Authorization": f"Bearer {response.json()['access_token']}"}
    )
    assert response.status_code == 200
    assert response.json() == []


async def test_negative_account_balance_rejected(create_customer):
    customer = await create_customer()
    async with SessionLocal() as session:
        session.add(Account(
            customer_id=customer.id, name="Invalid", iban="TR004", balance_kurus=-1
        ))
        with pytest.raises(IntegrityError) as error:
            await session.commit()
        await session.rollback()
        assert "ck_accounts_balance_non_negative" in str(error.value)


async def test_zero_transaction_amount_rejected(create_customer):
    customer = await create_customer(
        accounts=[{"name": "Current", "iban": "TR005", "balance_kurus": 100}]
    )
    async with SessionLocal() as session:
        account_id = await session.scalar(
            select(Account.id).where(Account.customer_id == customer.id)
        )
        session.add(Transaction(account_id=account_id, amount_kurus=0, description="Invalid"))
        with pytest.raises(IntegrityError) as error:
            await session.commit()
        await session.rollback()
        assert "ck_transactions_amount_non_zero" in str(error.value)
