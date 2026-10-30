"""Exercise the real upgrade against rows allowed by the previous schema."""

import importlib.util
from pathlib import Path

from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import text

from app.db import engine


async def test_upgrade_turns_legacy_checking_account_with_goal_into_savings():
    path = (
        Path(__file__).parents[1] / "migrations" / "versions"
        / "2026_10_31_1000-99f8b363cc2b_credit_accounts.py"
    )
    spec = importlib.util.spec_from_file_location("credit_migration", path)
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)

    async with engine.connect() as connection:
        transaction = await connection.begin()
        try:
            # Shadow only accounts on this connection; never alter the application's tables.
            await connection.execute(text("""
                CREATE TEMP TABLE accounts (
                    id integer PRIMARY KEY,
                    customer_id integer NOT NULL,
                    kind varchar(20) NOT NULL,
                    balance_kurus bigint NOT NULL,
                    goal_kurus bigint,
                    CONSTRAINT ck_accounts_balance_non_negative CHECK (balance_kurus >= 0),
                    CONSTRAINT ck_accounts_kind_valid CHECK (kind IN ('checking', 'savings')),
                    CONSTRAINT ck_accounts_goal_positive
                        CHECK (goal_kurus IS NULL OR goal_kurus > 0)
                ) ON COMMIT DROP
            """))
            await connection.execute(text(
                "INSERT INTO accounts VALUES (1, 1, 'checking', 12345, 100000)"
            ))

            def upgrade(sync_connection):
                context = MigrationContext.configure(sync_connection)
                with Operations.context(context):
                    migration.upgrade()

            await connection.run_sync(upgrade)
            row = (await connection.execute(text(
                "SELECT kind, balance_kurus, goal_kurus, credit_limit_kurus"
                " FROM accounts WHERE id = 1"
            ))).one()
            assert tuple(row) == ("savings", 12345, 100000, None)
        finally:
            await transaction.rollback()
