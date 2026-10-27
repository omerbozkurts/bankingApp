from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db import get_session
from app.models import Customer
from app.security import decode_access_token

SessionDep = Annotated[AsyncSession, Depends(get_session)]

bearer = HTTPBearer(auto_error=False)

# Cookie-authenticated requests must carry this header. Browsers only let a page send a custom
# header cross-origin after a CORS preflight, which our CORS policy rejects for unknown origins,
# so this blocks CSRF on top of the SameSite=Strict cookie.
CSRF_HEADER = "X-Requested-With"

# Web clients send `X-Session-Mode: cookie` on login to get an httpOnly cookie instead of a token
# in the response body. Mobile clients omit it and store the body token in secure storage.
SESSION_MODE_HEADER = "X-Session-Mode"


def require_csrf_header(request: Request) -> None:
    if not request.headers.get(CSRF_HEADER):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Geçersiz istek.")


def _unauthorized() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Oturumunuz geçersiz veya süresi doldu. Lütfen tekrar giriş yapın.",
        headers={"WWW-Authenticate": "Bearer"},
    )


def _request_token(request: Request, credentials: HTTPAuthorizationCredentials | None) -> str:
    """Bearer header (mobile) first, then the session cookie (web)."""
    if credentials is not None:
        return credentials.credentials
    cookie = request.cookies.get(get_settings().session_cookie_name)
    if cookie and request.headers.get(CSRF_HEADER):
        return cookie
    raise _unauthorized()


async def get_current_customer(
    request: Request,
    session: SessionDep,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
) -> Customer:
    customer_id = decode_access_token(_request_token(request, credentials))
    if customer_id is None:
        raise _unauthorized()
    customer = await session.get(Customer, customer_id)
    if customer is None:
        raise _unauthorized()
    return customer


CurrentCustomer = Annotated[Customer, Depends(get_current_customer)]
