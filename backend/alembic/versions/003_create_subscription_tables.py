"""create subscription tables

Revision ID: 003
Revises: 002
Create Date: 2025-01-14 20:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '003'
down_revision: Union[str, None] = '002'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create plans table
    op.create_table(
        'plans',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=50), nullable=False),
        sa.Column('monthly_invoice_limit', sa.Integer(), nullable=False),
        sa.Column('monthly_ai_limit', sa.Integer(), nullable=False),
        sa.Column('rate_limit_per_minute', sa.Integer(), nullable=False),
        sa.Column('features', sa.JSON(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_plans_name', 'plans', ['name'], unique=True)
    
    # Create subscriptions table
    op.create_table(
        'subscriptions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('tenant_id', sa.Integer(), nullable=False),
        sa.Column('plan_id', sa.Integer(), nullable=False),
        sa.Column('status', sa.Enum('ACTIVE', 'TRIAL', 'EXPIRED', 'SUSPENDED', name='subscriptionstatus'), nullable=False),
        sa.Column('trial_starts_at', sa.DateTime(), nullable=True),
        sa.Column('trial_ends_at', sa.DateTime(), nullable=True),
        sa.Column('custom_limits', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['plan_id'], ['plans.id'], ),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_subscriptions_tenant_id', 'subscriptions', ['tenant_id'], unique=True)
    op.create_index('ix_subscriptions_plan_id', 'subscriptions', ['plan_id'], unique=False)
    op.create_index('ix_subscriptions_status', 'subscriptions', ['status'], unique=False)
    
    # Create usage_counters table
    op.create_table(
        'usage_counters',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('tenant_id', sa.Integer(), nullable=False),
        sa.Column('subscription_id', sa.Integer(), nullable=False),
        sa.Column('billing_period', sa.String(length=7), nullable=False),
        sa.Column('invoice_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('ai_request_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['subscription_id'], ['subscriptions.id'], ),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_usage_counters_tenant_id', 'usage_counters', ['tenant_id'], unique=False)
    op.create_index('ix_usage_counters_subscription_id', 'usage_counters', ['subscription_id'], unique=False)
    op.create_index('ix_usage_counters_billing_period', 'usage_counters', ['billing_period'], unique=False)
    # Unique constraint: one counter per tenant per billing period
    op.create_index('ix_usage_counters_tenant_billing', 'usage_counters', ['tenant_id', 'billing_period'], unique=True)


def downgrade() -> None:
    op.drop_index('ix_usage_counters_tenant_billing', table_name='usage_counters')
    op.drop_index('ix_usage_counters_billing_period', table_name='usage_counters')
    op.drop_index('ix_usage_counters_subscription_id', table_name='usage_counters')
    op.drop_index('ix_usage_counters_tenant_id', table_name='usage_counters')
    op.drop_table('usage_counters')
    op.drop_index('ix_subscriptions_status', table_name='subscriptions')
    op.drop_index('ix_subscriptions_plan_id', table_name='subscriptions')
    op.drop_index('ix_subscriptions_tenant_id', table_name='subscriptions')
    op.drop_table('subscriptions')
    op.drop_index('ix_plans_name', table_name='plans')
    op.drop_table('plans')

