"""admin panel

Revision ID: 32e96e49c29c
Revises: 99f8b363cc2b
Create Date: 2026-10-31 15:13:06.751199

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '32e96e49c29c'
down_revision: Union[str, Sequence[str], None] = '99f8b363cc2b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('admin_actions',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('admin_id', sa.Integer(), nullable=True),
    sa.Column('action', sa.String(length=32), nullable=False),
    sa.Column('customer_id', sa.Integer(), nullable=False),
    sa.Column('account_id', sa.Integer(), nullable=True),
    sa.Column('reason', sa.String(length=200), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint(
        "action IN ('freeze_account', 'unfreeze_account', 'unlock_customer', 'grant_admin', "
        "'revoke_admin')",
        name=op.f('ck_admin_actions_action_valid'),
    ),
    sa.ForeignKeyConstraint(['account_id'], ['accounts.id'], name=op.f('fk_admin_actions_account_id_accounts')),
    sa.ForeignKeyConstraint(['admin_id'], ['customers.id'], name=op.f('fk_admin_actions_admin_id_customers')),
    sa.ForeignKeyConstraint(['customer_id'], ['customers.id'], name=op.f('fk_admin_actions_customer_id_customers')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_admin_actions'))
    )
    op.create_index(op.f('ix_admin_actions_admin_id'), 'admin_actions', ['admin_id'], unique=False)
    op.create_index(op.f('ix_admin_actions_created_at'), 'admin_actions', ['created_at'], unique=False)
    op.create_index(op.f('ix_admin_actions_customer_id'), 'admin_actions', ['customer_id'], unique=False)
    op.add_column('accounts', sa.Column('frozen_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column(
        'customers', sa.Column('is_admin', sa.Boolean(), server_default='false', nullable=False)
    )


def downgrade() -> None:
    """Downgrade schema."""
    # Dropping these would silently unfreeze accounts and erase the audit log; refuse instead.
    bind = op.get_bind()
    if bind.scalar(sa.text("SELECT count(*) FROM accounts WHERE frozen_at IS NOT NULL")):
        raise RuntimeError('Frozen accounts exist; unfreeze them before downgrading.')
    if bind.scalar(sa.text("SELECT count(*) FROM admin_actions")):
        raise RuntimeError('The admin audit log is not empty; archive it before downgrading.')
    op.drop_column('customers', 'is_admin')
    op.drop_column('accounts', 'frozen_at')
    op.drop_index(op.f('ix_admin_actions_customer_id'), table_name='admin_actions')
    op.drop_index(op.f('ix_admin_actions_created_at'), table_name='admin_actions')
    op.drop_index(op.f('ix_admin_actions_admin_id'), table_name='admin_actions')
    op.drop_table('admin_actions')
