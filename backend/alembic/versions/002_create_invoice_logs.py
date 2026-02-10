"""create invoice_logs

Revision ID: 002
Revises: 001
Create Date: 2025-01-14 19:40:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '002'
down_revision: Union[str, None] = '001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create invoice_logs table
    op.create_table(
        'invoice_logs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('tenant_id', sa.Integer(), nullable=False),
        sa.Column('invoice_number', sa.String(length=50), nullable=False),
        sa.Column('uuid', sa.String(length=100), nullable=True),
        sa.Column('hash', sa.String(length=64), nullable=True),
        sa.Column('environment', sa.String(length=20), nullable=False),
        sa.Column('status', sa.Enum('SUBMITTED', 'CLEARED', 'REJECTED', 'ERROR', name='invoicelogstatus'), nullable=False),
        sa.Column('zatca_response_code', sa.String(length=50), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_invoice_logs_tenant_id', 'invoice_logs', ['tenant_id'], unique=False)
    op.create_index('ix_invoice_logs_invoice_number', 'invoice_logs', ['invoice_number'], unique=False)
    op.create_index('ix_invoice_logs_status', 'invoice_logs', ['status'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_invoice_logs_status', table_name='invoice_logs')
    op.drop_index('ix_invoice_logs_invoice_number', table_name='invoice_logs')
    op.drop_index('ix_invoice_logs_tenant_id', table_name='invoice_logs')
    op.drop_table('invoice_logs')

