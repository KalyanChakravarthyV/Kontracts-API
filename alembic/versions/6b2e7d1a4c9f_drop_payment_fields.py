"""Drop payment fields from leases

Revision ID: 6b2e7d1a4c9f
Revises: 3a9d7c4e1b2f
Create Date: 2025-01-18 00:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "6b2e7d1a4c9f"
down_revision: Union[str, None] = "3a9d7c4e1b2f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    schema_name = op.get_context().config.get_main_option("schema_name", "kontracts")
    op.drop_column("leases", "next_payment", schema=schema_name)
    op.drop_column("leases", "payment_frequency", schema=schema_name)
    op.drop_column("leases", "periodic_payment", schema=schema_name)


def downgrade() -> None:
    schema_name = op.get_context().config.get_main_option("schema_name", "kontracts")
    op.add_column(
        "leases",
        sa.Column("periodic_payment", sa.Numeric(precision=15, scale=2), nullable=True),
        schema=schema_name,
    )
    op.add_column(
        "leases",
        sa.Column("payment_frequency", sa.String(), nullable=True),
        schema=schema_name,
    )
    op.add_column(
        "leases",
        sa.Column("next_payment", sa.DateTime(), nullable=True),
        schema=schema_name,
    )
    op.execute(
        f"""
        UPDATE {schema_name}.leases
        SET periodic_payment = 0
        WHERE periodic_payment IS NULL
        """
    )
    op.alter_column(
        "leases",
        "periodic_payment",
        existing_type=sa.Numeric(precision=15, scale=2),
        nullable=False,
        schema=schema_name,
    )
