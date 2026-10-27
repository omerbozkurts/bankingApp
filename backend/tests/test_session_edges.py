"""Cookie validation, credential precedence, and web security regressions."""

from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta

import httpx
import jwt
import pytest

from app.config import get_settings
from app.main import app
from app.security import create_access_token
from tests.conftest import login

CSRF = {"X-Requested-With": "abbank"}


@pytest.fixture
async def browser() -> AsyncIterator[httpx.AsyncClient]:
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="https://test"
    ) as client:
        yield client


@pytest.mark.parametrize("path", ["/me", "/accounts"])
@pytest.mark.parametrize("case", ["malformed", "expired", "wrong_secret", "unknown"])
async def test_invalid_cookie_is_unauthorized(browser, create_customer, path, case):
    customer = await create_customer()
    settings = get_settings()
    now = datetime.now(UTC)
    payload = {
        "sub": str(customer.id if case != "unknown" else customer.id + 1000000),
        "type": "access",
        "iat": now - timedelta(minutes=2),
        "exp": now + timedelta(minutes=-1 if case == "expired" else 30),
    }
    secret = "wrong-secret-" + "x" * 40 if case == "wrong_secret" else settings.jwt_secret
    token = jwt.encode(payload, secret, algorithm=settings.jwt_algorithm)
    browser.cookies.set(settings.session_cookie_name, "not-a-jwt" if case == "malformed" else token)
    response = await browser.get(path, headers=CSRF)
    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"


@pytest.mark.parametrize("path", ["/me", "/accounts"])
async def test_invalid_bearer_does_not_fall_back_to_valid_cookie(browser, create_customer, path):
    await create_customer()
    assert (await login(browser, "123456789", "123456", web=True)).status_code == 200
    response = await browser.get(path, headers={**CSRF, "Authorization": "Bearer invalid"})
    assert response.status_code == 401


async def test_bearer_takes_priority_over_another_customers_cookie(browser, create_customer):
    cookie_customer = await create_customer()
    bearer_customer = await create_customer(customer_no="987654321")
    response = await login(browser, cookie_customer.customer_no, "123456", web=True)
    assert response.status_code == 200
    token, _ = create_access_token(bearer_customer.id)
    response = await browser.get("/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert response.json()["customer_no"] == bearer_customer.customer_no


async def test_valid_bearer_ignores_invalid_cookie(browser, create_customer):
    customer = await create_customer()
    browser.cookies.set(get_settings().session_cookie_name, "invalid")
    token, _ = create_access_token(customer.id)
    response = await browser.get("/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200


@pytest.mark.parametrize("path", ["/me", "/accounts"])
async def test_empty_csrf_header_is_rejected(browser, create_customer, path):
    await create_customer()
    await login(browser, "123456789", "123456", web=True)
    response = await browser.get(path, headers={"X-Requested-With": ""})
    assert response.status_code == 401


async def test_logout_is_idempotent_and_deletes_matching_cookie(browser, create_customer):
    await create_customer()
    await login(browser, "123456789", "123456", web=True)
    for _ in range(2):
        response = await browser.post("/auth/logout", headers=CSRF)
        assert response.status_code == 204
        assert response.content == b""
        cookie = response.headers["set-cookie"].lower()
        for attribute in ("max-age=0", "path=/", "httponly", "secure", "samesite=strict"):
            assert attribute in cookie
    assert (await browser.get("/me", headers=CSRF)).status_code == 401


@pytest.mark.parametrize("origin", ["https://evil.example", "http://localhost:8082"])
async def test_untrusted_login_preflight_is_rejected(browser, origin):
    response = await browser.options(
        "/auth/login",
        headers={
            "Origin": origin,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type,x-requested-with",
        },
    )
    assert response.status_code == 400
    assert "access-control-allow-origin" not in response.headers


async def test_web_login_must_not_expose_cookie_token_in_json(browser, create_customer):
    await create_customer()
    response = await browser.post(
        "/auth/login",
        json={"customer_no": "123456789", "password": "123456"},
        headers={"Origin": "http://localhost:8081", "X-Session-Mode": "cookie", **CSRF},
    )
    assert response.status_code == 200
    assert get_settings().session_cookie_name in browser.cookies
    assert "access_token" not in response.json(), "Web JavaScript can read the session JWT"
