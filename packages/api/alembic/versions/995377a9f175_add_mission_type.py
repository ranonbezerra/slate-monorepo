"""add_mission_type

Revision ID: 995377a9f175
Revises: b8d4e2f3a561
Create Date: 2026-06-20 18:56:02.503054

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "995377a9f175"
down_revision: str | Sequence[str] | None = "b8d4e2f3a561"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("loadouts", sa.Column("context", sa.String(length=120), nullable=True))
    op.add_column(
        "missions",
        sa.Column("mission_type", sa.String(), server_default="regular", nullable=False),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("missions", "mission_type")
    op.drop_column("loadouts", "context")
