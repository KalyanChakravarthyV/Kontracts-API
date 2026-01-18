"""Require incremental borrowing rate

Revision ID: 3a9d7c4e1b2f
Revises: 5c9f2d8b3e6a
Create Date: 2025-01-18 00:20:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "3a9d7c4e1b2f"
down_revision: Union[str, None] = "5c9f2d8b3e6a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    schema_name = op.get_context().config.get_main_option("schema_name", "kontracts")
    op.execute(
        f"""
        UPDATE {schema_name}.leases
        SET incremental_borrowing_rate = 0
        WHERE incremental_borrowing_rate IS NULL
        """
    )
    op.alter_column(
        "leases",
        "incremental_borrowing_rate",
        existing_type=sa.Numeric(8, 6),
        nullable=False,
        schema=schema_name,
    )


def downgrade() -> None:
    schema_name = op.get_context().config.get_main_option("schema_name", "kontracts")
    op.alter_column(
        "leases",
        "incremental_borrowing_rate",
        existing_type=sa.Numeric(8, 6),
        nullable=True,
        schema=schema_name,
    )
