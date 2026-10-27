"""Web session: httpOnly cookie plus the X-Requested-With CSRF header."""

from collections.abc import AsyncIterator

import httpx
import pytest

from app.config import get_settings
from app.main import app
from tests.conftest import login

CSRF = {"X-Requested-With": "abbank"}


@pytest.fixture
async def web_client() -> AsyncIterator[httpx.AsyncClient]:
    # https so httpx sends back the Secure cookie, like a browser would.
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="https://test") as c:
        yield c


async def test_login_sets_hardened_session_cookie(web_client, create_customer):
    await create_customer()
    response = await login(web_client, "123456789", "123456", web=True)
    assert response.status_code == 200

    set_cookie = response.headers["set-cookie"].lower()
    assert set_cookie.startswith(f"{get_settings().session_cookie_name}=")
    assert "httponly" in set_cookie
    assert "secure" in set_cookie
    assert "samesite=strict" in set_cookie
    assert "max-age=1800" in set_cookie


async def test_cookie_with_csrf_header_authenticates(web_client, create_customer):
    await create_customer()
    await login(web_client, "123456789", "123456", web=True)

    me = await web_client.get("/me", headers=CSRF)
    assert me.status_code == 200
    assert me.json()["customer_no"] == "123456789"
    accounts = await web_client.get("/accounts", headers=CSRF)
    assert accounts.status_code == 200


async def test_cookie_without_csrf_header_is_rejected(web_client, create_customer):
    await create_customer()
    await login(web_client, "123456789", "123456", web=True)

    response = await web_client.get("/me")
    assert response.status_code == 401


async def test_failed_login_sets_no_cookie(web_client, create_customer):
    await create_customer()
    response = await login(web_client, "123456789", "000000", web=True)
    assert response.status_code == 401
    assert "set-cookie" not in response.headers


async def test_logout_clears_cookie(web_client, create_customer):
    await create_customer()
    await login(web_client, "123456789", "123456", web=True)

    response = await web_client.post("/auth/logout", headers=CSRF)
    assert response.status_code == 204
    assert get_settings().session_cookie_name not in web_client.cookies
    assert (await web_client.get("/me", headers=CSRF)).status_code == 401


async def test_cors_allows_credentials_only_for_known_origin(client):
    preflight = {
        "Access-Control-Request-Method": "GET",
        "Access-Control-Request-Headers": "x-requested-with",
    }
    allowed = await client.options(
        "/me", headers={"Origin": "http://localhost:8081", **preflight}
    )
    assert allowed.status_code == 200
    assert allowed.headers["access-control-allow-origin"] == "http://localhost:8081"
    assert allowed.headers["access-control-allow-credentials"] == "true"

    evil = await client.options("/me", headers={"Origin": "https://evil.example", **preflight})
    assert "access-control-allow-origin" not in evil.headers


async def test_web_login_returns_no_token_in_body(web_client, create_customer):
    await create_customer()
    response = await login(web_client, "123456789", "123456", web=True)
    assert response.json() == {"token_type": "cookie", "expires_in": 1800}


async def test_mobile_login_returns_token_and_sets_no_cookie(web_client, create_customer):
    await create_customer()
    response = await login(web_client, "123456789", "123456")
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]
    assert "set-cookie" not in response.headers


async def test_logout_requires_csrf_header(web_client, create_customer):
    await create_customer()
    await login(web_client, "123456789", "123456", web=True)
    response = await web_client.post("/auth/logout")
    assert response.status_code == 403
    # The session survives a forged logout attempt.
    assert (await web_client.get("/me", headers=CSRF)).status_code == 200
