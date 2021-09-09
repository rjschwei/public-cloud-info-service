"""split out region servers

Revision ID: 35bc840e262b
Revises: e2bdb3a5b1b4
Create Date: 2021-09-13 12:32:17.818502

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '35bc840e262b'
down_revision = 'e2bdb3a5b1b4'
branch_labels = None
depends_on = None

meta = sa.MetaData()

#
# Data types
#

# server_type is used in the *servers table
server_type = postgresql.ENUM('region', 'update', name='server_type',
                               metadata=meta)

alter_items = (
    ('SEQUENCE', 'id_seq'),
    ('INDEX', 'pkey'),
)

#
# Split/Unsplit table helper routines
#
def split_servers_table(provider):
    # create the new provider regionservers table
    op.create_table(f'{provider}regionservers',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('shape', sa.String(length=10), nullable=True),
        sa.Column('ip', postgresql.INET(), nullable=True),
        sa.Column('region', sa.String(length=100), nullable=False),
        sa.Column('ipv6', postgresql.INET(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )

    # rename existing provider servers table to updateservers and
    # drop the superfluous type column.
    op.rename_table(f'{provider}servers', f'{provider}updateservers')
    for alter_type, alter_suffix in alter_items:
        op.execute(f'ALTER {alter_type} {provider}servers_{alter_suffix} RENAME TO {provider}updateservers_{alter_suffix}')
    op.drop_column(f'{provider}updateservers', 'type')

def unsplit_servers_table(provider):
    # rename the updateservers table back to servers and
    # re-add the type field
    for alter_type, alter_suffix in alter_items:
        op.execute(f'ALTER {alter_type} {provider}updateservers_{alter_suffix} RENAME TO {provider}servers_{alter_suffix}')
    op.rename_table(f'{provider}updateservers', f'{provider}servers')
    op.add_column(f'{provider}servers', sa.Column('type', server_type, autoincrement=False, nullable=False))

    # drop the provider regionservers table
    op.drop_table(f'{provider}regionservers')

providers = ['amazon', 'google', 'microsoft']

def upgrade():
    # split the provider specific servers tables into updateservers and regionservers tables
    for provider in providers:
        split_servers_table(provider)

    # The server_type enum is no longer required
    op.execute('DROP TYPE server_type RESTRICT')

def downgrade():
    # split the provider specific servers tables into updateservers and regionservers tables
    for provider in providers:
        split_servers_table(provider)
