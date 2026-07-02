"""add steam account-sync columns (Epic 30)

Link a Slate account to a Steam identity (``users.steam_id``, a unique SteamID64)
and record all-time Steam playtime on each imported library row
(``library_entries.steam_playtime_minutes``). Both columns are nullable — most
rows are not Steam-synced — and ``steam_id`` is unique so one Steam identity maps
to at most one account.

Revision ID: c3a9f1e7b204
Revises: b2f8a1c3d4e5
Create Date: 2026-07-02 09:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c3a9f1e7b204"
down_revision: str | Sequence[str] | None = "b2f8a1c3d4e5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add ``users.steam_id`` and ``library_entries.steam_playtime_minutes``."""
    op.add_column("users", sa.Column("steam_id", sa.String(), nullable=True))
    op.create_unique_constraint("uq_users_steam_id", "users", ["steam_id"])
    op.add_column(
        "library_entries",
        sa.Column("steam_playtime_minutes", sa.BigInteger(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("library_entries", "steam_playtime_minutes")
    op.drop_constraint("uq_users_steam_id", "users", type_="unique")
    op.drop_column("users", "steam_id")
