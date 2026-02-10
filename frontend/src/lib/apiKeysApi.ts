/**
 * API Keys management client.
 */

import { apiGet, apiPost, apiDelete } from './api';

const API_BASE = '/api/v1/api-keys';

export interface ApiKeyResponse {
  id: number;
  api_key: string;
  tenant_id: number;
  is_active: boolean;
  created_at: string;
  last_used_at: string | null;
}

export interface ApiKeyCreatePayload {
  api_key?: string;
  is_active?: boolean;
}

/** List API keys for the current tenant */
export const listApiKeys = async (): Promise<ApiKeyResponse[]> => {
  return apiGet<ApiKeyResponse[]>(API_BASE);
};

/** Create API key for the current tenant (use tenant_id from /tenants/me) */
export const createApiKey = async (
  tenantId: number,
  data: ApiKeyCreatePayload = {}
): Promise<ApiKeyResponse> => {
  return apiPost<ApiKeyResponse>(`${API_BASE}/tenants/${tenantId}`, {
    is_active: data.is_active ?? true,
    ...(data.api_key ? { api_key: data.api_key } : {}),
  });
};

/** Delete (revoke) an API key */
export const deleteApiKey = async (keyId: number): Promise<void> => {
  return apiDelete(`${API_BASE}/${keyId}`);
};

export function maskApiKey(key: string): string {
  if (!key || key.length < 8) return '••••••••';
  return key.slice(0, 4) + '••••••••' + key.slice(-4);
}
