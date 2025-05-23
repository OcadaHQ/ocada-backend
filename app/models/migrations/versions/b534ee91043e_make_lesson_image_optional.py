"""Make lesson image optional

Revision ID: b534ee91043e
Revises: bd56b841b2c4
Create Date: 2023-04-10 10:44:36.789037

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b534ee91043e'
down_revision = 'bd56b841b2c4'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column('lessons', 'lesson_image',
               existing_type=sa.VARCHAR(),
               nullable=True)
    op.alter_column('quiz_answers', 'is_correct',
               existing_type=sa.INTEGER(),
               comment='',
               existing_nullable=False)
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column('quiz_answers', 'is_correct',
               existing_type=sa.INTEGER(),
               comment=None,
               existing_comment='',
               existing_nullable=False)
    op.alter_column('lessons', 'lesson_image',
               existing_type=sa.VARCHAR(),
               nullable=False)
    # ### end Alembic commands ###
