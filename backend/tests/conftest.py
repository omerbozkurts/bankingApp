"""Test setup: runs against the separate `abbank_test` database (created by docker/initdb).

Environment variables are set before any `app` import so the engine binds to the test database.
"""

import os

os.environ["DATABASE_URL"] = os.environ.get(
    "TEST_DATABASE_URL", "postgresql+asyncpg://abbank:abbank_dev@localhost:5434/abbank_test"
)
os.environ["JWT_SECRET"] = "test-only-secret-" + "x" * 40

from collections.abc import AsyncIterator, Awaitable, Callable  # noqa: E402

import httpx  # noqa: E402
import pytest  # noqa: E402
from sqlalchemy import text  # noqa: E402

from app.db import SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402
from app.models import Account, Base, Customer  # noqa: E402
from app.routers.auth import login_limiter  # noqa: E402
from app.security import hash_password  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
async def prepare_database() -> AsyncIterator[None]:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.fixture(autouse=True)
async def clean_tables() -> None:
    async with engine.begin() as conn:
        await conn.execute(
            text("TRUNCATE transactions, accounts, customers RESTART IDENTITY CASCADE")
        )
    # Every test client uses the same IP, so start each test with a fresh login allowance.
    login_limiter.reset()


@pytest.fixture
async def client() -> AsyncIterator[httpx.AsyncClient]:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


CreateCustomer = Callable[..., Awaitable[Customer]]


@pytest.fixture
def create_customer() -> CreateCustomer:
    """Insert a customer with optional accounts: await create_customer("111111111", "654321")."""

    async def _create(
        customer_no: str = "123456789",
        password: str = "123456",
        full_name: str = "Test Müşteri",
        accounts: list[dict] | None = None,
    ) -> Customer:
        async with SessionLocal() as session:
            customer = Customer(
                customer_no=customer_no,
                full_name=full_name,
                password_hash=hash_password(password),
            )
            customer.accounts = [Account(**a) for a in (accounts or [])]
            session.add(customer)
            await session.commit()
            await session.refresh(customer)
            return customer

    return _create


async def login(
    client: httpx.AsyncClient, customer_no: str, password: str, *, web: bool = False
) -> httpx.Response:
    """Mobile-style login by default; web=True asks for the httpOnly session cookie instead."""
    headers = {"X-Session-Mode": "cookie", "X-Requested-With": "abbank"} if web else {}
    return await client.post(
        "/auth/login", json={"customer_no": customer_no, "password": password}, headers=headers
    )
