from datetime import UTC, datetime, timedelta

import jwt
import pytest

from app.config import get_settings
from app.db import SessionLocal
from app.models import Customer
from app.routers.auth import INVALID_CREDENTIALS
from tests.conftest import login


async def test_login_success(client, create_customer):
    await create_customer()
    response = await login(client, "123456789", "123456")
    assert response.status_code == 200
    assert response.json()["token_type"] == "bearer"
    assert response.json()["expires_in"] == 1800
    assert response.json()["access_token"]


async def test_invalid_credentials_have_identical_detail(client, create_customer):
    await create_customer()
    for number in ("123456789", "987654321"):
        response = await login(client, number, "654321")
        assert response.status_code == 401
        assert response.json() == {"detail": INVALID_CREDENTIALS}


@pytest.mark.parametrize(
    "body",
    [
        {"customer_no": "12345678", "password": "123456"},
        {"customer_no": "1234567890", "password": "123456"},
        {"customer_no": "123456789", "password": "12345a"},
        {"customer_no": "123456789"},
        {"password": "123456"},
    ],
)
async def test_login_format_errors(client, body):
    response = await client.post("/auth/login", json=body)
    assert response.status_code == 422


async def test_lockout_and_expiry(client, create_customer):
    customer = await create_customer()
    for _ in range(5):
        response = await login(client, customer.customer_no, "654321")
        assert response.status_code == 401

    # Locked: even the right password fails, with the same response an unknown customer gets.
    response = await login(client, customer.customer_no, "123456")
    unknown = await login(client, "999999999", "123456")
    assert response.status_code == unknown.status_code == 401
    assert response.json() == unknown.json() == {"detail": INVALID_CREDENTIALS}
    async with SessionLocal() as session:
        stored = await session.get(Customer, customer.id)
        assert stored.locked_until > datetime.now(UTC)
        assert stored.failed_login_count == 0
        stored.locked_until = datetime.now(UTC) - timedelta(seconds=1)
        await session.commit()

    response = await login(client, customer.customer_no, "123456")
    assert response.status_code == 200
    async with SessionLocal() as session:
        stored = await session.get(Customer, customer.id)
        assert stored.failed_login_count == 0
        assert stored.locked_until is None


async def test_successful_login_resets_failed_counter(client, create_customer):
    customer = await create_customer()
    response = await login(client, customer.customer_no, "654321")
    assert response.status_code == 401
    async with SessionLocal() as session:
        stored = await session.get(Customer, customer.id)
        assert stored.failed_login_count == 1
    response = await login(client, customer.customer_no, "123456")
    assert response.status_code == 200
    async with SessionLocal() as session:
        stored = await session.get(Customer, customer.id)
        assert stored.failed_login_count == 0


@pytest.mark.parametrize("path", ["/me", "/accounts"])
@pytest.mark.parametrize(
    "token_case", ["missing", "malformed", "wrong_secret", "expired", "wrong_type", "unknown"]
)
async def test_protected_routes_reject_invalid_tokens(client, create_customer, path, token_case):
    customer = await create_customer()
    settings = get_settings()
    now = datetime.now(UTC)
    payload = {
        "sub": str(customer.id),
        "type": "access",
        "iat": now - timedelta(minutes=2),
        "exp": now + timedelta(minutes=30),
    }
    secret = settings.jwt_secret
    if token_case == "wrong_secret":
        secret = "incorrect-signing-secret-" + "x" * 40
    elif token_case == "expired":
        payload["exp"] = now - timedelta(minutes=1)
    elif token_case == "wrong_type":
        payload["type"] = "refresh"
    elif token_case == "unknown":
        payload["sub"] = str(customer.id + 1000000)
    token = jwt.encode(payload, secret, algorithm=settings.jwt_algorithm)
    if token_case == "malformed":
        token = "not-a-jwt"
    headers = {} if token_case == "missing" else {"Authorization": f"Bearer {token}"}
    response = await client.get(path, headers=headers)
    assert response.status_code == 401
    assert response.headers["WWW-Authenticate"] == "Bearer"


async def test_attempts_while_locked_do_not_extend_lock(client, create_customer):
    customer = await create_customer()
    for _ in range(5):
        await login(client, customer.customer_no, "654321")
    async with SessionLocal() as session:
        locked_until = (await session.get(Customer, customer.id)).locked_until

    await login(client, customer.customer_no, "654321")
    async with SessionLocal() as session:
        stored = await session.get(Customer, customer.id)
        assert stored.locked_until == locked_until
        assert stored.failed_login_count == 0


async def test_ip_rate_limit_applies_to_any_customer_number(client):
    limit = get_settings().login_rate_limit
    for i in range(limit):
        response = await login(client, f"{100000000 + i}", "123456")
        assert response.status_code == 401
    response = await login(client, "999999999", "123456")
    assert response.status_code == 429
