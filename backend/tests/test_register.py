import asyncio
from datetime import date, timedelta

import pytest
from sqlalchemy import select, text

from app.banking import is_valid_tr_iban, national_id_digest
from app.config import get_settings
from app.db import SessionLocal
from app.models import Account, Customer
from tests.conftest import login

BODY = {
    "national_id": "10000000146",
    "full_name": "Deniz Yılmaz",
    "birth_date": "1990-01-01",
    "password": "582963",
}


async def test_registration(client):
    response = await client.post("/auth/register", json=BODY)
    assert response.status_code == 201, response.text
    data = response.json()
    assert len(data["customer_no"]) == 9 and data["customer_no"].isascii()
    assert data["customer_no"].isdigit()
    assert (await login(client, data["customer_no"], BODY["password"])).status_code == 200
    async with SessionLocal() as session:
        customer = await session.scalar(select(Customer))
        assert customer.national_id_digest == national_id_digest(
            BODY["national_id"], get_settings().national_id_pepper
        )
        assert customer.password_hash != BODY["password"]
        # Inspect all persisted customer columns, not just the mapped digest attribute.
        raw = await session.scalar(text("SELECT row_to_json(customers)::text FROM customers"))
        assert BODY["national_id"] not in raw
        accounts = list(await session.scalars(select(Account)))
        assert len(accounts) == 1
        assert accounts[0].customer_id == customer.id
        assert accounts[0].kind == "checking" and accounts[0].balance_kurus == 0
        assert is_valid_tr_iban(accounts[0].iban)


async def test_duplicate(client):
    assert (await client.post("/auth/register", json=BODY)).status_code == 201
    assert (await client.post("/auth/register", json=BODY)).status_code == 409
    async with SessionLocal() as session:
        assert len(list(await session.scalars(select(Customer)))) == 1
        assert len(list(await session.scalars(select(Account)))) == 1


@pytest.mark.parametrize(
    ("patch", "detail"),
    [
        ({"national_id": "10000000147"}, "T.C. kimlik numarası geçersiz."),
        (
            {"birth_date": (date.today() - timedelta(days=365 * 17)).isoformat()},
            "Hesap açmak için 18 yaşından büyük olmalısınız.",
        ),
        ({"birth_date": (date.today() + timedelta(days=1)).isoformat()}, "Doğum tarihi geçersiz."),
        ({"full_name": "Deniz123 Yılmaz"}, "Ad soyad yalnızca harflerden oluşmalı."),
    ],
)
async def test_invalid_registration(client, patch, detail):
    response = await client.post("/auth/register", json={**BODY, **patch})
    assert response.status_code == 422
    assert response.json()["detail"] == detail
    assert response.json()["errors"]
    assert BODY["password"] not in response.text
    async with SessionLocal() as session:
        assert not list(await session.scalars(select(Customer)))


async def test_sixth_attempt_limited(client):
    for i in range(6):
        response = await client.post("/auth/register", json=BODY)
        assert response.status_code == (201 if i == 0 else 409 if i < 5 else 429)


async def test_parallel_duplicate_registration(client):
    responses = await asyncio.wait_for(
        asyncio.gather(*[client.post("/auth/register", json=BODY) for _ in range(2)]), timeout=20
    )
    assert sorted(r.status_code for r in responses) == [201, 409]
    async with SessionLocal() as session:
        assert len(list(await session.scalars(select(Customer)))) == 1
        assert len(list(await session.scalars(select(Account)))) == 1


async def test_unicode_identity_cannot_register_same_person_twice(client):
    assert (await client.post("/auth/register", json=BODY)).status_code == 201
    alternate = BODY["national_id"].translate(str.maketrans("0123456789", "０１２３４５６７８９"))
    response = await client.post("/auth/register", json={**BODY, "national_id": alternate})
    assert response.status_code in (409, 422), response.text


@pytest.mark.parametrize("password", ["111111", "000000", "123456", "654321", "345678", "012345"])
async def test_guessable_password_rejected(client, password):
    response = await client.post("/auth/register", json={**BODY, "password": password})
    assert response.status_code == 422
    assert response.json()["detail"] == (
        "Tahmin edilmesi kolay bir şifre seçmeyin (111111, 123456 gibi)."
    )
    ok = await client.post("/auth/register", json={**BODY, "password": "482913"})
    assert ok.status_code == 201
