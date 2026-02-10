"""alter invoice_logs zatca_response_code to TEXT

Revision ID: 007
Revises: 006
Create Date: 2025-01-18 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '007'
down_revision: Union[str, None] = '006'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Alter zatca_response_code column from VARCHAR(50) to TEXT.
    
    This allows storing longer error messages from ZATCA API responses
    without truncation, ensuring complete error information is preserved
    for debugging and audit purposes.
    """
    # Detect database type for proper column type handling
    bind = op.get_bind()
    is_postgres = bind.dialect.name == 'postgresql'
    
    if is_postgres:
        # PostgreSQL: Use TEXT type
        op.alter_column(
            'invoice_logs',
            'zatca_response_code',
            type_=sa.Text(),
            existing_type=sa.String(length=50),
            existing_nullable=True,
            comment='ZATCA response code or error message (TEXT for long messages)'
        )
    else:
        # SQLite: Use TEXT type (SQLite doesn't distinguish between VARCHAR and TEXT)
        # But we still need to alter the column to ensure consistency
        op.alter_column(
            'invoice_logs',
            'zatca_response_code',
            type_=sa.Text(),
            existing_type=sa.String(length=50),
            existing_nullable=True
        )


def downgrade() -> None:
    """
    Revert zatca_response_code column back to VARCHAR(50).
    
    WARNING: This may truncate existing long error messages.
    """
    # Detect database type
    bind = op.get_bind()
    is_postgres = bind.dialect.name == 'postgresql'
    
    if is_postgres:
        # PostgreSQL: Revert to VARCHAR(50)
        op.alter_column(
            'invoice_logs',
            'zatca_response_code',
            type_=sa.String(length=50),
            existing_type=sa.Text(),
            existing_nullable=True
        )
    else:
        # SQLite: Revert to String(50)
        op.alter_column(
            'invoice_logs',
            'zatca_response_code',
            type_=sa.String(length=50),
            existing_type=sa.Text(),
            existing_nullable=True
        )

