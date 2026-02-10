"""create tenants api_keys

Revision ID: 001
Revises: 
Create Date: 2025-01-14 19:35:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create tenants table
    op.create_table(
        'tenants',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('company_name', sa.String(length=200), nullable=False),
        sa.Column('vat_number', sa.String(length=15), nullable=False),
        sa.Column('environment', sa.String(length=20), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_tenants_company_name', 'tenants', ['company_name'], unique=False)
    op.create_index('ix_tenants_vat_number', 'tenants', ['vat_number'], unique=True)
    
    # Create api_keys table
    op.create_table(
        'api_keys',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('api_key', sa.String(length=255), nullable=False),
        sa.Column('tenant_id', sa.Integer(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('last_used_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_api_keys_api_key', 'api_keys', ['api_key'], unique=True)
    op.create_index('ix_api_keys_tenant_id', 'api_keys', ['tenant_id'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_api_keys_tenant_id', table_name='api_keys')
    op.drop_index('ix_api_keys_api_key', table_name='api_keys')
    op.drop_table('api_keys')
    op.drop_index('ix_tenants_vat_number', table_name='tenants')
    op.drop_index('ix_tenants_company_name', table_name='tenants')
    op.drop_table('tenants')

