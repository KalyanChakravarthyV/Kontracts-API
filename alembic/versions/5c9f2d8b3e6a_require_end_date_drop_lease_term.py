"""Require end date and drop lease term

Revision ID: 5c9f2d8b3e6a
Revises: 2f4a9f2c5b1e
Create Date: 2025-01-18 00:10:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "5c9f2d8b3e6a"
down_revision: Union[str, None] = "2f4a9f2c5b1e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    schema_name = op.get_context().config.get_main_option("schema_name", "kontracts")

    op.execute(
        f"""
        UPDATE {schema_name}.leases
        SET end_date = commencement_date + (lease_term_months || ' months')::interval
        WHERE end_date IS NULL AND lease_term_months IS NOT NULL
        """
    )

    op.alter_column(
        "leases",
        "end_date",
        existing_type=sa.Date(),
        nullable=False,
        schema=schema_name,
    )
    op.drop_column("leases", "lease_term_months", schema=schema_name)


def downgrade() -> None:
    schema_name = op.get_context().config.get_main_option("schema_name", "kontracts")

    op.add_column(
        "leases",
        sa.Column("lease_term_months", sa.Integer(), nullable=True),
        schema=schema_name,
    )
    op.execute(
        f"""
        UPDATE {schema_name}.leases
        SET lease_term_months = (
            date_part('year', age(end_date, commencement_date)) * 12
            + date_part('month', age(end_date, commencement_date))
            + CASE WHEN date_part('day', age(end_date, commencement_date)) > 0 THEN 1 ELSE 0 END
        )::int
        WHERE lease_term_months IS NULL AND end_date IS NOT NULL
        """
    )
    op.alter_column(
        "leases",
        "lease_term_months",
        existing_type=sa.Integer(),
        nullable=False,
        schema=schema_name,
    )
    op.alter_column(
        "leases",
        "end_date",
        existing_type=sa.Date(),
        nullable=True,
        schema=schema_name,
    )
