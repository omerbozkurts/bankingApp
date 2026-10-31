"""Saved recipients: save after a lookup-style check, list, delete, and per-customer isolation."""

import asyncio

import pytest
from sqlalchemy import select

from app.banking import make_tr_iban
from app.db import SessionLocal
from app.models import Customer, SavedRecipient
from app.routers.recipients import MAX_SAVED_RECIPIENTS
from app.routers.transfers import lookup_limiter
from tests.conftest import login

ALI_IBAN = make_tr_iban("3".zfill(16))
CREDIT_IBAN = make_tr_iban("9".zfill(16))


@pytest.fixture
async def bank(client, create_customer):
    """Deniz (signed in) with checking 1; Ali 987654321 with checking 3 and credit 9."""
    await create_customer(
        full_name="Deniz Yılmaz",
        accounts=[{"id": 1, "name": "Vadesiz", "iban": make_tr_iban("1".zfill(16))}],
    )
    await create_customer(
        customer_no="987654321",
        password="654321",
        full_name="Ali Kaya",
        accounts=[
            {"id": 3, "name": "Vadesiz", "iban": ALI_IBAN},
            {
                "id": 9,
                "kind": "credit",
                "name": "Kredili",
                "iban": CREDIT_IBAN,
                "credit_limit_kurus": 2_000_000,
            },
        ],
    )
    return await bearer(client, "123456789", "123456")


async def bearer(client, customer_no: str, password: str) -> dict[str, str]:
    token = (await login(client, customer_no, password)).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


async def test_save_list_and_delete(client, bank):
    by_iban = await client.post(
        "/recipients/saved", headers=bank, json={"nickname": " Ev sahibi ", "iban": ALI_IBAN}
    )
    assert by_iban.status_code == 201, by_iban.text
    assert by_iban.json() == {
        "id": 1,
        "nickname": "Ev sahibi",
        "iban": ALI_IBAN,
        "customer_no": None,
        "masked_name": "Al*** Ka***",
    }
    by_number = await client.post(
        "/recipients/saved", headers=bank, json={"nickname": "ali", "customer_no": "987654321"}
    )
    assert by_number.status_code == 201
    # A customer number is saved without the IBAN behind it.
    assert by_number.json()["iban"] is None

    listed = (await client.get("/recipients/saved", headers=bank)).json()
    # Sorted by nickname, case-insensitively.
    assert [r["nickname"] for r in listed] == ["ali", "Ev sahibi"]

    assert (await client.delete("/recipients/saved/1", headers=bank)).status_code == 204
    assert [r["id"] for r in (await client.get("/recipients/saved", headers=bank)).json()] == [2]
    assert (await client.delete("/recipients/saved/1", headers=bank)).status_code == 404


async def test_iban_is_stored_normalised(client, bank):
    spaced = " ".join(ALI_IBAN[i : i + 4] for i in range(0, len(ALI_IBAN), 4)).lower()
    saved = await client.post(
        "/recipients/saved", headers=bank, json={"nickname": "Ali", "iban": spaced}
    )
    assert saved.json()["iban"] == ALI_IBAN
    again = await client.post(
        "/recipients/saved", headers=bank, json={"nickname": "Başka ad", "iban": ALI_IBAN}
    )
    assert again.status_code == 409
    assert again.json()["detail"] == "Bu alıcı zaten kayıtlı."


@pytest.mark.parametrize(
    ("body", "status"),
    [
        ({"nickname": "X", "iban": make_tr_iban("5".zfill(16))}, 404),
        ({"nickname": "X", "customer_no": "000000000"}, 404),
        # Someone else's credit account can't be paid, so it can't be saved either.
        ({"nickname": "X", "iban": CREDIT_IBAN}, 404),
        ({"nickname": "  ", "iban": ALI_IBAN}, 422),
        ({"nickname": "x" * 41, "iban": ALI_IBAN}, 422),
        ({"nickname": "X"}, 422),
        ({"nickname": "X", "iban": ALI_IBAN, "customer_no": "987654321"}, 422),
        ({"nickname": "X", "iban": "TR00"}, 422),
    ],
)
async def test_invalid_recipients_are_not_saved(client, bank, body, status):
    response = await client.post("/recipients/saved", headers=bank, json=body)
    assert response.status_code == status
    assert (await client.get("/recipients/saved", headers=bank)).json() == []


