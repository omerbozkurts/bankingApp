"""Admin panel: access rules, account freezing, login unlock and the audit log."""

import asyncio
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import update

from app.banking import make_tr_iban
from app.db import SessionLocal
from app.models import Customer
from app.routers import transfers
from scripts.make_admin import set_admin
from tests.conftest import login

REASON = {"reason": "Şüpheli işlem bildirimi"}


async def bearer(client, customer_no: str, password: str) -> dict[str, str]:
    token = (await login(client, customer_no, password)).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


async def make_admin(customer_no: str, value: bool = True) -> None:
    async with SessionLocal() as session:
        await session.execute(
            update(Customer).where(Customer.customer_no == customer_no).values(is_admin=value)
        )
        await session.commit()


@pytest.fixture
async def bank(client, create_customer):
    """Admin without accounts; Deniz: checking 1 (1.000 TL), savings 2; Ali: checking 3 (500 TL)."""
    await create_customer(customer_no="555555555", password="246810", full_name="Yönetici Bir")
    await make_admin("555555555")
    deniz = await create_customer(
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
    ali = await create_customer(
        customer_no="987654321",
        password="654321",
        full_name="Ali Kaya",
        accounts=[
            {
                "id": 3,
                "name": "Vadesiz",
                "iban": make_tr_iban("3".zfill(16)),
                "balance_kurus": 50_000,
            }
        ],
    )
    return {
        "admin": await bearer(client, "555555555", "246810"),
        "deniz": await bearer(client, "123456789", "123456"),
        "deniz_id": deniz.id,
        "ali_id": ali.id,
    }


def transfer(to_number: str, amount: int, key: str, from_id: int = 1) -> dict:
    return {
        "from_account_id": from_id,
        "to_iban": make_tr_iban(to_number.zfill(16)),
        "amount_kurus": amount,
        "idempotency_key": key,
    }


async def test_me_reports_admin_flag(client, bank):
    assert (await client.get("/me", headers=bank["admin"])).json()["is_admin"] is True
    assert (await client.get("/me", headers=bank["deniz"])).json()["is_admin"] is False


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("GET", "/admin/customers"),
        ("GET", "/admin/customers/2"),
        ("GET", "/admin/accounts/3/transactions"),
        ("POST", "/admin/accounts/3/freeze"),
        ("POST", "/admin/accounts/3/unfreeze"),
        ("POST", "/admin/customers/3/unlock"),
        ("GET", "/admin/actions"),
    ],
)
async def test_customers_cannot_use_admin_endpoints(client, bank, method, path):
    body = REASON if method == "POST" else None
    anonymous = await client.request(method, path, json=body)
    assert anonymous.status_code == 401
    customer = await client.request(method, path, json=body, headers=bank["deniz"])
    assert customer.status_code == 403


async def test_revoked_admin_loses_access_with_the_same_token(client, bank):
    assert (await client.get("/admin/customers", headers=bank["admin"])).status_code == 200
    await make_admin("555555555", False)
    assert (await client.get("/admin/customers", headers=bank["admin"])).status_code == 403


async def test_search_customers(client, bank):
    everyone = (await client.get("/admin/customers", headers=bank["admin"])).json()
    assert [c["customer_no"] for c in everyone["items"]] == ["987654321", "123456789", "555555555"]
    deniz = everyone["items"][1]
    assert deniz["account_count"] == 2 and deniz["locked"] is False

    by_number = await client.get("/admin/customers?q=9876", headers=bank["admin"])
    assert [c["full_name"] for c in by_number.json()["items"]] == ["Ali Kaya"]
    by_name = await client.get("/admin/customers?q=yıl", headers=bank["admin"])
    assert [c["full_name"] for c in by_name.json()["items"]] == ["Deniz Yılmaz"]
    # LIKE wildcards are matched literally.
    wildcard = await client.get("/admin/customers?q=%25", headers=bank["admin"])
    assert wildcard.json()["items"] == []


