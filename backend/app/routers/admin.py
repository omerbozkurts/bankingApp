"""Admin panel: look up customers, freeze accounts, clear login locks. Every change is audited.

Admins are customers with `is_admin` set (scripts/make_admin.py). They can read any customer's
accounts and history but cannot move money or change a balance: a correction would be a
separate, reviewed booking, not an edit.
"""

from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, HTTPException, Path, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import aliased

from app.deps import CurrentAdmin, SessionDep
from app.models import Account, AdminAction, Customer
from app.routers.accounts import transaction_page
from app.schemas import (
    AccountOut,
    AdminActionOut,
    AdminActionPage,
    AdminActionRequest,
    AdminCustomerDetail,
    AdminCustomerOut,
    AdminCustomerPage,
    TransactionPage,
)

router = APIRouter(prefix="/admin", tags=["admin"])

DbId = Annotated[int, Path(ge=1, le=2**31 - 1)]
BeforeId = Annotated[int | None, Query(ge=1, le=2**31 - 1)]
Limit = Annotated[int, Query(ge=1, le=100)]


def _not_found(what: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"{what} bulunamadı.")


def _not_on_self(admin: Customer, customer_id: int) -> None:
    # Another admin has to act on an admin's own record.
    if customer_id == admin.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Kendi hesaplarınızda yönetici işlemi yapamazsınız.",
        )


def _customer_out(customer: Customer, account_count: int) -> AdminCustomerOut:
    locked_until = customer.locked_until
    return AdminCustomerOut(
        id=customer.id,
        customer_no=customer.customer_no,
        full_name=customer.full_name,
        is_admin=customer.is_admin,
        locked=locked_until is not None and locked_until > datetime.now(UTC),
        account_count=account_count,
        created_at=customer.created_at,
    )


def _escape_like(term: str) -> str:
    # So "%" or "_" in a search matches itself instead of everyone.
    return term.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


@router.get("/customers")
async def list_customers(
    admin: CurrentAdmin,
    session: SessionDep,
    q: Annotated[str, Query(max_length=120)] = "",
    limit: Limit = 20,
    before_id: BeforeId = None,
) -> AdminCustomerPage:
    """Newest customers first. `q` matches the start of a customer number or part of a name."""
    account_count = (
        select(func.count(Account.id)).where(Account.customer_id == Customer.id).scalar_subquery()
    )
    query = select(Customer, account_count)
    term = _escape_like(" ".join(q.split()))
    if term:
        query = query.where(
            or_(
                Customer.customer_no.like(f"{term}%", escape="\\"),
                Customer.full_name.ilike(f"%{term}%", escape="\\"),
            )
        )
    if before_id is not None:
        query = query.where(Customer.id < before_id)
    rows = (await session.execute(query.order_by(Customer.id.desc()).limit(limit + 1))).all()
    items = [_customer_out(c, n) for c, n in rows[:limit]]
    return AdminCustomerPage(
        items=items, next_before_id=items[-1].id if len(rows) > limit else None
    )


@router.get("/customers/{customer_id}")
async def read_customer(
    customer_id: DbId, admin: CurrentAdmin, session: SessionDep
) -> AdminCustomerDetail:
    customer = await session.get(Customer, customer_id)
    if customer is None:
        raise _not_found("Müşteri")
    accounts = list(
        await session.scalars(
            select(Account).where(Account.customer_id == customer.id).order_by(Account.id)
        )
    )
    return AdminCustomerDetail(
        **_customer_out(customer, len(accounts)).model_dump(),
        accounts=[AccountOut.model_validate(a) for a in accounts],
    )


@router.get("/accounts/{account_id}/transactions")
async def list_account_transactions(
    account_id: DbId,
    admin: CurrentAdmin,
    session: SessionDep,
    limit: Limit = 20,
    before_id: BeforeId = None,
) -> TransactionPage:
    if await session.get(Account, account_id) is None:
        raise _not_found("Hesap")
    return await transaction_page(session, account_id, limit, before_id)


