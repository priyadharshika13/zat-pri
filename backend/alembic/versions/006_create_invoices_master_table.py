"""create invoices master table

Revision ID: 006
Revises: 005
Create Date: 2025-01-18 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '006'
down_revision: Union[str, None] = '005'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Detect database type for enum handling
    bind = op.get_bind()
    is_postgres = bind.dialect.name == 'postgresql'
    
    # Create InvoiceStatus enum (PostgreSQL only)
    if is_postgres:
        invoice_status_enum = postgresql.ENUM(
            'CREATED', 'PROCESSING', 'CLEARED', 'REJECTED', 'FAILED',
            name='invoicestatus',
            create_type=False
        )
        invoice_status_enum.create(bind, checkfirst=True)
        status_column = sa.Column(
            'status',
            invoice_status_enum,
            nullable=False,
            server_default='CREATED'
        )
    else:
        # SQLite: Use String with check constraint
        status_column = sa.Column(
            'status',
            sa.String(20),
            nullable=False,
            server_default='CREATED'
        )
    
    # Create invoices master table
    op.create_table(
        'invoices',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('tenant_id', sa.Integer(), nullable=False),
        sa.Column('invoice_number', sa.String(length=50), nullable=False),
        sa.Column('phase', sa.String(20), nullable=False),  # Use String for SQLite compatibility
        status_column,
        sa.Column('environment', sa.String(20), nullable=False),  # Use String for SQLite compatibility
        sa.Column('total_amount', sa.Float(), nullable=False),
        sa.Column('tax_amount', sa.Float(), nullable=False),
        sa.Column('hash', sa.String(length=64), nullable=True),
        sa.Column('uuid', sa.String(length=100), nullable=True),
        sa.Column('xml_content', sa.Text(), nullable=True),
        sa.Column('zatca_response', sa.JSON(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('tenant_id', 'invoice_number', name='uq_invoices_tenant_invoice_number')
    )
    
    # Create indexes for performance
    op.create_index('ix_invoices_tenant_id', 'invoices', ['tenant_id'], unique=False)
    op.create_index('ix_invoices_invoice_number', 'invoices', ['invoice_number'], unique=False)
    op.create_index('ix_invoices_status', 'invoices', ['status'], unique=False)
    op.create_index('ix_invoices_hash', 'invoices', ['hash'], unique=False)
    op.create_index('ix_invoices_uuid', 'invoices', ['uuid'], unique=False)
    op.create_index('ix_invoices_created_at', 'invoices', ['created_at'], unique=False)
    op.create_index('ix_invoices_tenant_status', 'invoices', ['tenant_id', 'status'], unique=False)
    op.create_index('ix_invoices_tenant_created', 'invoices', ['tenant_id', 'created_at'], unique=False)


def downgrade() -> None:
    # Drop indexes
    op.drop_index('ix_invoices_tenant_created', table_name='invoices')
    op.drop_index('ix_invoices_tenant_status', table_name='invoices')
    op.drop_index('ix_invoices_created_at', table_name='invoices')
    op.drop_index('ix_invoices_uuid', table_name='invoices')
    op.drop_index('ix_invoices_hash', table_name='invoices')
    op.drop_index('ix_invoices_status', table_name='invoices')
    op.drop_index('ix_invoices_invoice_number', table_name='invoices')
    op.drop_index('ix_invoices_tenant_id', table_name='invoices')
    
    # Drop table
    op.drop_table('invoices')
    
    # Drop enum (only if no other tables use it)
    # Note: We don't drop the enum as it might be used elsewhere
    # op.execute('DROP TYPE IF EXISTS invoicestatus')

