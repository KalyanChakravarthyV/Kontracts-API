"""Add lease end date

Revision ID: 2f4a9f2c5b1e
Revises: 7a1e9f772ecc
Create Date: 2025-01-18 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "2f4a9f2c5b1e"
down_revision: Union[str, None] = "7a1e9f772ecc"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    schema_name = op.get_context().config.get_main_option("schema_name", "kontracts")
    op.add_column(
        "leases",
        sa.Column("end_date", sa.Date(), nullable=True),
        schema=schema_name,
    )


def downgrade() -> None:
    schema_name = op.get_context().config.get_main_option("schema_name", "kontracts")
    op.drop_column("leases", "end_date", schema=schema_name)
