"""add retry tracking to invoice_logs

Revision ID: 008
Revises: 007
Create Date: 2025-01-18 14:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '008'
down_revision: Union[str, None] = '007'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Add retry tracking fields to invoice_logs table.
    
    Adds:
    - action: String(20) - Action type (e.g., 'RETRY', 'SUBMIT')
    - previous_status: String(20) - Previous invoice status before action
    
    These fields enable audit trail tracking for invoice retry operations,
    allowing full visibility into retry attempts and status transitions.
    """
    op.add_column(
        'invoice_logs',
        sa.Column('action', sa.String(length=20), nullable=True, comment="Action type (e.g., 'RETRY', 'SUBMIT')")
    )
    op.add_column(
        'invoice_logs',
        sa.Column('previous_status', sa.String(length=20), nullable=True, comment="Previous invoice status before action")
    )


def downgrade() -> None:
    """
    Remove retry tracking fields from invoice_logs table.
    """
    op.drop_column('invoice_logs', 'previous_status')
    op.drop_column('invoice_logs', 'action')

