from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.concurrency import run_in_threadpool
from sqlalchemy import select

from app.config import get_settings
from app.deps import SESSION_MODE_HEADER, SessionDep, require_csrf_header
from app.models import Customer
from app.rate_limit import SlidingWindowLimiter
from app.schemas import LoginRequest, Token
from app.security import create_access_token, verify_password

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
    client_ip = request.client.host if request.client else "unknown"
    if not login_limiter.allow(client_ip):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Çok fazla giriş denemesi yapıldı. Lütfen birkaç dakika sonra tekrar deneyin.",
        )

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
