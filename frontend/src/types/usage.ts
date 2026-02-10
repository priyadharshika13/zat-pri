/**
 * Usage type definitions.
 * 
 * Matches backend UsageCounterResponse schema.
 */

export interface Usage {
  tenant_id: number;
  billing_period: string; // Format: YYYY-MM
  invoice_count: number;
  invoice_limit: number; // 0 = unlimited
  ai_request_count: number;
  ai_limit: number; // 0 = unlimited
  invoice_limit_exceeded: boolean;
  ai_limit_exceeded: boolean;
}

