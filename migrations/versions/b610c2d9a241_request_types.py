"""Add general employee request types.

Revision ID: b610c2d9a241
Revises: f41071fcd162
Create Date: 2026-10-17
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "b610c2d9a241"
down_revision = "f41071fcd162"
branch_labels = None
depends_on = None


def upgrade():
    request_type = postgresql.ENUM(
        "VACATION", "SICK_LEAVE", "CERTIFICATE", "OTHER",
        name="request_type",
        create_type=False,
    )
    request_type.create(op.get_bind(), checkfirst=True)
    op.add_column(
        "vacation_requests",
        sa.Column("request_type", request_type, nullable=False, server_default="VACATION"),
    )
    op.alter_column("vacation_requests", "request_type", server_default=None)
    op.alter_column("vacation_requests", "start_date", existing_type=sa.Date(), nullable=True)
    op.alter_column("vacation_requests", "end_date", existing_type=sa.Date(), nullable=True)


def downgrade():
    op.execute(
        "UPDATE vacation_requests "
        "SET start_date = COALESCE(start_date, created_at::date), "
        "end_date = COALESCE(end_date, created_at::date) "
        "WHERE start_date IS NULL OR end_date IS NULL"
    )
    op.alter_column("vacation_requests", "end_date", existing_type=sa.Date(), nullable=False)
    op.alter_column("vacation_requests", "start_date", existing_type=sa.Date(), nullable=False)
    op.drop_column("vacation_requests", "request_type")
    postgresql.ENUM(
        "VACATION", "SICK_LEAVE", "CERTIFICATE", "OTHER",
        name="request_type",
        create_type=False,
    ).drop(op.get_bind(), checkfirst=True)
