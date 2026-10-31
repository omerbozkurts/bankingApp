"""Grant or revoke admin rights. Deliberately not an API endpoint: it needs server access.

    uv run python -m scripts.make_admin 123456789 --reason "Operasyon ekibine katıldı"
    uv run python -m scripts.make_admin 123456789 --revoke --reason "Ekipten ayrıldı"

The change is written to the audit log with no admin as its author.
"""

import argparse
import asyncio

from sqlalchemy import select

from app.db import SessionLocal, engine
from app.models import AdminAction, Customer
from app.schemas import AdminActionRequest


async def set_admin(customer_no: str, is_admin: bool, reason: str) -> str:
    """Returns the message to print. Changes nothing when the flag already has that value."""
    async with SessionLocal() as session:
        customer = await session.scalar(
            select(Customer).where(Customer.customer_no == customer_no).with_for_update()
        )
        if customer is None:
            return f"{customer_no} numaralı müşteri yok."
        if customer.is_admin == is_admin:
            return f"{customer_no} zaten {'yönetici' if is_admin else 'yönetici değil'}."
        customer.is_admin = is_admin
        session.add(
            AdminAction(
                admin_id=None,
                action="grant_admin" if is_admin else "revoke_admin",
                customer_id=customer.id,
                reason=reason,
            )
        )
        await session.commit()
    return f"{customer_no}: yönetici yetkisi {'verildi' if is_admin else 'kaldırıldı'}."


async def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("customer_no")
    parser.add_argument("--revoke", action="store_true", help="yönetici yetkisini kaldır")
    parser.add_argument("--reason", required=True, help="işlem kaydına yazılacak gerekçe")
    args = parser.parse_args()
    try:
        reason = AdminActionRequest(reason=args.reason).reason
    except ValueError:
        parser.error("gerekçe 3-200 karakter olmalı")
    try:
        message = await set_admin(args.customer_no, not args.revoke, reason)
    finally:
        await engine.dispose()
    print(message)
    return 1 if message.endswith("müşteri yok.") else 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
