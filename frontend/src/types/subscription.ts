/**
 * Subscription type definitions.
 * 
 * Matches backend SubscriptionResponse schema.
 */

export type SubscriptionStatus = 'active' | 'trial' | 'expired' | 'suspended';

export interface Subscription {
  id: number;
  tenant_id: number;
  plan_id: number;
  plan_name: string;
  status: SubscriptionStatus;
  trial_starts_at?: string | null; // ISO datetime string
  trial_ends_at?: string | null; // ISO datetime string
  trial_days_remaining?: number | null;
  custom_limits?: Record<string, unknown> | null; // JSON object for enterprise custom limits
  created_at: string; // ISO datetime string
  updated_at: string; // ISO datetime string
}