async def test_customer_list_pages(client, bank):
    first = (await client.get("/admin/customers?limit=2", headers=bank["admin"])).json()
    assert len(first["items"]) == 2 and first["next_before_id"] is not None
    rest = await client.get(
        f"/admin/customers?limit=2&before_id={first['next_before_id']}", headers=bank["admin"]
    )
    assert [c["customer_no"] for c in rest.json()["items"]] == ["555555555"]
    assert rest.json()["next_before_id"] is None


async def test_customer_detail_and_transactions(client, bank):
    sent = await client.post(
        "/transfers", headers=bank["deniz"], json=transfer("3", 2_500, "detail-1")
    )
    assert sent.status_code == 201
    detail = await client.get(f"/admin/customers/{bank['deniz_id']}", headers=bank["admin"])
    assert detail.status_code == 200
    accounts = detail.json()["accounts"]
    assert [(a["id"], a["balance_kurus"], a["frozen"]) for a in accounts] == [
        (1, 97_500, False),
        (2, 0, False),
    ]
    history = await client.get("/admin/accounts/1/transactions", headers=bank["admin"])
    assert [t["amount_kurus"] for t in history.json()["items"]] == [-2_500]
    assert (await client.get("/admin/customers/999", headers=bank["admin"])).status_code == 404
    missing = await client.get("/admin/accounts/999/transactions", headers=bank["admin"])
    assert missing.status_code == 404


async def test_frozen_account_cannot_send_but_still_receives(client, bank):
    frozen = await client.post("/admin/accounts/1/freeze", headers=bank["admin"], json=REASON)
    assert frozen.status_code == 200 and frozen.json()["frozen"] is True
    # The customer sees the freeze on their own accounts.
    mine = (await client.get("/accounts", headers=bank["deniz"])).json()
    assert [a["frozen"] for a in mine] == [True, False]

    out = await client.post(
        "/transfers", headers=bank["deniz"], json=transfer("3", 100, "freeze-1")
    )
    assert out.status_code == 400 and "dondurulmuş" in out.json()["detail"]
    # Moving money to an own account is money leaving the frozen account too.
    own = await client.post(
        "/transfers", headers=bank["deniz"], json=transfer("2", 100, "freeze-2")
    )
    assert own.status_code == 400

    ali = await bearer(client, "987654321", "654321")
    incoming = await client.post("/transfers", headers=ali, json=transfer("1", 300, "freeze-3", 3))
    assert incoming.status_code == 201, incoming.text

    unfrozen = await client.post("/admin/accounts/1/unfreeze", headers=bank["admin"], json=REASON)
    assert unfrozen.json()["frozen"] is False
    again = await client.post(
        "/transfers", headers=bank["deniz"], json=transfer("3", 100, "freeze-1")
    )
    assert again.status_code == 201
    assert again.json()["from_balance_after_kurus"] == 100_000 + 300 - 100


async def test_freeze_state_conflicts(client, bank):
    path = "/admin/accounts/3"
    assert (
        await client.post(f"{path}/unfreeze", headers=bank["admin"], json=REASON)
    ).status_code == 409
    assert (
        await client.post(f"{path}/freeze", headers=bank["admin"], json=REASON)
    ).status_code == 200
    assert (
        await client.post(f"{path}/freeze", headers=bank["admin"], json=REASON)
    ).status_code == 409
    missing = await client.post("/admin/accounts/999/freeze", headers=bank["admin"], json=REASON)
    assert missing.status_code == 404


@pytest.mark.parametrize("reason", ["", "  ", "ab", "x" * 201])
async def test_actions_need_a_reason(client, bank, reason):
    response = await client.post(
        "/admin/accounts/3/freeze", headers=bank["admin"], json={"reason": reason}
    )
    assert response.status_code == 422
    log = (await client.get("/admin/actions", headers=bank["admin"])).json()
    assert log["items"] == []


