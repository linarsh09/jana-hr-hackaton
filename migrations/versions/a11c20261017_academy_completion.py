"""Store each user's completed lessons."""
from alembic import op
import sqlalchemy as sa

revision = "a11c20261017"
down_revision = "a10c20261017"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("academy_lesson_completions",
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), primary_key=True),
        sa.Column("lesson_id", sa.Integer(), sa.ForeignKey("academy_lessons.id"), primary_key=True),
        sa.Column("completed_at", sa.DateTime(), nullable=False))


def downgrade():
    op.drop_table("academy_lesson_completions")
