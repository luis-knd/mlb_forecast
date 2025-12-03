"""Remove unused game fields innings_played attendance weather_conditions

Revision ID: e2fac52e98be
Revises: ef4e8c0a62ce
Create Date: 2025-07-22 17:21:22.219560

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "e2fac52e98be"
down_revision = "ef4e8c0a62ce"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Remove unused columns from games table
    op.drop_column("games", "innings_played")
    op.drop_column("games", "attendance")
    op.drop_column("games", "weather_conditions")


def downgrade() -> None:
    # Add back the columns in case we need to rollback
    op.add_column("games", sa.Column("weather_conditions", sa.JSON(), nullable=True))
    op.add_column("games", sa.Column("attendance", sa.Integer(), nullable=True))
    op.add_column("games", sa.Column("innings_played", sa.Integer(), nullable=True))
