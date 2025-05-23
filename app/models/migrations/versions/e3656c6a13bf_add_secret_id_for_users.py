"""add secret_id for users

Revision ID: e3656c6a13bf
Revises: dbb5d9b69a9a
Create Date: 2022-12-29 17:36:01.918807

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'e3656c6a13bf'
down_revision = 'dbb5d9b69a9a'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column('quiz_answers', 'is_correct',
               existing_type=sa.INTEGER(),
               comment='',
               existing_nullable=False)
    op.alter_column('skill_groups', 'group_key',
               existing_type=sa.VARCHAR(),
               comment='',
               existing_nullable=False)
    op.add_column('users', sa.Column('secret_id', sa.String(), server_default='user', nullable=False, comment='to be used by revenuecat'))
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('users', 'secret_id')
    op.alter_column('skill_groups', 'group_key',
               existing_type=sa.VARCHAR(),
               comment=None,
               existing_comment='',
               existing_nullable=False)
    op.alter_column('quiz_answers', 'is_correct',
               existing_type=sa.INTEGER(),
               comment=None,
               existing_comment='',
               existing_nullable=False)
    # ### end Alembic commands ###
