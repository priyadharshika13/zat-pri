"""create webhooks tables

Revision ID: 009
Revises: 008
Create Date: 2026-01-26 16:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '009'
down_revision: Union[str, None] = '008'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Create webhooks and webhook_logs tables.
    
    webhooks table:
    - Stores webhook configuration per tenant
    - Includes URL, events array, secret for HMAC signing
    - Tracks active status and delivery metrics
    
    webhook_logs table:
    - Tracks webhook delivery attempts
    - Stores payload, response status, error messages
    - Enables audit trail and debugging
    """
    # Create webhooks table
    op.create_table(
        'webhooks',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('tenant_id', sa.Integer(), nullable=False),
        sa.Column('url', sa.String(length=500), nullable=False, comment='Webhook URL endpoint'),
        sa.Column('events', sa.JSON(), nullable=False, comment='Array of event types to subscribe to'),
        sa.Column('secret', sa.String(length=255), nullable=False, comment='HMAC secret for signature verification'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('last_triggered_at', sa.DateTime(), nullable=True, comment='Last time this webhook was triggered'),
        sa.Column('failure_count', sa.Integer(), nullable=False, server_default='0', comment='Number of consecutive failures'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for webhooks
    op.create_index('ix_webhooks_tenant_id', 'webhooks', ['tenant_id'], unique=False)
    op.create_index('ix_webhooks_is_active', 'webhooks', ['is_active'], unique=False)
    op.create_index('ix_webhooks_tenant_active', 'webhooks', ['tenant_id', 'is_active'], unique=False)
    
    # Create webhook_logs table
    op.create_table(
        'webhook_logs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('webhook_id', sa.Integer(), nullable=False),
        sa.Column('event', sa.String(length=100), nullable=False, comment='Event type that triggered the webhook'),
        sa.Column('payload', sa.JSON(), nullable=False, comment='Webhook payload sent'),
        sa.Column('response_status', sa.Integer(), nullable=True, comment='HTTP response status code'),
        sa.Column('error_message', sa.Text(), nullable=True, comment='Error message if delivery failed'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.ForeignKeyConstraint(['webhook_id'], ['webhooks.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for webhook_logs
    op.create_index('ix_webhook_logs_webhook_id', 'webhook_logs', ['webhook_id'], unique=False)
    op.create_index('ix_webhook_logs_event', 'webhook_logs', ['event'], unique=False)
    op.create_index('ix_webhook_logs_created_at', 'webhook_logs', ['created_at'], unique=False)
    op.create_index('ix_webhook_logs_webhook_created', 'webhook_logs', ['webhook_id', 'created_at'], unique=False)
    op.create_index('ix_webhook_logs_event_created', 'webhook_logs', ['event', 'created_at'], unique=False)


def downgrade() -> None:
    """
    Drop webhooks and webhook_logs tables.
    """
    # Drop indexes for webhook_logs
    op.drop_index('ix_webhook_logs_event_created', table_name='webhook_logs')
    op.drop_index('ix_webhook_logs_webhook_created', table_name='webhook_logs')
    op.drop_index('ix_webhook_logs_created_at', table_name='webhook_logs')
    op.drop_index('ix_webhook_logs_event', table_name='webhook_logs')
    op.drop_index('ix_webhook_logs_webhook_id', table_name='webhook_logs')
    
    # Drop webhook_logs table
    op.drop_table('webhook_logs')
    
    # Drop indexes for webhooks
    op.drop_index('ix_webhooks_tenant_active', table_name='webhooks')
    op.drop_index('ix_webhooks_is_active', table_name='webhooks')
    op.drop_index('ix_webhooks_tenant_id', table_name='webhooks')
    
    # Drop webhooks table
    op.drop_table('webhooks')

