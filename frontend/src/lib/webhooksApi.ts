/**
 * Webhooks API client.
 */

import { apiGet, apiPost, apiPut, apiDelete } from './api';

export type WebhookEvent =
  | 'invoice.cleared'
  | 'invoice.rejected'
  | 'invoice.failed'
  | 'invoice.retry_started'
  | 'invoice.retry_completed';

export interface WebhookCreateRequest {
  url: string;
  events: WebhookEvent[];
  secret?: string;
  is_active?: boolean;
}

export interface WebhookUpdateRequest {
  url?: string;
  events?: WebhookEvent[];
  secret?: string;
  is_active?: boolean;
}

export interface WebhookResponse {
  id: number;
  tenant_id: number;
  url: string;
  events: string[];
  is_active: boolean;
  created_at: string;
  updated_at: string;
  last_triggered_at: string | null;
  failure_count: number;
}

export interface WebhookListResponse {
  webhooks: WebhookResponse[];
  total: number;
  active_count: number;
  inactive_count: number;
}

export interface WebhookLogResponse {
  id: number;
  webhook_id: number;
  event: string;
  payload: Record<string, unknown>;
  response_status: number | null;
  error_message: string | null;
  created_at: string;
}

export const listWebhooks = async (): Promise<WebhookListResponse> => {
  return apiGet<WebhookListResponse>('/api/v1/webhooks');
};

export const getWebhook = async (id: number): Promise<WebhookResponse> => {
  return apiGet<WebhookResponse>(`/api/v1/webhooks/${id}`);
};

export const createWebhook = async (data: WebhookCreateRequest): Promise<WebhookResponse> => {
  return apiPost<WebhookResponse>('/api/v1/webhooks', data);
};

export const updateWebhook = async (id: number, data: WebhookUpdateRequest): Promise<WebhookResponse> => {
  return apiPut<WebhookResponse>(`/api/v1/webhooks/${id}`, data);
};

export const deleteWebhook = async (id: number): Promise<void> => {
  return apiDelete(`/api/v1/webhooks/${id}`);
};

export const getWebhookLogs = async (webhookId: number, limit = 100): Promise<WebhookLogResponse[]> => {
  return apiGet<WebhookLogResponse[]>(`/api/v1/webhooks/${webhookId}/logs?limit=${limit}`);
}
