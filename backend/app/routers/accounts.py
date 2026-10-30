from typing import Annotated

from fastapi import APIRouter, HTTPException, Path, Query, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.banking import random_iban
from app.deps import CurrentCustomer, SessionDep
from app.models import Account, Customer, Transaction
from app.schemas import AccountOut, OpenAccountRequest, TransactionOut, TransactionPage

router = APIRouter(prefix="/accounts", tags=["accounts"])

MAX_ACCOUNTS_PER_CUSTOMER = 10


async def get_owned_account(session: SessionDep, customer_id: int, account_id: int) -> Account:
    """404 for both missing and someone else's account, so ids can't be probed."""
    account = await session.get(Account, account_id)
    if account is None or account.customer_id != customer_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Hesap bulunamadı.")
    return account


@router.get("")
async def list_accounts(customer: CurrentCustomer, session: SessionDep) -> list[AccountOut]:
    rows = await session.scalars(
        select(Account).where(Account.customer_id == customer.id).order_by(Account.id)
    )
    return [AccountOut.model_validate(a) for a in rows]


@router.post("", status_code=status.HTTP_201_CREATED)
async def open_account(
    body: OpenAccountRequest, customer: CurrentCustomer, session: SessionDep
) -> AccountOut:
    # Lock the customer row so two parallel requests can't both see 9 accounts and both insert.
    await session.scalar(select(Customer).where(Customer.id == customer.id).with_for_update())
    existing = await session.scalars(select(Account.id).where(Account.customer_id == customer.id))
    if len(existing.all()) >= MAX_ACCOUNTS_PER_CUSTOMER:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"En fazla {MAX_ACCOUNTS_PER_CUSTOMER} hesap açabilirsiniz.",
        )
    # A random 16-digit account number collides with negligible probability; retry just in case.
    # Each attempt is a savepoint, so a collision keeps the customer lock and the count above valid.
    for _ in range(3):
        account = Account(
            customer_id=customer.id,
            kind=body.kind,
            name=body.name,
            iban=random_iban(),
            balance_kurus=0,
            goal_kurus=body.goal_kurus,
        )
        try:
            async with session.begin_nested():
                session.add(account)
        except IntegrityError:
            continue
        await session.commit()
        return AccountOut.model_validate(account)
    raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Tekrar deneyin.")


@router.get("/{account_id}/transactions")
async def list_transactions(
    account_id: Annotated[int, Path(ge=1, le=2**31 - 1)],
    customer: CurrentCustomer,
    session: SessionDep,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    before_id: Annotated[int | None, Query(ge=1, le=2**31 - 1)] = None,
) -> TransactionPage:
    await get_owned_account(session, customer.id, account_id)
    query = select(Transaction).where(Transaction.account_id == account_id)
    if before_id is not None:
        query = query.where(Transaction.id < before_id)
    rows = list(await session.scalars(query.order_by(Transaction.id.desc()).limit(limit + 1)))
    items = rows[:limit]
    return TransactionPage(
        items=[TransactionOut.model_validate(t) for t in items],
        next_before_id=items[-1].id if len(rows) > limit else None,
    )
