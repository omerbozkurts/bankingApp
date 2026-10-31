"""Sending money by customer number: lookup, routing to the checking account, IBAN masking."""

import pytest

from app.banking import make_tr_iban, mask_iban
from tests.conftest import login

ALI_CHECKING = make_tr_iban("3".zfill(16))


@pytest.fixture
async def bank(client, create_customer):
    """Deniz: checking 1 (1.000 TL), savings 2. Ali 987654321: credit 3, savings 4, checking 5."""
    await create_customer(
        full_name="Deniz Yılmaz",
        accounts=[
            {
                "id": 1,
                "name": "Vadesiz",
                "iban": make_tr_iban("1".zfill(16)),
                "balance_kurus": 100_000,
            },
            {"id": 2, "kind": "savings", "name": "Birikim", "iban": make_tr_iban("2".zfill(16))},
        ],
    )
    # Ali's checking account isn't his first account: money must still land there.
    await create_customer(
        customer_no="987654321",
        password="654321",
        full_name="Ali Kaya",
        accounts=[
            {
                "id": 3,
                "kind": "credit",
                "name": "Kredili",
                "iban": make_tr_iban("9".zfill(16)),
                "credit_limit_kurus": 2_000_000,
            },
            {"id": 4, "kind": "savings", "name": "Birikim", "iban": make_tr_iban("8".zfill(16))},
            {"id": 5, "name": "Vadesiz", "iban": ALI_CHECKING},
        ],
    )
    # No checking account at all: can't be paid by customer number.
    await create_customer(
        customer_no="111222333",
        password="246810",
        accounts=[
            {"id": 6, "kind": "savings", "name": "Birikim", "iban": make_tr_iban("6".zfill(16))}
        ],
    )
    token = (await login(client, "123456789", "123456")).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def by_number(customer_no: str, amount: int, key: str, from_id: int = 1, **extra) -> dict:
    return {
        "from_account_id": from_id,
        "to_customer_no": customer_no,
        "amount_kurus": amount,
        "idempotency_key": key,
        **extra,
    }


def test_mask_iban_keeps_country_check_digits_and_last_four():
    assert mask_iban(ALI_CHECKING) == ALI_CHECKING[:4] + "*" * 18 + ALI_CHECKING[-4:]


async def test_lookup_by_customer_no_masks_the_iban(client, bank):
    response = await client.get("/recipients/lookup?customer_no=987654321", headers=bank)
    assert response.status_code == 200
    assert response.json() == {"iban": mask_iban(ALI_CHECKING), "masked_name": "Al*** Ka***"}


@pytest.mark.parametrize("customer_no", ["000000000", "111222333"])
async def test_lookup_unknown_or_unpayable_customer(client, bank, customer_no):
    response = await client.get(f"/recipients/lookup?customer_no={customer_no}", headers=bank)
    assert response.status_code == 404
    assert "müşteri numarasıyla" in response.json()["detail"]


@pytest.mark.parametrize(
    "query", ["", f"?iban={ALI_CHECKING}&customer_no=987654321", "?customer_no=12345", "?iban=TR"]
)
async def test_lookup_needs_exactly_one_valid_recipient(client, bank, query):
    response = await client.get(f"/recipients/lookup{query}", headers=bank)
    assert response.status_code == 422


async def test_lookup_by_customer_no_is_rate_limited(client, bank):
    for _ in range(30):
        await client.get("/recipients/lookup?customer_no=000000000", headers=bank)
    response = await client.get("/recipients/lookup?customer_no=987654321", headers=bank)
    assert response.status_code == 429


async def test_transfer_by_customer_no_lands_in_checking_account(client, bank):
    sent = await client.post(
        "/transfers", headers=bank, json=by_number("987654321", 2_500, "cno-0001")
    )
    assert sent.status_code == 201, sent.text
    body = sent.json()
    assert body["to_iban"] == mask_iban(ALI_CHECKING)
    assert body["recipient"] == "Al*** Ka***"
    assert body["from_balance_after_kurus"] == 97_500

    ali = (await login(client, "987654321", "654321")).json()["access_token"]
    accounts = (await client.get("/accounts", headers={"Authorization": f"Bearer {ali}"})).json()
    assert {a["id"]: a["balance_kurus"] for a in accounts} == {3: 0, 4: 0, 5: 2_500}