async def _lock_customers(session: SessionDep, *customer_ids: int) -> None:
    """Locks customer rows in id order, before any account row.

    A transfer locks its sender's customer row and then the account rows, and the audit row's
    foreign keys need the admin's and the owner's customer rows. Taking those first, in the same
    order everywhere, means a freeze and a transfer queue up instead of deadlocking.
    """
    await session.execute(
        select(Customer.id)
        .where(Customer.id.in_(customer_ids))
        .order_by(Customer.id)
        .with_for_update()
    )


async def _set_frozen(
    session: SessionDep, admin: Customer, account_id: int, reason: str, frozen: bool
) -> AccountOut:
    owner_id = await session.scalar(select(Account.customer_id).where(Account.id == account_id))
    if owner_id is None:
        raise _not_found("Hesap")
    _not_on_self(admin, owner_id)
    await _lock_customers(session, admin.id, owner_id)
    # The row lock a transfer takes: a transfer either finishes first or sees the freeze. An
    # account never changes owner, so the owner read above is still the one locked.
    account = await session.scalar(
        select(Account)
        .where(Account.id == account_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    assert account is not None
    if account.frozen == frozen:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Hesap zaten dondurulmuş." if frozen else "Hesap dondurulmuş değil.",
        )
    account.frozen_at = datetime.now(UTC) if frozen else None
    session.add(
        AdminAction(
            admin_id=admin.id,
            action="freeze_account" if frozen else "unfreeze_account",
            customer_id=account.customer_id,
            account_id=account.id,
            reason=reason,
        )
    )
    await session.commit()
    return AccountOut.model_validate(account)


@router.post("/accounts/{account_id}/freeze")
async def freeze_account(
    account_id: DbId, body: AdminActionRequest, admin: CurrentAdmin, session: SessionDep
) -> AccountOut:
    """Stops money leaving the account (transfers, credit draws). Incoming money still arrives."""
    return await _set_frozen(session, admin, account_id, body.reason, frozen=True)


@router.post("/accounts/{account_id}/unfreeze")
async def unfreeze_account(
    account_id: DbId, body: AdminActionRequest, admin: CurrentAdmin, session: SessionDep
) -> AccountOut:
    return await _set_frozen(session, admin, account_id, body.reason, frozen=False)


@router.post("/customers/{customer_id}/unlock")
async def unlock_customer(
    customer_id: DbId, body: AdminActionRequest, admin: CurrentAdmin, session: SessionDep
) -> AdminCustomerOut:
    """Clears the temporary lock after repeated wrong passwords."""
    _not_on_self(admin, customer_id)
    # Locked like a login attempt, so a concurrent wrong password can't interleave.
    await _lock_customers(session, admin.id, customer_id)
    customer = await session.scalar(
        select(Customer).where(Customer.id == customer_id).execution_options(populate_existing=True)
    )
    if customer is None:
        raise _not_found("Müşteri")
    if not _customer_out(customer, 0).locked:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Müşterinin girişi kilitli değil."
        )
    customer.locked_until = None
    customer.failed_login_count = 0
    session.add(
        AdminAction(
            admin_id=admin.id, action="unlock_customer", customer_id=customer.id, reason=body.reason
        )
    )
    await session.commit()
    account_count = await session.scalar(
        select(func.count(Account.id)).where(Account.customer_id == customer.id)
    )
    return _customer_out(customer, account_count or 0)


@router.get("/actions")
async def list_actions(
    admin: CurrentAdmin, session: SessionDep, limit: Limit = 20, before_id: BeforeId = None
) -> AdminActionPage:
    """The audit log, newest first."""
    actor, target = aliased(Customer), aliased(Customer)
    query = (
        select(AdminAction, actor.customer_no, target.customer_no)
        .outerjoin(actor, actor.id == AdminAction.admin_id)
        .join(target, target.id == AdminAction.customer_id)
    )
    if before_id is not None:
        query = query.where(AdminAction.id < before_id)
    rows = (await session.execute(query.order_by(AdminAction.id.desc()).limit(limit + 1))).all()
    items = [
        AdminActionOut(
            id=action.id,
            action=action.action,  # type: ignore[arg-type]
            admin_customer_no=admin_no,
            customer_no=customer_no,
            account_id=action.account_id,
            reason=action.reason,
            created_at=action.created_at,
        )
        for action, admin_no, customer_no in rows[:limit]
    ]
    return AdminActionPage(items=items, next_before_id=items[-1].id if len(rows) > limit else None)
