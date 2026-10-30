from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import func, select

from app.banking import mask_name, normalize_iban
from app.config import get_settings
from app.deps import CurrentCustomer, SessionDep
from app.models import Account, Customer, Transaction, Transfer
from app.rate_limit import SlidingWindowLimiter
from app.routers.accounts import get_owned_account
from app.schemas import Iban, RecipientOut, TransferOut, TransferRequest

router = APIRouter(tags=["transfers"])

_settings = get_settings()
lookup_limiter = SlidingWindowLimiter(
    _settings.lookup_rate_limit, _settings.lookup_rate_window_seconds
)

UNKNOWN_IBAN = (
    "Bu IBAN AB Bank'ta kayıtlı değil. Şimdilik yalnızca AB Bank hesaplarına gönderim yapılabilir."
)


async def _recipient_account(session: SessionDep, iban: str) -> Account:
    account = await session.scalar(select(Account).where(Account.iban == normalize_iban(iban)))
    if account is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=UNKNOWN_IBAN)
    return account


@router.get("/recipients/lookup")
async def lookup_recipient(
    iban: Annotated[Iban, Query()], customer: CurrentCustomer, session: SessionDep
) -> RecipientOut:
    """Masked owner name, so the sender can confirm the recipient before sending."""
    if not lookup_limiter.allow(str(customer.id)):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Çok fazla alıcı sorgusu yaptınız. Lütfen birkaç dakika sonra tekrar deneyin.",
        )
    account = await _recipient_account(session, iban)
    # Someone else's credit account can't receive transfers, so don't reveal its owner either.
    if account.kind == "credit" and account.customer_id != customer.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=UNKNOWN_IBAN)
    owner = await session.get(Customer, account.customer_id)
    assert owner is not None
    return RecipientOut(iban=account.iban, masked_name=mask_name(owner.full_name))


def _description(body: TransferRequest, own: bool) -> str:
    return body.description or ("Hesaplar arası transfer" if own else "Para transferi")


async def _transfer_out(session: SessionDep, transfer: Transfer) -> TransferOut:
    to_account = await session.get(Account, transfer.to_account_id)
    debit = await session.scalar(
        select(Transaction).where(
            Transaction.transfer_id == transfer.id,
            Transaction.account_id == transfer.from_account_id,
        )
    )
    assert to_account is not None and debit is not None
    return TransferOut(
        id=transfer.id,
        from_account_id=transfer.from_account_id,
        to_iban=to_account.iban,
        recipient=debit.counterparty or "",
        amount_kurus=transfer.amount_kurus,
        description=transfer.description,
        from_balance_after_kurus=debit.balance_after_kurus or 0,
        created_at=transfer.created_at,
    )


