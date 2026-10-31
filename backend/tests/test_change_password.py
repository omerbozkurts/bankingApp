"""Password change: current password check, lockout, and signing out every other session."""

import asyncio

import jwt
import pytest

from app.config import get_settings
from app.security import create_access_token
from tests.conftest import login

CHANGE = {"current_password": "123456", "new_password": "246813"}
WEB = {"X-Requested-With": "abbank"}


@pytest.fixture
async def deniz(create_customer):
    return await create_customer()


async def bearer(client, password: str = "123456") -> dict[str, str]:
    response = await login(client, "123456789", password)
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


async def test_change_password_signs_out_other_sessions(client, deniz):
    phone = await bearer(client)
    other_phone = await bearer(client)

    changed = await client.post("/auth/change-password", headers=phone, json=CHANGE)
    assert changed.status_code == 200, changed.text
    fresh = {"Authorization": f"Bearer {changed.json()['access_token']}"}

    assert (await client.get("/me", headers=fresh)).status_code == 200
    # Every token from before the change is dead, including the one that made the request.
    assert (await client.get("/me", headers=phone)).status_code == 401
    assert (await client.get("/me", headers=other_phone)).status_code == 401

    assert (await login(client, "123456789", "123456")).status_code == 401
    assert (await login(client, "123456789", "246813")).status_code == 200


async def test_web_session_gets_a_new_cookie(web_client, deniz):
    client = web_client
    web = await login(client, "123456789", "123456", web=True)
    old_cookie = web.cookies[get_settings().session_cookie_name]
    changed = await client.post("/auth/change-password", headers=WEB, json=CHANGE)
    assert changed.status_code == 200, changed.text
    # The token stays out of the body that page JavaScript can read.
    assert "access_token" not in changed.json()
    new_cookie = changed.cookies[get_settings().session_cookie_name]
    assert new_cookie != old_cookie
    assert (await client.get("/me", headers=WEB)).status_code == 200

    client.cookies.set(get_settings().session_cookie_name, old_cookie)
    assert (await client.get("/me", headers=WEB)).status_code == 401


async def test_wrong_current_password(client, deniz):
    phone = await bearer(client)
    wrong = await client.post(
        "/auth/change-password", headers=phone, json={**CHANGE, "current_password": "000000"}
    )
    assert wrong.status_code == 400
    assert wrong.json()["detail"] == "Mevcut şifreniz hatalı."
    # Nothing changed: the session and the old password still work.
    assert (await client.get("/me", headers=phone)).status_code == 200
    assert (await login(client, "123456789", "123456")).status_code == 200


async def test_wrong_current_passwords_lock_like_logins(client, deniz):
    phone = await bearer(client)
    for _ in range(get_settings().max_failed_logins):
        await client.post(
            "/auth/change-password", headers=phone, json={**CHANGE, "current_password": "000000"}
        )
    # Locked now: even the right current password is refused, and so is a login.
    locked = await client.post("/auth/change-password", headers=phone, json=CHANGE)
    assert locked.status_code == 429
    assert (await login(client, "123456789", "123456")).status_code == 401


async def test_failed_logins_and_change_attempts_share_one_count(client, deniz):
    phone = await bearer(client)
    for _ in range(get_settings().max_failed_logins - 1):
        await login(client, "123456789", "000000")
    await client.post(
        "/auth/change-password", headers=phone, json={**CHANGE, "current_password": "000000"}
    )
    assert (
        await client.post("/auth/change-password", headers=phone, json=CHANGE)
    ).status_code == 429


@pytest.mark.parametrize(
    "body",
    [
        {**CHANGE, "new_password": "111111"},
        {**CHANGE, "new_password": "123456789"},
        {**CHANGE, "new_password": "12345"},
        {**CHANGE, "new_password": "654321"},
        {**CHANGE, "current_password": ""},
        {"new_password": "246813"},
    ],
)
async def test_invalid_new_password_rejected(client, deniz, body):
    phone = await bearer(client)
    assert (await client.post("/auth/change-password", headers=phone, json=body)).status_code == 422


async def test_new_password_must_differ(client, create_customer):
    await create_customer(password="246813")
    phone = await bearer(client, "246813")
    same = await client.post(
        "/auth/change-password",
        headers=phone,
        json={"current_password": "246813", "new_password": "246813"},
    )
    assert same.status_code == 400
    assert same.json()["detail"] == "Yeni şifre mevcut şifrenizle aynı olamaz."


