/**
 * Billing and subscription API functions.
 * 
 * Typed functions for plans, subscriptions, and usage.
 */

import { apiGet } from './api';
import { Plan } from '../types/plan';
import { Subscription } from '../types/subscription';
import { Usage } from '../types/usage';

/**
 * Gets all available subscription plans (public endpoint).
 */
export const getPlans = async (): Promise<Plan[]> => {
  return apiGet<Plan[]>('/api/v1/plans');
};

/**
 * Gets current tenant's subscription (requires X-API-Key).
 * 
 * Returns null if no subscription found (404).
 */
export const getCurrentSubscription = async (): Promise<Subscription | null> => {
  try {
    return await apiGet<Subscription>('/api/v1/plans/current');
  } catch (error: unknown) {
    const apiError = error as { status?: number; message?: string };
    // If 404, treat as "no subscription" state
    if (apiError.status === 404) {
      return null;
    }
    // Re-throw other errors (401/403 will be handled by api.ts)
    throw error;
  }
};

/**
 * Gets current tenant's usage summary (requires X-API-Key).
 * 
 * Returns null if no subscription found (404).
 */
export const getUsage = async (): Promise<Usage | null> => {
  try {
    return await apiGet<Usage>('/api/v1/plans/usage');
  } catch (error: unknown) {
    const apiError = error as { status?: number; message?: string };
    // If 404, treat as "no subscription" state
    if (apiError.status === 404) {
      return null;
    }
    // Re-throw other errors (401/403 will be handled by api.ts)
    throw error;
  }
};

