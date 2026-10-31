from datetime import date
from typing import Annotated

from fastapi import APIRouter, HTTPException, Path, Query, Response, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from app.banking import random_iban
from app.config import get_settings
from app.deps import CurrentCustomer, SessionDep
from app.models import Account, Customer, Transaction
from app.schemas import AccountOut, OpenAccountRequest, TransactionOut, TransactionPage
from app.statement import MAX_STATEMENT_DAYS, MAX_STATEMENT_ROWS, day_bounds, statement_csv

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
    credit_limit = None
    if body.kind == "credit":
        has_credit = await session.scalar(
            select(Account.id).where(Account.customer_id == customer.id, Account.kind == "credit")
        )
        if has_credit is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail="Zaten bir kredili hesabınız var."
            )
        credit_limit = get_settings().credit_limit_kurus
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
            credit_limit_kurus=credit_limit,
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
    from_date: Annotated[date | None, Query()] = None,
    to_date: Annotated[date | None, Query()] = None,
) -> TransactionPage:
    """`from_date` / `to_date` (inclusive, Turkish days) narrow the list; paging works as usual."""
    _check_range(from_date, to_date)
    await get_owned_account(session, customer.id, account_id)
    return await transaction_page(session, account_id, limit, before_id, from_date, to_date)


def _check_range(from_date: date | None, to_date: date | None) -> None:
    # Far-off dates are typos; date.max would also overflow the end-of-day bound.
    if any(d is not None and not 2000 <= d.year <= 2100 for d in (from_date, to_date)):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Tarih geçersiz."
        )
    if from_date and to_date and from_date > to_date:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Başlangıç tarihi bitiş tarihinden sonra olamaz.",
        )


def _in_range(query, from_date: date | None, to_date: date | None):
    start, end = day_bounds(from_date, to_date)
    if start is not None:
        query = query.where(Transaction.created_at >= start)
    if end is not None:
        query = query.where(Transaction.created_at < end)
    return query


async def transaction_page(
    session: SessionDep,
    account_id: int,
    limit: int,
    before_id: int | None,
    from_date: date | None = None,
    to_date: date | None = None,
) -> TransactionPage:
    """Newest first; `before_id` continues from the previous page. Access is checked by callers."""
    query = _in_range(
        select(Transaction).where(Transaction.account_id == account_id), from_date, to_date
    )
    if before_id is not None:
        query = query.where(Transaction.id < before_id)
    rows = list(await session.scalars(query.order_by(Transaction.id.desc()).limit(limit + 1)))
    items = rows[:limit]
    return TransactionPage(
        items=[TransactionOut.model_validate(t) for t in items],
        next_before_id=items[-1].id if len(rows) > limit else None,
    )


@router.get(
    "/{account_id}/statement",
    response_class=Response,
    responses={
        200: {
            "content": {"text/csv": {}},
            "description": "Ekstre (CSV, noktalı virgülle ayrılmış)",
        },
        422: {"description": "Tarih aralığı geçersiz, çok uzun veya çok fazla hareket içeriyor"},
    },
)
async def download_statement(
    account_id: Annotated[int, Path(ge=1, le=2**31 - 1)],
    customer: CurrentCustomer,
    session: SessionDep,
    from_date: Annotated[date, Query()],
    to_date: Annotated[date, Query()],
) -> Response:
    """Movements in the range (inclusive, Turkish days), oldest first, as a CSV file."""
    _check_range(from_date, to_date)
    if (to_date - from_date).days + 1 > MAX_STATEMENT_DAYS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"Ekstre en fazla {MAX_STATEMENT_DAYS} günü kapsayabilir.",
        )
    account = await get_owned_account(session, customer.id, account_id)
    query = _in_range(
        select(Transaction).where(Transaction.account_id == account_id), from_date, to_date
    )
    count = await session.scalar(select(func.count()).select_from(query.subquery()))
    if (count or 0) > MAX_STATEMENT_ROWS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Bu aralıkta çok fazla hareket var. Lütfen aralığı daraltın.",
        )
    rows = await session.scalars(query.order_by(Transaction.id))
    filename = f"ABBank-ekstre-{account.iban[-4:]}-{from_date:%Y%m%d}-{to_date:%Y%m%d}.csv"
    return Response(
        content=statement_csv(rows),
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            # Statements are private: no shared or browser cache keeps a copy.
            "Cache-Control": "no-store",
        },
    )
