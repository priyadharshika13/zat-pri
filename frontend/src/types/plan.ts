/**
 * Plan type definitions.
 * 
 * Matches backend PlanResponse schema.
 */

export interface Plan {
  id: number;
  name: string;
  monthly_invoice_limit: number; // 0 = unlimited
  monthly_ai_limit: number; // 0 = unlimited
  rate_limit_per_minute: number;
  features?: Record<string, unknown>; // JSON object with feature flags
  is_active: boolean;
  created_at: string; // ISO datetime string
}

