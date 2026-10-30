"""credit accounts

Revision ID: 99f8b363cc2b
Revises: 2af37c15ad57
Create Date: 2026-10-31 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '99f8b363cc2b'
down_revision: Union[str, Sequence[str], None] = '2af37c15ad57'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('accounts', sa.Column('credit_limit_kurus', sa.BigInteger(), nullable=True))
    op.drop_constraint(op.f('ck_accounts_balance_non_negative'), 'accounts', type_='check')
    op.drop_constraint(op.f('ck_accounts_kind_valid'), 'accounts', type_='check')
    op.create_check_constraint(
        op.f('ck_accounts_balance_within_limit'), 'accounts',
        'balance_kurus >= -COALESCE(credit_limit_kurus, 0)',
    )
    op.create_check_constraint(
        op.f('ck_accounts_kind_valid'), 'accounts', "kind IN ('checking', 'savings', 'credit')"
    )
    op.create_check_constraint(
        op.f('ck_accounts_credit_limit_iff_credit'), 'accounts',
        "(kind = 'credit') = (credit_limit_kurus IS NOT NULL)",
    )
    op.create_check_constraint(
        op.f('ck_accounts_credit_limit_positive'), 'accounts',
        'credit_limit_kurus IS NULL OR credit_limit_kurus > 0',
    )
    op.create_check_constraint(
        op.f('ck_accounts_credit_not_positive'), 'accounts', "kind <> 'credit' OR balance_kurus <= 0"
    )
    # The old schema allowed a goal on any account; as in 2af37c15ad57, an account with a goal is a
    # savings account. Converting keeps the goal instead of dropping customer data.
    op.execute("UPDATE accounts SET kind = 'savings' WHERE goal_kurus IS NOT NULL")
    op.create_check_constraint(
        op.f('ck_accounts_goal_only_savings'), 'accounts', "kind = 'savings' OR goal_kurus IS NULL"
    )
    # One credit account per customer, also enforced by the database.
    op.create_index(
        'uq_accounts_one_credit_per_customer', 'accounts', ['customer_id'], unique=True,
        postgresql_where=sa.text("kind = 'credit'"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    # Credit accounts (and their history) can't be represented in the old schema; refuse rather
    # than silently deleting money records.
    if op.get_bind().scalar(sa.text("SELECT count(*) FROM accounts WHERE kind = 'credit'")):
        raise RuntimeError('Credit accounts exist; remove them before downgrading.')
    op.drop_index('uq_accounts_one_credit_per_customer', table_name='accounts')
    for name in (
        'goal_only_savings', 'credit_not_positive', 'credit_limit_positive',
        'credit_limit_iff_credit', 'kind_valid', 'balance_within_limit',
    ):
        op.drop_constraint(op.f(f'ck_accounts_{name}'), 'accounts', type_='check')
    op.create_check_constraint(
        op.f('ck_accounts_kind_valid'), 'accounts', "kind IN ('checking', 'savings')"
    )
    op.create_check_constraint(
        op.f('ck_accounts_balance_non_negative'), 'accounts', 'balance_kurus >= 0'
    )
    op.drop_column('accounts', 'credit_limit_kurus')
