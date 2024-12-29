"""Agregar modelo Producto

Revision ID: 614bf51c038c
Revises: 85d67f9fd4bd
Create Date: 2024-12-27 15:45:47.779607

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '614bf51c038c'
down_revision = '85d67f9fd4bd'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('producto',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('nombre', sa.String(length=100), nullable=False),
    sa.Column('total_piezas', sa.Integer(), nullable=False),
    sa.Column('stock', sa.Integer(), nullable=False),
    sa.Column('precio', sa.Float(), nullable=False),
    sa.Column('ultima_actualizacion', sa.DateTime(), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('producto')
    # ### end Alembic commands ###