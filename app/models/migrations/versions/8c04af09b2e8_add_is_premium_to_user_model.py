"""Add is_premium to user model

Revision ID: 8c04af09b2e8
Revises: b534ee91043e
Create Date: 2023-05-10 07:49:16.850841

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '8c04af09b2e8'
down_revision = 'b534ee91043e'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('users', sa.Column('is_premium', sa.Integer(), server_default='0', nullable=False))
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('users', 'is_premium')
    # ### end Alembic commands ###
