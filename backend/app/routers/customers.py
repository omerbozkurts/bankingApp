from fastapi import APIRouter

from app.deps import CurrentCustomer
from app.schemas import CustomerOut

router = APIRouter(tags=["customers"])


@router.get("/me")
async def read_me(customer: CurrentCustomer) -> CustomerOut:
    return CustomerOut.model_validate(customer)
