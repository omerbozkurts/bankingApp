from tests.conftest import login


async def test_health(client):
    r = await client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


async def test_login_and_me(client, create_customer):
    await create_customer()
    r = await login(client, "123456789", "123456")
    assert r.status_code == 200
    token = r.json()["access_token"]
    me = await client.get("/me", headers={"Authorization": f"Bearer {token}"})
    assert me.json()["customer_no"] == "123456789"
