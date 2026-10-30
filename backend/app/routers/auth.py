import secrets
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.concurrency import run_in_threadpool
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.banking import national_id_digest, random_iban
from app.config import get_settings
from app.deps import SESSION_MODE_HEADER, SessionDep, require_csrf_header
from app.models import Account, Customer
from app.rate_limit import SlidingWindowLimiter
from app.schemas import LoginRequest, RegisterOut, RegisterRequest, Token
from app.security import create_access_token, hash_password, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])

# One message for every failed login (wrong password, unknown customer, locked account) so the
# response never reveals whether a customer number exists.
INVALID_CREDENTIALS = (
    "Müşteri numarası veya şifre hatalı. "
    "Art arda hatalı denemelerde hesabınız geçici olarak kilitlenir."
)

_settings = get_settings()
login_limiter = SlidingWindowLimiter(
    _settings.login_rate_limit, _settings.login_rate_window_seconds
)
register_limiter = SlidingWindowLimiter(
    _settings.register_rate_limit, _settings.register_rate_window_seconds
)

TOO_MANY_REQUESTS = "Çok fazla deneme yapıldı. Lütfen birkaç dakika sonra tekrar deneyin."


def _client_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"


@router.post(
    "/register",
    status_code=status.HTTP_201_CREATED,
    responses={
        409: {"description": "Bu kimlik numarasıyla zaten kayıt var"},
        429: {"description": "Bu IP adresinden çok fazla kayıt denemesi"},
    },
)
async def register(body: RegisterRequest, request: Request, session: SessionDep) -> RegisterOut:
    """Creates a customer with a checking account. Returns the new 9-digit customer number."""
    if not register_limiter.allow(_client_ip(request)):
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=TOO_MANY_REQUESTS)

    digest = national_id_digest(body.national_id, get_settings().national_id_pepper)
    if await session.scalar(select(Customer.id).where(Customer.national_id_digest == digest)):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Bu bilgilerle yeni kayıt oluşturulamadı. Zaten müşterimizseniz giriş yapın.",
        )

    password_hash = await run_in_threadpool(hash_password, body.password)
    # Random customer numbers and IBANs collide with negligible probability; retry just in case.
    for _ in range(5):
        customer = Customer(
            customer_no=str(secrets.randbelow(900_000_000) + 100_000_000),
            full_name=body.full_name,
            password_hash=password_hash,
            national_id_digest=digest,
            birth_date=body.birth_date,
            accounts=[Account(kind="checking", name="Vadesiz TL Hesabı", iban=random_iban())],
        )
        session.add(customer)
        try:
            await session.commit()
        except IntegrityError as error:
            await session.rollback()
            if "national_id_digest" in str(error.orig):
                # Same person registering twice at the same moment.
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Bu bilgilerle yeni kayıt oluşturulamadı.",
                ) from None
            continue
        return RegisterOut(customer_no=customer.customer_no, full_name=customer.full_name)
    raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Tekrar deneyin.")


@router.post(
    "/login",
    response_model_exclude_none=True,
    responses={
        401: {"description": "Giriş başarısız (hatalı bilgi veya geçici kilit)"},
        429: {"description": "Bu IP adresinden çok fazla deneme"},
    },
)
async def login(
    body: LoginRequest, request: Request, response: Response, session: SessionDep
) -> Token:
    settings = get_settings()
    if not login_limiter.allow(_client_ip(request)):
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=TOO_MANY_REQUESTS)

    now = datetime.now(UTC)
    customer = await session.scalar(
        select(Customer).where(Customer.customer_no == body.customer_no).with_for_update()
    )

    # Always run the (slow) hash check, even for unknown or locked customers, so response time
    # doesn't reveal which customer numbers exist. Off the event loop so other requests keep moving.
    password_ok = await run_in_threadpool(
        verify_password, body.password, customer.password_hash if customer else None
    )
    locked_until = customer.locked_until if customer else None
    locked = locked_until is not None and locked_until > now

    if customer is None or locked or not password_ok:
        if customer is not None and not locked:
            customer.failed_login_count += 1
            if customer.failed_login_count >= settings.max_failed_logins:
                customer.locked_until = now + timedelta(minutes=settings.lockout_minutes)
                customer.failed_login_count = 0
        await session.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=INVALID_CREDENTIALS,
            headers={"WWW-Authenticate": "Bearer"},
        )

    customer.failed_login_count = 0
    customer.locked_until = None
    await session.commit()

    token, expires_in = create_access_token(customer.id)
    if request.headers.get(SESSION_MODE_HEADER) != "cookie":
        # Mobile: token in the body only, kept in the device's secure storage.
        return Token(access_token=token, token_type="bearer", expires_in=expires_in)

    # Web: token in an httpOnly cookie only, never in the body that page JavaScript can read.
    response.set_cookie(
        settings.session_cookie_name,
        token,
        max_age=expires_in,
        httponly=True,
        secure=settings.session_cookie_secure,
        samesite="strict",
        path="/",
    )
    return Token(token_type="cookie", expires_in=expires_in)


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    # Without the header another site could not send this anyway (SameSite=Strict), but require it
    # so a cross-site form post can't force a sign-out either.
    dependencies=[Depends(require_csrf_header)],
)
async def logout(response: Response) -> None:
    """Clears the web session cookie. Mobile clients simply delete their stored token."""
    settings = get_settings()
    response.delete_cookie(
        settings.session_cookie_name,
        path="/",
        httponly=True,
        secure=settings.session_cookie_secure,
        samesite="strict",
    )
