"""Add Academy course and lesson catalog."""
from alembic import op
import sqlalchemy as sa

revision = "a10c20261017"
down_revision = "b610c2d9a241"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "academy_courses",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
    )
    op.create_table(
        "academy_lessons",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("course_id", sa.Integer(), sa.ForeignKey("academy_courses.id"), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.UniqueConstraint("course_id", "position", name="uq_academy_lesson_position"),
        sa.CheckConstraint("position > 0", name="ck_academy_lesson_position"),
    )


def downgrade():
    op.drop_table("academy_lessons")
    op.drop_table("academy_courses")
