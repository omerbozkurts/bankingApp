"""Saved recipients: IBANs or customer numbers a customer pays often, under a nickname."""

from typing import Annotated

from fastapi import APIRouter, HTTPException, Path, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from app.deps import CurrentCustomer, SessionDep
from app.models import Customer, SavedRecipient
from app.routers.transfers import describe_recipient
from app.schemas import SavedRecipientOut, SaveRecipientRequest

router = APIRouter(prefix="/recipients/saved", tags=["recipients"])

MAX_SAVED_RECIPIENTS = 50


@router.get("")
async def list_saved(customer: CurrentCustomer, session: SessionDep) -> list[SavedRecipientOut]:
    rows = await session.scalars(
        select(SavedRecipient)
        .where(SavedRecipient.customer_id == customer.id)
        .order_by(func.lower(SavedRecipient.nickname), SavedRecipient.id)
    )
    return [SavedRecipientOut.model_validate(r) for r in rows]


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    responses={
        404: {"description": "IBAN veya müşteri numarası para alabilecek bir hesaba ait değil"},
        409: {"description": "Alıcı zaten kayıtlı veya kayıt sınırı doldu"},
        429: {"description": "Alıcı sorgu kotası doldu"},
    },
)
async def save_recipient(
    body: SaveRecipientRequest, customer: CurrentCustomer, session: SessionDep
) -> SavedRecipientOut:
    """Checks the recipient like a lookup (same quota), then saves it with the masked name."""
    # Serialise this customer's saves so two parallel requests can't both pass the count check.
    await session.scalar(select(Customer).where(Customer.id == customer.id).with_for_update())
    count = await session.scalar(
        select(func.count(SavedRecipient.id)).where(SavedRecipient.customer_id == customer.id)
    )
    if (count or 0) >= MAX_SAVED_RECIPIENTS:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"En fazla {MAX_SAVED_RECIPIENTS} alıcı kaydedebilirsiniz.",
        )
    found = await describe_recipient(session, customer, body.iban, body.customer_no)
    saved = SavedRecipient(
        customer_id=customer.id,
        nickname=body.nickname,
        iban=found.iban if body.iban is not None else None,
        customer_no=body.customer_no,
        masked_name=found.masked_name,
    )
    try:
        async with session.begin_nested():
            session.add(saved)
    except IntegrityError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Bu alıcı zaten kayıtlı."
        ) from None
    await session.commit()
    return SavedRecipientOut.model_validate(saved)


@router.delete("/{recipient_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_saved(
    recipient_id: Annotated[int, Path(ge=1, le=2**31 - 1)],
    customer: CurrentCustomer,
    session: SessionDep,
) -> None:
    saved = await session.get(SavedRecipient, recipient_id)
    # Someone else's entry looks the same as a missing one.
    if saved is None or saved.customer_id != customer.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alıcı bulunamadı.")
    await session.delete(saved)
    await session.commit()
