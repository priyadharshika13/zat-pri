"""extend invoice_logs with observability fields

Revision ID: 005
Revises: 004
Create Date: 2025-01-17 20:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '005'
down_revision: Union[str, None] = '004'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add new columns for invoice observability
    # Use sa.JSON() for SQLite compatibility (works with both SQLite and PostgreSQL)
    op.add_column('invoice_logs', sa.Column('request_payload', sa.JSON(), nullable=True, comment='Original invoice request payload (JSON)'))
    op.add_column('invoice_logs', sa.Column('generated_xml', sa.Text(), nullable=True, comment='Generated XML content (for Phase-2)'))
    op.add_column('invoice_logs', sa.Column('zatca_response', sa.JSON(), nullable=True, comment='Full ZATCA API response (JSON)'))
    op.add_column('invoice_logs', sa.Column('submitted_at', sa.DateTime(), nullable=True, comment='Timestamp when invoice was submitted to ZATCA'))
    op.add_column('invoice_logs', sa.Column('cleared_at', sa.DateTime(), nullable=True, comment='Timestamp when invoice was cleared by ZATCA'))


def downgrade() -> None:
    # Remove observability columns
    op.drop_column('invoice_logs', 'cleared_at')
    op.drop_column('invoice_logs', 'submitted_at')
    op.drop_column('invoice_logs', 'zatca_response')
    op.drop_column('invoice_logs', 'generated_xml')
    op.drop_column('invoice_logs', 'request_payload')

