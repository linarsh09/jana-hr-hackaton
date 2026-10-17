"""Convert legacy admin accounts to HR.

Revision ID: c45f0d91a2e7
Revises: b610c2d9a241
Create Date: 2026-10-17
"""
from alembic import op


revision = "c45f0d91a2e7"
down_revision = "b610c2d9a241"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("UPDATE users SET role = 'HR' WHERE role = 'ADMIN'")


def downgrade():
    # Keep normalized roles as HR; converting every HR account back to admin
    # would incorrectly change accounts that were already HR before upgrade.
    pass