async def test_retry_by_customer_no_replays_without_paying_twice(client, bank):
    first = await client.post(
        "/transfers", headers=bank, json=by_number("987654321", 100, "cno-0002")
    )
    again = await client.post(
        "/transfers", headers=bank, json=by_number("987654321", 100, "cno-0002")
    )
    assert first.status_code == 201 and again.status_code == 201
    assert again.json() == first.json()
    assert again.json()["to_iban"] == mask_iban(ALI_CHECKING)

    # The same key for another recipient, or for the same account by IBAN, is a different request.
    other = await client.post(
        "/transfers", headers=bank, json=by_number("111222333", 100, "cno-0002")
    )
    assert other.status_code == 409
    by_iban = {
        "from_account_id": 1,
        "to_iban": ALI_CHECKING,
        "amount_kurus": 100,
        "idempotency_key": "cno-0002",
    }
    assert (await client.post("/transfers", headers=bank, json=by_iban)).status_code == 201
    accounts = (await client.get("/accounts", headers=bank)).json()
    assert accounts[0]["balance_kurus"] == 99_900


async def test_iban_retry_with_customer_no_key_is_not_masked(client, bank):
    by_iban = {
        "from_account_id": 1,
        "to_iban": ALI_CHECKING,
        "amount_kurus": 100,
        "idempotency_key": "cno-0003",
    }
    first = await client.post("/transfers", headers=bank, json=by_iban)
    assert first.json()["to_iban"] == ALI_CHECKING
    # Retrying the same transfer by customer number replays it, but a reply to a request made
    # by number never shows the full IBAN.
    replay = await client.post(
        "/transfers", headers=bank, json=by_number("987654321", 100, "cno-0003")
    )
    assert replay.status_code == 201
    assert replay.json()["to_iban"] == mask_iban(ALI_CHECKING)


async def test_limits_and_checks_still_apply(client, bank):
    too_much = await client.post(
        "/transfers", headers=bank, json=by_number("987654321", 100_001, "cno-0004")
    )
    assert too_much.json()["detail"] == "Yetersiz bakiye."
    over_cap = await client.post(
        "/transfers", headers=bank, json=by_number("987654321", 5_000_001, "cno-0005")
    )
    assert over_cap.status_code == 400 and "en fazla" in over_cap.json()["detail"]
    nobody = await client.post(
        "/transfers", headers=bank, json=by_number("000000000", 1, "cno-0006")
    )
    assert nobody.status_code == 404


async def test_own_customer_no_goes_to_own_checking(client, bank):
    # Checking 1 is where the customer's own number points, so it can't pay itself.
    same = await client.post("/transfers", headers=bank, json=by_number("123456789", 1, "cno-0007"))
    assert same.status_code == 400
    assert same.json()["detail"] == "Aynı hesaba para gönderilemez."
    # Fill savings 2, then send from it to the own number: an own-account move into checking 1.
    fill = {
        "from_account_id": 1,
        "to_iban": make_tr_iban("2".zfill(16)),
        "amount_kurus": 400,
        "idempotency_key": "cno-0008",
    }
    assert (await client.post("/transfers", headers=bank, json=fill)).status_code == 201
    back = await client.post(
        "/transfers", headers=bank, json=by_number("123456789", 400, "cno-0009", from_id=2)
    )
    assert back.status_code == 201
    assert back.json()["recipient"] == "Vadesiz"
    balances = [a["balance_kurus"] for a in (await client.get("/accounts", headers=bank)).json()]
    assert balances == [100_000, 0]


@pytest.mark.parametrize(
    "recipient",
    [{}, {"to_iban": ALI_CHECKING, "to_customer_no": "987654321"}, {"to_customer_no": "98765"}],
)
async def test_transfer_needs_exactly_one_valid_recipient(client, bank, recipient):
    body = {"from_account_id": 1, "amount_kurus": 1, "idempotency_key": "cno-0010", **recipient}
    assert (await client.post("/transfers", headers=bank, json=body)).status_code == 422


async def test_replay_by_number_must_match_the_numbers_account(client, bank):
    """An IBAN payment to checking #2 is not a payment to the number's checking #1."""
    from app.db import SessionLocal
    from app.models import Account

    async with SessionLocal() as session:
        first = await session.get(Account, 5)
        session.add(Account(
            id=7, customer_id=first.customer_id, name="Second checking",
            iban=make_tr_iban("7".zfill(16)),
        ))
        await session.commit()
    original = await client.post("/transfers", headers=bank, json={
        "from_account_id": 1, "to_iban": make_tr_iban("7".zfill(16)),
        "amount_kurus": 100, "idempotency_key": "second-checking",
    })
    assert original.status_code == 201, original.text
    lookup = await client.get("/recipients/lookup?customer_no=987654321", headers=bank)
    assert lookup.json()["iban"] == mask_iban(ALI_CHECKING)
    replay = await client.post(
        "/transfers", headers=bank, json=by_number("987654321", 100, "second-checking")
    )
    assert replay.status_code == 409, "replay accepted a different destination account"


