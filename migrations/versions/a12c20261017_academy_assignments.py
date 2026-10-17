"""Assign Academy courses to employee profiles."""
from alembic import op
import sqlalchemy as sa

revision = "a12c20261017"
down_revision = "a11c20261017"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("academy_course_assignments",
        sa.Column("employee_id", sa.Integer(), sa.ForeignKey("employees.id"), primary_key=True),
        sa.Column("course_id", sa.Integer(), sa.ForeignKey("academy_courses.id"), primary_key=True),
        sa.Column("assigned_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("assigned_at", sa.DateTime(), nullable=False))


def downgrade():
    op.drop_table("academy_course_assignments")
