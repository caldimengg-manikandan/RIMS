"""Add stage enforcement flags

Revision ID: da1350f4c17c
Revises: 002_schema_alignment_cleanup
Create Date: 2026-03-03 11:32:40.664777

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'da1350f4c17c'
down_revision: Union[str, Sequence[str], None] = '002_schema_alignment_cleanup'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
