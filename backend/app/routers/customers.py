from fastapi import APIRouter
from sqlalchemy import select

from app.deps import CurrentCustomer, SessionDep
from app.models import Account
from app.schemas import AccountOut, CustomerOut

router = APIRouter(tags=["customers"])


@router.get("/me")
async def read_me(customer: CurrentCustomer) -> CustomerOut:
    return CustomerOut.model_validate(customer)


@router.get("/accounts")
async def list_accounts(customer: CurrentCustomer, session: SessionDep) -> list[AccountOut]:
    rows = await session.scalars(
        select(Account).where(Account.customer_id == customer.id).order_by(Account.id)
    )
    return [AccountOut.model_validate(a) for a in rows]
