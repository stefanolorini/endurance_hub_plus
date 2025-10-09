"""baseline (empty)

Revision ID: 03406557077d
Revises: 4114232b46dc
Create Date: 2025-10-09 17:57:41.219243

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '03406557077d'
down_revision: Union[str, Sequence[str], None] = '4114232b46dc'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
