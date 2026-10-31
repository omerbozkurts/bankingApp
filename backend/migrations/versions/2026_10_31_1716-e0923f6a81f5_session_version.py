"""session version

Revision ID: e0923f6a81f5
Revises: 32e96e49c29c
Create Date: 2026-10-31 17:16:10.115330

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e0923f6a81f5'
down_revision: Union[str, Sequence[str], None] = '32e96e49c29c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Existing tokens carry no version and count as 0, so nobody is signed out by the upgrade.
    op.add_column(
        'customers',
        sa.Column('session_version', sa.Integer(), server_default='0', nullable=False),
    )


def downgrade() -> None:
    """Downgrade schema."""
    # Tokens revoked by a password change would work again until they expire (30 minutes).
    op.drop_column('customers', 'session_version')
