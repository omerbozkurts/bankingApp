"""saved recipients

Revision ID: 84650f1225ac
Revises: e0923f6a81f5
Create Date: 2026-10-31 17:40:31.810463

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '84650f1225ac'
down_revision: Union[str, Sequence[str], None] = 'e0923f6a81f5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('saved_recipients',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('customer_id', sa.Integer(), nullable=False),
    sa.Column('nickname', sa.String(length=40), nullable=False),
    sa.Column('iban', sa.String(length=34), nullable=True),
    sa.Column('customer_no', sa.String(length=9), nullable=True),
    sa.Column('masked_name', sa.String(length=120), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint('(iban IS NULL) <> (customer_no IS NULL)', name=op.f('ck_saved_recipients_one_target')),
    sa.ForeignKeyConstraint(['customer_id'], ['customers.id'], name=op.f('fk_saved_recipients_customer_id_customers')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_saved_recipients')),
    sa.UniqueConstraint('customer_id', 'customer_no', name='uq_saved_recipients_customer_no'),
    sa.UniqueConstraint('customer_id', 'iban', name='uq_saved_recipients_iban')
    )
    op.create_index(op.f('ix_saved_recipients_customer_id'), 'saved_recipients', ['customer_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_saved_recipients_customer_id'), table_name='saved_recipients')
    op.drop_table('saved_recipients')