async def test_transfers_by_number_share_the_lookup_limit(client, bank):
    """Over-cap probes would otherwise enumerate payable numbers without moving money."""
    from app.routers.transfers import lookup_limiter

    for _ in range(lookup_limiter.max_requests):
        await client.get("/recipients/lookup?customer_no=000000000", headers=bank)
    blocked = await client.get("/recipients/lookup?customer_no=987654321", headers=bank)
    assert blocked.status_code == 429
    statuses = []
    for i in range(32):
        number = "987654321" if i % 2 else f"{i:09d}"
        response = await client.post(
            "/transfers", headers=bank,
            json=by_number(number, 5_000_001, f"enumerate-{i:04d}"),
        )
        assert ALI_CHECKING not in response.text
        statuses.append(response.status_code)
    assert 429 in statuses, f"unlimited existence oracle: {statuses}"


@pytest.mark.parametrize("number", [123456789, True, "987654321\n", " 987654321",
                                       "9876543210", "９８７６５４３２１", "", None])
async def test_number_validation_rejects_noncanonical_values(client, bank, number):
    response = await client.post(
        "/transfers", headers=bank, json=by_number(number, 1, "invalid-number")
    )
    assert response.status_code == 422, response.text
    assert ALI_CHECKING not in response.text


@pytest.mark.parametrize("change", [
    {"amount_kurus": 101}, {"from_account_id": 2}, {"description": "Changed"},
    {"to_customer_no": "123456789"},
])
async def test_number_replay_conflicts_do_not_disclose_iban(client, bank, change):
    original = by_number("987654321", 100, "conflict-number")
    assert (await client.post("/transfers", headers=bank, json=original)).status_code == 201
    response = await client.post("/transfers", headers=bank, json={**original, **change})
    assert response.status_code == 409
    assert ALI_CHECKING not in response.text


@pytest.mark.parametrize("amount,status", [(100_001, 400), (5_000_001, 400), (0, 422)])
async def test_number_error_responses_do_not_disclose_iban(client, bank, amount, status):
    response = await client.post(
        "/transfers", headers=bank, json=by_number("987654321", amount, "masked-error")
    )
    assert response.status_code == status
    assert ALI_CHECKING not in response.text


async def test_own_number_from_credit_can_draw_above_external_cap(client, bank):
    from app.db import SessionLocal
    from app.models import Account

    async with SessionLocal() as session:
        checking = await session.get(Account, 1)
        session.add(Account(
            id=7, customer_id=checking.customer_id, name="Credit", kind="credit",
            iban=make_tr_iban("7".zfill(16)), credit_limit_kurus=6_000_000,
        ))
        await session.commit()
    body = by_number("123456789", 5_000_001, "own-credit-number", from_id=7)
    first = await client.post("/transfers", headers=bank, json=body)
    assert first.status_code == 201, first.text
    assert first.json()["to_iban"] == mask_iban(make_tr_iban("1".zfill(16)))
    assert (await client.post("/transfers", headers=bank, json=body)).json() == first.json()


@pytest.mark.parametrize("original_by_number", [True, False])
async def test_cross_mode_replays_mask_only_number_requests(client, bank, original_by_number):
    number = by_number("987654321", 100, "cross-mode-privacy")
    iban = {k: v for k, v in number.items() if k != "to_customer_no"}
    iban["to_iban"] = ALI_CHECKING
    original = await client.post(
        "/transfers", headers=bank, json=number if original_by_number else iban
    )
    assert original.status_code == 201
    for body in (number, iban, number):
        response = await client.post("/transfers", headers=bank, json=body)
        assert response.status_code == 201
        assert response.json()["id"] == original.json()["id"]
        if "to_customer_no" in body:
            assert ALI_CHECKING not in response.text
            assert response.json()["to_iban"] == mask_iban(ALI_CHECKING)
        else:
            assert response.json()["to_iban"] == ALI_CHECKING
    accounts = (await client.get("/accounts", headers=bank)).json()
    assert accounts[0]["balance_kurus"] == 99_900


async def test_own_number_without_checking_is_not_payable(client, bank):
    token = (await login(client, "111222333", "246810")).json()["access_token"]
    response = await client.post(
        "/transfers", headers={"Authorization": f"Bearer {token}"},
        json=by_number("111222333", 1, "own-no-checking", from_id=6),
    )
    assert response.status_code == 404
