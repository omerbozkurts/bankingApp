"""Create the demo customer (123456789 / 123456). Safe to run more than once.

    uv run python -m scripts.seed_demo
"""

import asyncio

from sqlalchemy import select

from app.db import SessionLocal, engine
from app.models import Account, Customer, Transaction
from app.security import hash_password

DEMO_CUSTOMER_NO = "123456789"
DEMO_PASSWORD = "123456"


async def seed() -> None:
    async with SessionLocal() as session:
        exists = await session.scalar(
            select(Customer.id).where(Customer.customer_no == DEMO_CUSTOMER_NO)
        )
        if exists:
            print("Demo müşteri zaten var, değişiklik yapılmadı.")
            return

        customer = Customer(
            customer_no=DEMO_CUSTOMER_NO,
            full_name="Deniz Yılmaz",
            password_hash=hash_password(DEMO_PASSWORD),
        )
        checking = Account(
            name="Vadesiz TL Hesabı",
            iban="TR00 0000 0000 0000 0000 0000 01",
            balance_kurus=1_245_075,
        )
        savings = Account(
            name="Birikim Hesabı",
            iban="TR00 0000 0000 0000 0000 0000 02",
            balance_kurus=3_820_000,
            goal_kurus=5_000_000,
        )
        customer.accounts = [checking, savings]
        session.add(customer)
        await session.flush()

        session.add_all(
            [
                Transaction(account_id=checking.id, amount_kurus=2_500_000, description="Maaş"),
                Transaction(account_id=checking.id, amount_kurus=-1_254_925, description="Kira"),
                Transaction(account_id=savings.id, amount_kurus=3_820_000, description="Birikim"),
            ]
        )
        await session.commit()
        print(f"Demo müşteri oluşturuldu: {DEMO_CUSTOMER_NO} / {DEMO_PASSWORD}")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(seed())