async def test_saving_uses_the_lookup_quota(client, bank):
    for _ in range(lookup_limiter.max_requests):
        await client.get("/recipients/lookup?customer_no=000000000", headers=bank)
    response = await client.post(
        "/recipients/saved", headers=bank, json={"nickname": "Ali", "customer_no": "987654321"}
    )
    assert response.status_code == 429


async def test_recipients_are_private(client, bank):
    await client.post("/recipients/saved", headers=bank, json={"nickname": "Ali", "iban": ALI_IBAN})
    ali = await bearer(client, "987654321", "654321")
    assert (await client.get("/recipients/saved", headers=ali)).json() == []
    assert (await client.delete("/recipients/saved/1", headers=ali)).status_code == 404
    assert len((await client.get("/recipients/saved", headers=bank)).json()) == 1
    assert (await client.get("/recipients/saved")).status_code == 401


async def test_saved_recipient_limit(client, bank, create_customer, monkeypatch):
    monkeypatch.setattr("app.routers.recipients.MAX_SAVED_RECIPIENTS", 2)
    for i, number in enumerate(["111111111", "222222222", "333333333"]):
        await create_customer(
            customer_no=number,
            accounts=[
                {"id": 20 + i, "name": "Vadesiz", "iban": make_tr_iban(f"{i + 4}".zfill(16))}
            ],
        )
    statuses = [
        (
            await client.post(
                "/recipients/saved", headers=bank, json={"nickname": n, "customer_no": n}
            )
        ).status_code
        for n in ["111111111", "222222222", "333333333"]
    ]
    assert statuses == [201, 201, 409]
    assert MAX_SAVED_RECIPIENTS == 50


async def test_parallel_duplicate_saves_keep_one(client, bank):
    body = {"nickname": "Ali", "iban": ALI_IBAN}
    results = await asyncio.gather(
        client.post("/recipients/saved", headers=bank, json=body),
        client.post("/recipients/saved", headers=bank, json=body),
    )
    assert sorted(r.status_code for r in results) == [201, 409]
    assert len((await client.get("/recipients/saved", headers=bank)).json()) == 1


async def test_delete_is_allowed_by_cors(client):
    preflight = await client.options(
        "/recipients/saved/1",
        headers={"Origin": "http://localhost:8081", "Access-Control-Request-Method": "DELETE"},
    )
    assert preflight.status_code == 200
    assert "DELETE" in preflight.headers["access-control-allow-methods"]


async def test_parallel_saves_compete_for_last_slot(client, bank):
    async with SessionLocal() as session:
        customer_id = await session.scalar(
            select(Customer.id).where(Customer.customer_no == "123456789")
        )
        session.add_all(
            SavedRecipient(
                customer_id=customer_id,
                nickname=f"Recipient {i}",
                customer_no=f"{i:09d}",
                masked_name="Te***",
            )
            for i in range(MAX_SAVED_RECIPIENTS - 1)
        )
        await session.commit()

    results = await asyncio.gather(
        client.post(
            "/recipients/saved", headers=bank, json={"nickname": "Ali IBAN", "iban": ALI_IBAN}
        ),
        client.post(
            "/recipients/saved",
            headers=bank,
            json={"nickname": "Ali number", "customer_no": "987654321"},
        ),
    )
    assert sorted(r.status_code for r in results) == [201, 409]
    assert len((await client.get("/recipients/saved", headers=bank)).json()) == 50


async def test_cookie_delete_requires_csrf_header(web_client, bank):
    assert (await login(web_client, "123456789", "123456", web=True)).status_code == 200
    headers = {"X-Requested-With": "abbank"}
    saved = await web_client.post(
        "/recipients/saved", headers=headers, json={"nickname": "Ali", "iban": ALI_IBAN}
    )
    assert saved.status_code == 201
    path = f"/recipients/saved/{saved.json()['id']}"
    assert (await web_client.delete(path)).status_code == 401
    preflight = await web_client.options(
        path,
        headers={
            "Origin": "http://localhost:8081",
            "Access-Control-Request-Method": "DELETE",
            "Access-Control-Request-Headers": "X-Requested-With",
        },
    )
    assert preflight.status_code == 200
    assert (await web_client.delete(path, headers=headers)).status_code == 204
