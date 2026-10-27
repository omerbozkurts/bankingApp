from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.models import Customer
from app.security import decode_access_token

SessionDep = Annotated[AsyncSession, Depends(get_session)]

bearer = HTTPBearer(auto_error=False)


async def get_current_customer(
    session: SessionDep,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
) -> Customer:
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Oturumunuz geçersiz veya süresi doldu. Lütfen tekrar giriş yapın.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if credentials is None:
        raise unauthorized
    customer_id = decode_access_token(credentials.credentials)
    if customer_id is None:
        raise unauthorized
    customer = await session.get(Customer, customer_id)
    if customer is None:
        raise unauthorized
    return customer


CurrentCustomer = Annotated[Customer, Depends(get_current_customer)]