async def test_admin_cannot_act_on_own_record(client, bank):
    await make_admin("123456789")
    # Deniz is now an admin too: their own accounts and login are off limits to themselves.
    own = await client.post("/admin/accounts/1/freeze", headers=bank["deniz"], json=REASON)
    assert own.status_code == 403
    unlock = await client.post(
        f"/admin/customers/{bank['deniz_id']}/unlock", headers=bank["deniz"], json=REASON
    )
    assert unlock.status_code == 403
    # Another admin can.
    other = await client.post("/admin/accounts/1/freeze", headers=bank["admin"], json=REASON)
    assert other.status_code == 200


async def test_unlock_customer(client, bank):
    path = f"/admin/customers/{bank['ali_id']}/unlock"
    assert (await client.post(path, headers=bank["admin"], json=REASON)).status_code == 409

    for _ in range(5):
        await login(client, "987654321", "000000")
    assert (await login(client, "987654321", "654321")).status_code == 401
    listed = await client.get("/admin/customers?q=987654321", headers=bank["admin"])
    assert listed.json()["items"][0]["locked"] is True

    unlocked = await client.post(path, headers=bank["admin"], json=REASON)
    assert unlocked.status_code == 200 and unlocked.json()["locked"] is False
    assert (await login(client, "987654321", "654321")).status_code == 200


async def test_expired_lock_is_not_locked(client, bank):
    async with SessionLocal() as session:
        await session.execute(
            update(Customer)
            .where(Customer.id == bank["ali_id"])
            .values(locked_until=datetime.now(UTC) - timedelta(minutes=1))
        )
        await session.commit()
    path = f"/admin/customers/{bank['ali_id']}/unlock"
    assert (await client.post(path, headers=bank["admin"], json=REASON)).status_code == 409


async def test_audit_log_records_every_change(client, bank):
    await client.post("/admin/accounts/3/freeze", headers=bank["admin"], json=REASON)
    await client.post(
        "/admin/accounts/3/unfreeze", headers=bank["admin"], json={"reason": "  Doğrulandı  "}
    )
    # A refused change leaves no entry.
    await client.post("/admin/accounts/3/unfreeze", headers=bank["admin"], json=REASON)

    log = (await client.get("/admin/actions", headers=bank["admin"])).json()
    assert [(a["action"], a["reason"]) for a in log["items"]] == [
        ("unfreeze_account", "Doğrulandı"),
        ("freeze_account", "Şüpheli işlem bildirimi"),
    ]
    entry = log["items"][0]
    assert entry["admin_customer_no"] == "555555555"
    assert entry["customer_no"] == "987654321" and entry["account_id"] == 3

    page = (await client.get("/admin/actions?limit=1", headers=bank["admin"])).json()
    older = await client.get(
        f"/admin/actions?limit=1&before_id={page['next_before_id']}", headers=bank["admin"]
    )
    assert [a["action"] for a in older.json()["items"]] == ["freeze_account"]


async def test_freeze_racing_a_transfer_serialises_without_deadlock(client, bank, monkeypatch):
    """The transfer holds the customer lock and has read the account when the freeze arrives."""
    read = asyncio.Event()
    resume = asyncio.Event()
    original = transfers.get_owned_account

    async def paused_read(*args, **kwargs):
        account = await original(*args, **kwargs)
        read.set()
        await asyncio.wait_for(resume.wait(), timeout=20)
        return account

    monkeypatch.setattr(transfers, "get_owned_account", paused_read)
    sending = asyncio.create_task(
        client.post("/transfers", headers=bank["deniz"], json=transfer("3", 100, "freeze-race-1"))
    )
    await asyncio.wait_for(read.wait(), timeout=10)
    freezing = asyncio.create_task(
        client.post("/admin/accounts/1/freeze", headers=bank["admin"], json=REASON)
    )
    # Let the freeze reach its first lock before the transfer continues.
    await asyncio.sleep(0.5)
    resume.set()
    sent, frozen = await asyncio.wait_for(asyncio.gather(sending, freezing), timeout=20)

    assert frozen.status_code == 200, frozen.text
    # The transfer got its locks first, so it completes; the freeze waits for it.
    assert sent.status_code == 201, sent.text
    detail = (
        await client.get(f"/admin/customers/{bank['deniz_id']}", headers=bank["admin"])
    ).json()
    assert detail["accounts"][0]["balance_kurus"] == 99_900
    assert detail["accounts"][0]["frozen"] is True
    after = await client.post("/transfers", headers=bank["deniz"], json=transfer("3", 1, "after-freeze-1"))
    assert after.status_code == 400


