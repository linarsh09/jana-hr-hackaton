"""Course final quizzes and scored attempts."""
from alembic import op
import sqlalchemy as sa

revision = 'a13c20261017'
down_revision = 'a12c20261017'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('academy_quiz_questions',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('course_id', sa.Integer(), sa.ForeignKey('academy_courses.id'), nullable=False),
        sa.Column('position', sa.Integer(), nullable=False),
        sa.Column('text', sa.Text(), nullable=False),
        sa.Column('options', sa.JSON(), nullable=False),
        sa.Column('correct_option', sa.Integer(), nullable=False),
        sa.UniqueConstraint('course_id', 'position', name='uq_academy_question_position'))
    op.create_index('ix_academy_quiz_questions_course_id', 'academy_quiz_questions', ['course_id'])
    op.create_table('academy_quiz_attempts',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('course_id', sa.Integer(), sa.ForeignKey('academy_courses.id'), nullable=False),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('submission_id', sa.String(64), nullable=False, unique=True),
        sa.Column('correct_count', sa.Integer(), nullable=False),
        sa.Column('question_count', sa.Integer(), nullable=False),
        sa.Column('score_percent', sa.Integer(), nullable=False),
        sa.Column('passed', sa.Boolean(), nullable=False),
        sa.Column('submitted_at', sa.DateTime(), nullable=False))
    op.create_index('ix_academy_attempt_user_course', 'academy_quiz_attempts', ['user_id', 'course_id'])


def downgrade():
    op.drop_table('academy_quiz_attempts')
    op.drop_table('academy_quiz_questions')