@router.post(
    "/transfers",
    status_code=status.HTTP_201_CREATED,
    responses={
        400: {"description": "Yetersiz bakiye, limit aşımı veya aynı hesaba gönderim"},
        404: {"description": "Gönderen hesap veya alıcı IBAN bulunamadı"},
        409: {"description": "İşlem anahtarı farklı bir istekle tekrar kullanıldı"},
    },
)
async def create_transfer(
    body: TransferRequest, customer: CurrentCustomer, session: SessionDep
) -> TransferOut:
    settings = get_settings()

    # Serialise this customer's transfers: the daily-limit sum and the idempotency check below
    # must not race with a concurrent transfer by the same customer.
    await session.scalar(select(Customer).where(Customer.id == customer.id).with_for_update())

    previous = await session.scalar(
        select(Transfer).where(
            Transfer.customer_id == customer.id,
            Transfer.idempotency_key == body.idempotency_key,
        )
    )
    if previous is not None:
        to_account = await session.get(Account, previous.to_account_id)
        own = to_account is not None and to_account.customer_id == customer.id
        # For own accounts a blank description matches either default: own transfers made before
        # own-account support stored "Para transferi", and a retry of one must still replay.
        descriptions = {_description(body, o) for o in ((True, False) if own else (False,))}
        same_request = (
            to_account is not None
            and previous.from_account_id == body.from_account_id
            and previous.amount_kurus == body.amount_kurus
            and previous.description in descriptions
            and to_account.iban == body.to_iban
        )
        if not same_request:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Bu işlem anahtarı farklı bir işlem için kullanıldı.",
            )
        return await _transfer_out(session, previous)

    from_account = await get_owned_account(session, customer.id, body.from_account_id)
    to_account = await _recipient_account(session, body.to_iban)
    # Matches the lookup: someone else's credit account doesn't exist as far as senders know.
    if to_account.kind == "credit" and to_account.customer_id != customer.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=UNKNOWN_IBAN)
    if to_account.id == from_account.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Aynı hesaba para gönderilemez."
        )
    # Moving money between the customer's own accounts never leaves them, so the transfer
    # limits (there to cap losses from a stolen session) don't apply and it doesn't count.
    own = to_account.customer_id == customer.id

    if not own and body.amount_kurus > settings.transfer_max_kurus:
        max_tl = f"{settings.transfer_max_kurus // 100:,}".replace(",", ".")  # 50.000
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Tek seferde en fazla {max_tl} TL gönderebilirsiniz.",
        )

    if not own:
        since = datetime.now(UTC) - timedelta(hours=24)
        sent_today = await session.scalar(
            select(func.coalesce(func.sum(Transfer.amount_kurus), 0))
            .join(Account, Account.id == Transfer.to_account_id)
            .where(
                Transfer.customer_id == customer.id,
                Transfer.created_at >= since,
                Account.customer_id != customer.id,
            )
        )
        if sent_today + body.amount_kurus > settings.transfer_daily_max_kurus:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "Günlük transfer limitinizi aşıyorsunuz. Lütfen daha düşük bir tutar deneyin."
                ),
            )

    # Lock both accounts in id order so two opposite transfers can't deadlock each other.
    locked = {
        a.id: a
        for a in await session.scalars(
            select(Account)
            .where(Account.id.in_([from_account.id, to_account.id]))
            .order_by(Account.id)
            .with_for_update()
            # The rows are already in the session from the unlocked reads above; without this,
            # SQLAlchemy keeps their stale balances and a concurrent credit would be overwritten.
            .execution_options(populate_existing=True)
        )
    }
    source, target = locked[from_account.id], locked[to_account.id]
    # Credit accounts only move money between the owner's accounts: draw to, repay from.
    if not own and "credit" in (source.kind, target.kind):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Kredili hesap yalnızca kendi hesaplarınız arasında kullanılabilir.",
        )
    if source.available_kurus < body.amount_kurus:
        detail = "Kullanılabilir limit yetersiz." if source.kind == "credit" else "Yetersiz bakiye."
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)
    if target.kind == "credit" and body.amount_kurus > -target.balance_kurus:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ödeme tutarı kredi borcunuzdan fazla olamaz.",
        )

    recipient = await session.get(Customer, target.customer_id)
    assert recipient is not None
    description = _description(body, own)
    # Each side shows where the money went or came from: the other account's name for the
    # customer's own accounts, otherwise the other customer's masked name.
    debit_party = target.name if own else mask_name(recipient.full_name)
    credit_party = source.name if own else mask_name(customer.full_name)

    source.balance_kurus -= body.amount_kurus
    target.balance_kurus += body.amount_kurus
    transfer = Transfer(
        customer_id=customer.id,
        from_account_id=source.id,
        to_account_id=target.id,
        amount_kurus=body.amount_kurus,
        description=description,
        idempotency_key=body.idempotency_key,
    )
    session.add(transfer)
    await session.flush()
    session.add_all(
        [
            Transaction(
                account_id=source.id,
                transfer_id=transfer.id,
                amount_kurus=-body.amount_kurus,
                balance_after_kurus=source.balance_kurus,
                description=description,
                counterparty=debit_party,
            ),
            Transaction(
                account_id=target.id,
                transfer_id=transfer.id,
                amount_kurus=body.amount_kurus,
                balance_after_kurus=target.balance_kurus,
                description=description,
                counterparty=credit_party,
            ),
        ]
    )
    await session.commit()
    await session.refresh(transfer)
    return await _transfer_out(session, transfer)
