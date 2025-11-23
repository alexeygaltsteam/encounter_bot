"""merge heads: notifications and image_url branch

Revision ID: b89335dbb65d
Revises: f3a7b2c1d4e5, 9e5a62ea4a2b
Create Date: 2025-11-23 16:10:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b89335dbb65d'
down_revision: Union[str, None] = ('f3a7b2c1d4e5', '9e5a62ea4a2b')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
