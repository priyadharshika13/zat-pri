"""create certificates

Revision ID: 004
Revises: 003
Create Date: 2025-01-15 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '004'
down_revision: Union[str, None] = '003'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create certificates table
    op.create_table(
        'certificates',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('tenant_id', sa.Integer(), nullable=False),
        sa.Column('environment', sa.String(length=20), nullable=False),
        sa.Column('certificate_serial', sa.String(length=100), nullable=True),
        sa.Column('issuer', sa.String(length=200), nullable=True),
        sa.Column('expiry_date', sa.DateTime(), nullable=True),
        sa.Column('status', sa.Enum('ACTIVE', 'EXPIRED', 'REVOKED', name='certificatestatus'), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('uploaded_at', sa.DateTime(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_certificates_tenant_id', 'certificates', ['tenant_id'], unique=False)
    op.create_index('ix_certificates_environment', 'certificates', ['environment'], unique=False)
    op.create_index('ix_certificates_certificate_serial', 'certificates', ['certificate_serial'], unique=False)
    op.create_index('ix_certificates_status', 'certificates', ['status'], unique=False)
    op.create_index('ix_certificates_is_active', 'certificates', ['is_active'], unique=False)
    op.create_index('ix_certificates_expiry_date', 'certificates', ['expiry_date'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_certificates_expiry_date', table_name='certificates')
    op.drop_index('ix_certificates_is_active', table_name='certificates')
    op.drop_index('ix_certificates_status', table_name='certificates')
    op.drop_index('ix_certificates_certificate_serial', table_name='certificates')
    op.drop_index('ix_certificates_environment', table_name='certificates')
    op.drop_index('ix_certificates_tenant_id', table_name='certificates')
    op.drop_table('certificates')

