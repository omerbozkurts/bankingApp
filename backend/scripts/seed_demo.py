"""Create the demo customers. Safe to run more than once.

    uv run python -m scripts.seed_demo

- 123456789 / 123456  Deniz Yılmaz: checking + savings account
- 987654321 / 654321  Ali Kaya: checking account, a recipient for trying transfers
"""

import asyncio

from sqlalchemy import select

from app.banking import format_iban, make_tr_iban
from app.db import SessionLocal, engine
from app.models import Account, Customer, Transaction
from app.security import hash_password

DEMO_CUSTOMERS = [
    {
        "customer_no": "123456789",
        "password": "123456",
        "full_name": "Deniz Yılmaz",
        "accounts": [
            {
                "kind": "checking",
                "name": "Vadesiz TL Hesabı",
                "number": "0000000000000001",
                # (description, amount) oldest first; the balance is their running total.
                "movements": [("Maaş", 2_500_000), ("Kira", -1_254_925)],
            },
            {
                "kind": "savings",
                "name": "Birikim Hesabı",
                "number": "0000000000000002",
                "goal_kurus": 5_000_000,
                "movements": [("Birikim", 3_820_000)],
            },
        ],
    },
    {
        "customer_no": "987654321",
        "password": "654321",
        "full_name": "Ali Kaya",
        "accounts": [
            {
                "kind": "checking",
                "name": "Vadesiz TL Hesabı",
                "number": "0000000000000003",
                "movements": [("Maaş", 1_800_000)],
            },
        ],
    },
]


async def seed() -> None:
    async with SessionLocal() as session:
        for spec in DEMO_CUSTOMERS:
            exists = await session.scalar(
                select(Customer.id).where(Customer.customer_no == spec["customer_no"])
            )
            if exists:
                print(f"{spec['customer_no']} zaten var, atlandı.")
                continue

            customer = Customer(
                customer_no=spec["customer_no"],
                full_name=spec["full_name"],
                password_hash=hash_password(spec["password"]),
            )
            session.add(customer)
            for a in spec["accounts"]:
                balance = 0
                movements = []
                for description, amount in a["movements"]:
                    balance += amount
                    movements.append(
                        Transaction(
                            amount_kurus=amount,
                            balance_after_kurus=balance,
                            description=description,
                        )
                    )
                account = Account(
                    kind=a["kind"],
                    name=a["name"],
                    iban=make_tr_iban(a["number"]),
                    balance_kurus=balance,
                    goal_kurus=a.get("goal_kurus"),
                )
                customer.accounts.append(account)
                await session.flush()
                for movement in movements:
                    movement.account_id = account.id
                session.add_all(movements)
                print(f"  {spec['full_name']}: {a['name']} {format_iban(account.iban)}")
            print(f"{spec['customer_no']} / {spec['password']} oluşturuldu.")
        await session.commit()

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(seed())
