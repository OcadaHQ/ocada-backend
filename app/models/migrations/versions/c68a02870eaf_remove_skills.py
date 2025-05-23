"""remove skills

Revision ID: c68a02870eaf
Revises: bfc8dac7d9fd
Create Date: 2023-04-08 07:59:49.262782

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'c68a02870eaf'
down_revision = 'bfc8dac7d9fd'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('user_quiz_attempts')
    op.drop_table('quiz_answers')
    op.drop_table('quiz_questions')

    op.drop_table('user_skills')
    op.drop_table('skills')
    op.drop_table('skill_groups')

    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('user_skills',
    sa.Column('user_id', sa.INTEGER(), autoincrement=False, nullable=False),
    sa.Column('skill_id', sa.INTEGER(), autoincrement=False, nullable=False),
    sa.Column('date_discovered', postgresql.TIMESTAMP(timezone=True), server_default=sa.text('now()'), autoincrement=False, nullable=True),
    sa.Column('date_last_started_quiz', postgresql.TIMESTAMP(timezone=True), autoincrement=False, nullable=True),
    sa.Column('date_last_unlocked', postgresql.TIMESTAMP(timezone=True), autoincrement=False, nullable=True),
    sa.Column('date_last_updated', postgresql.TIMESTAMP(timezone=True), server_default=sa.text('now()'), autoincrement=False, nullable=False),
    sa.ForeignKeyConstraint(['skill_id'], ['skills.id'], name='user_skills_skill_id_fkey'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], name='user_skills_user_id_fkey'),
    sa.PrimaryKeyConstraint('user_id', 'skill_id', name='user_skills_pkey')
    )
    op.create_table('user_quiz_attempts',
    sa.Column('id', sa.INTEGER(), autoincrement=True, nullable=False),
    sa.Column('user_id', sa.INTEGER(), autoincrement=False, nullable=True),
    sa.Column('question_id', sa.INTEGER(), autoincrement=False, nullable=True),
    sa.Column('answer_id', sa.INTEGER(), autoincrement=False, nullable=True),
    sa.Column('date_created', postgresql.TIMESTAMP(timezone=True), server_default=sa.text('now()'), autoincrement=False, nullable=False),
    sa.Column('date_last_updated', postgresql.TIMESTAMP(timezone=True), server_default=sa.text('now()'), autoincrement=False, nullable=False),
    sa.ForeignKeyConstraint(['answer_id'], ['quiz_answers.id'], name='user_quiz_attempts_answer_id_fkey'),
    sa.ForeignKeyConstraint(['question_id'], ['quiz_questions.id'], name='user_quiz_attempts_question_id_fkey'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], name='user_quiz_attempts_user_id_fkey'),
    sa.PrimaryKeyConstraint('id', name='user_quiz_attempts_pkey')
    )
    op.create_table('quiz_answers',
    sa.Column('id', sa.INTEGER(), autoincrement=True, nullable=False),
    sa.Column('question_id', sa.INTEGER(), autoincrement=False, nullable=True),
    sa.Column('answer_text', sa.VARCHAR(), autoincrement=False, nullable=False),
    sa.Column('is_correct', sa.INTEGER(), autoincrement=False, nullable=False),
    sa.Column('date_created', postgresql.TIMESTAMP(timezone=True), server_default=sa.text('now()'), autoincrement=False, nullable=False),
    sa.Column('date_last_updated', postgresql.TIMESTAMP(timezone=True), server_default=sa.text('now()'), autoincrement=False, nullable=False),
    sa.ForeignKeyConstraint(['question_id'], ['quiz_questions.id'], name='quiz_answers_question_id_fkey'),
    sa.PrimaryKeyConstraint('id', name='quiz_answers_pkey')
    )
    op.create_table('quiz_questions',
    sa.Column('id', sa.INTEGER(), autoincrement=True, nullable=False),
    sa.Column('skill_id', sa.INTEGER(), autoincrement=False, nullable=True),
    sa.Column('question', sa.VARCHAR(), autoincrement=False, nullable=False),
    sa.Column('date_created', postgresql.TIMESTAMP(timezone=True), server_default=sa.text('now()'), autoincrement=False, nullable=False),
    sa.Column('date_last_updated', postgresql.TIMESTAMP(timezone=True), server_default=sa.text('now()'), autoincrement=False, nullable=False),
    sa.ForeignKeyConstraint(['skill_id'], ['skills.id'], name='quiz_questions_skill_id_fkey'),
    sa.PrimaryKeyConstraint('id', name='quiz_questions_pkey')
    )
    op.create_table('skills',
    sa.Column('id', sa.INTEGER(), autoincrement=True, nullable=False),
    sa.Column('skill_key', sa.VARCHAR(), autoincrement=False, nullable=False),
    sa.Column('skill_group_id', sa.INTEGER(), autoincrement=False, nullable=False),
    sa.Column('description', sa.VARCHAR(), autoincrement=False, nullable=False),
    sa.Column('is_discoverable', sa.INTEGER(), autoincrement=False, nullable=False, comment='1 if skill can be discovered for learning by the user, 0 only by the system'),
    sa.Column('expiration_days', sa.INTEGER(), autoincrement=False, nullable=False, comment='Days until the skill expires and needs a refresher, 0 if does not expire'),
    sa.Column('is_active', sa.INTEGER(), autoincrement=False, nullable=False),
    sa.Column('date_created', postgresql.TIMESTAMP(timezone=True), server_default=sa.text('now()'), autoincrement=False, nullable=False),
    sa.Column('date_last_updated', postgresql.TIMESTAMP(timezone=True), server_default=sa.text('now()'), autoincrement=False, nullable=False),
    sa.ForeignKeyConstraint(['skill_group_id'], ['skill_groups.id'], name='skills_skill_group_id_fkey'),
    sa.PrimaryKeyConstraint('id', name='skills_pkey'),
    sa.UniqueConstraint('skill_key', name='skills_skill_key_key')
    )
    op.create_table('skill_groups',
    sa.Column('id', sa.INTEGER(), autoincrement=True, nullable=False),
    sa.Column('group_key', sa.VARCHAR(), autoincrement=False, nullable=False),
    sa.Column('description', sa.VARCHAR(), autoincrement=False, nullable=False),
    sa.Column('date_created', postgresql.TIMESTAMP(timezone=True), server_default=sa.text('now()'), autoincrement=False, nullable=False),
    sa.Column('date_last_updated', postgresql.TIMESTAMP(timezone=True), server_default=sa.text('now()'), autoincrement=False, nullable=False),
    sa.PrimaryKeyConstraint('id', name='skill_groups_pkey'),
    sa.UniqueConstraint('group_key', name='skill_groups_group_key_key')
    )
    # ### end Alembic commands ###