async def test_freeze_racing_the_admins_own_transfer(client, bank, create_customer, monkeypatch):
    """The audit row needs the admin's customer row, which the admin's own transfer holds."""
    await create_customer(
        customer_no="444444444",
        password="135790",
        accounts=[
            {
                "id": 9,
                "name": "Vadesiz",
                "iban": make_tr_iban("9".zfill(16)),
                "balance_kurus": 5_000,
            }
        ],
    )
    await make_admin("444444444")
    other_admin = await bearer(client, "444444444", "135790")
    read = asyncio.Event()
    resume = asyncio.Event()
    original = transfers.get_owned_account

    async def paused_read(*args, **kwargs):
        account = await original(*args, **kwargs)
        read.set()
        await asyncio.wait_for(resume.wait(), timeout=20)
        return account

    monkeypatch.setattr(transfers, "get_owned_account", paused_read)
    sending = asyncio.create_task(
        client.post("/transfers", headers=other_admin, json=transfer("3", 100, "race-own-1", 9))
    )
    await asyncio.wait_for(read.wait(), timeout=10)
    freezing = asyncio.create_task(
        client.post("/admin/accounts/3/freeze", headers=other_admin, json=REASON)
    )
    await asyncio.sleep(0.5)
    resume.set()
    sent, frozen = await asyncio.wait_for(asyncio.gather(sending, freezing), timeout=20)
    assert (sent.status_code, frozen.status_code) == (201, 200)


async def test_concurrent_freezes_create_only_one_audit_entry(client, bank):
    responses = await asyncio.gather(
        client.post("/admin/accounts/1/freeze", headers=bank["admin"], json=REASON),
        client.post("/admin/accounts/1/freeze", headers=bank["admin"], json=REASON),
    )
    assert sorted(r.status_code for r in responses) == [200, 409]
    log = (await client.get("/admin/actions", headers=bank["admin"])).json()
    assert [a["action"] for a in log["items"]] == ["freeze_account"]


async def test_unlock_is_audited(client, bank):
    for _ in range(5):
        await login(client, "987654321", "000000")
    response = await client.post(
        f"/admin/customers/{bank['ali_id']}/unlock", headers=bank["admin"], json=REASON
    )
    assert response.status_code == 200
    log = (await client.get("/admin/actions", headers=bank["admin"])).json()
    assert len(log["items"]) == 1
    entry = log["items"][0]
    assert entry["action"] == "unlock_customer"
    assert entry["admin_customer_no"] == "555555555"
    assert entry["customer_no"] == "987654321"
    assert entry["account_id"] is None
    assert entry["reason"] == REASON["reason"]


async def test_granting_admin_rights_is_audited(client, bank):
    message = await set_admin("987654321", True, "Operasyon ekibine katıldı")
    assert message.endswith("verildi.")
    assert (await set_admin("987654321", True, "Tekrar")).endswith("zaten yönetici.")
    assert (await set_admin("000000000", True, "Yok")).endswith("müşteri yok.")
    await set_admin("987654321", False, "Ekipten ayrıldı")

    log = (await client.get("/admin/actions", headers=bank["admin"])).json()
    assert [(a["action"], a["admin_customer_no"], a["customer_no"]) for a in log["items"]] == [
        ("revoke_admin", None, "987654321"),
        ("grant_admin", None, "987654321"),
    ]