async def test_requires_a_session(web_client, deniz):
    assert (await web_client.post("/auth/change-password", json=CHANGE)).status_code == 401
    # A cookie alone, without the CSRF header, is not a session.
    await login(web_client, "123456789", "123456", web=True)
    assert (await web_client.post("/auth/change-password", json=CHANGE)).status_code == 401
    assert (await web_client.get("/me", headers=WEB)).status_code == 200


async def test_tokens_without_a_version_still_work_until_a_change(client, deniz):
    # Tokens issued before session versions existed have no "ver" claim.
    token, _ = create_access_token(deniz.id)
    payload = jwt.decode(token, options={"verify_signature": False})
    del payload["ver"]
    settings = get_settings()
    legacy = jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)
    headers = {"Authorization": f"Bearer {legacy}"}
    assert (await client.get("/me", headers=headers)).status_code == 200
    assert (
        await client.post("/auth/change-password", headers=headers, json=CHANGE)
    ).status_code == 200
    assert (await client.get("/me", headers=headers)).status_code == 401


@pytest.mark.parametrize("version", [True, "0", 1.0, None])
async def test_malformed_version_claims_are_rejected(client, deniz, version):
    token, _ = create_access_token(deniz.id)
    payload = jwt.decode(token, options={"verify_signature": False})
    payload["ver"] = version
    settings = get_settings()
    forged = jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)
    assert (
        await client.get("/me", headers={"Authorization": f"Bearer {forged}"})
    ).status_code == 401


async def test_empty_bearer_preserves_cookie_session_mode(web_client, deniz):
    await login(web_client, "123456789", "123456", web=True)
    changed = await web_client.post(
        "/auth/change-password",
        headers={**WEB, "Authorization": "Bearer "},
        json=CHANGE,
    )
    assert changed.status_code == 200, changed.text
    # HTTPBearer ignores empty credentials, so this request authenticated with the cookie.
    # Its replacement must remain httpOnly and update that cookie, not expose a body token.
    assert "access_token" not in changed.json()
    assert get_settings().session_cookie_name in changed.cookies
    assert (await web_client.get("/me", headers=WEB)).status_code == 200


async def test_bearer_takes_precedence_over_another_customers_cookie(
    web_client, deniz, create_customer
):
    await create_customer(customer_no="987654321", password="135792")
    phone = await bearer(web_client)
    await login(web_client, "987654321", "135792", web=True)
    changed = await web_client.post("/auth/change-password", headers=phone, json=CHANGE)
    assert changed.status_code == 200, changed.text
    assert "access_token" in changed.json()
    assert get_settings().session_cookie_name not in changed.cookies
    fresh = {"Authorization": f"Bearer {changed.json()['access_token']}"}
    assert (await web_client.get("/me", headers=fresh)).json()["customer_no"] == "123456789"
    assert (await web_client.get("/me", headers=WEB)).json()["customer_no"] == "987654321"
    # A revoked bearer must not fall back to the still-valid cookie either.
    assert (await web_client.get("/me", headers={**WEB, **phone})).status_code == 401


async def test_parallel_wrong_passwords_cannot_lose_lockout_increments(client, deniz):
    phone = await bearer(client)
    limit = get_settings().max_failed_logins
    responses = await asyncio.gather(
        *(
            client.post(
                "/auth/change-password",
                headers=phone,
                json={**CHANGE, "current_password": "000000"},
            )
            for _ in range(limit + 3)
        )
    )
    assert sum(r.status_code == 400 for r in responses) == limit
    assert sum(r.status_code == 429 for r in responses) == 3
    assert (
        await client.post("/auth/change-password", headers=phone, json=CHANGE)
    ).status_code == 429


async def test_concurrent_changes_with_one_token_revoke_the_loser(client, deniz):
    """The second request waits for the row lock, then finds its token revoked: 401, not 400."""
    phone = await bearer(client)
    results = await asyncio.gather(
        client.post("/auth/change-password", headers=phone, json=CHANGE),
        client.post("/auth/change-password", headers=phone, json=CHANGE),
    )
    assert sorted(r.status_code for r in results) == [200, 401]
    # The loser didn't count as a wrong password.
    for _ in range(get_settings().max_failed_logins - 1):
        await login(client, "123456789", "000000")
    assert (await login(client, "123456789", "246813")).status_code == 200
