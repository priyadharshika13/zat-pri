/**
 * ZATCA API functions.
 * 
 * Typed functions for ZATCA setup and management operations.
 */

import { apiGet, apiPost, apiRequest } from './api';

export interface ZatcaStatus {
  connected: boolean;
  environment: string;
  certificate: {
    id: number;
    serial: string | null;
    issuer: string | null;
    status: string;
    is_active: boolean;
  } | null;
  certificate_expiry: string | null;
  last_sync: string | null;
}

export interface CsrGenerateRequest {
  environment: string;
  common_name: string;
  organization?: string;
  organizational_unit?: string;
  country?: string;
  state?: string;
  locality?: string;
  email?: string;
}

export interface CsrGenerateResponse {
  csr: string;
  private_key: string;
  subject: string;
  key_size: number;
  environment: string;
  common_name: string;
}

export interface CsidUploadResponse {
  success: boolean;
  certificate: {
    id: number;
    serial: string | null;
    issuer: string | null;
    expiry_date: string | null;
    uploaded_at: string | null;
    environment: string;
    status: string;
  };
  message: string;
}

/**
 * Gets ZATCA connection status.
 */
export const getZatcaStatus = async (environment?: string): Promise<ZatcaStatus> => {
  const query = environment ? `?environment=${environment}` : '';
  return apiGet<ZatcaStatus>(`/api/v1/zatca/status${query}`);
};

/**
 * Generates a Certificate Signing Request (CSR).
 */
export const generateCsr = async (data: CsrGenerateRequest): Promise<CsrGenerateResponse> => {
  const formData = new FormData();
  formData.append('environment', data.environment);
  formData.append('common_name', data.common_name);
  if (data.organization) formData.append('organization', data.organization);
  if (data.organizational_unit) formData.append('organizational_unit', data.organizational_unit);
  if (data.country) formData.append('country', data.country);
  if (data.state) formData.append('state', data.state);
  if (data.locality) formData.append('locality', data.locality);
  if (data.email) formData.append('email', data.email);

  // For FormData, we need to manually construct the request to avoid setting Content-Type
  const apiKey = (await import('./auth')).getApiKey();
  const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
  
  const headers: Record<string, string> = {};
  if (apiKey) {
    headers['X-API-Key'] = apiKey;
  }
  
  const response = await fetch(`${API_BASE_URL}/api/v1/zatca/csr/generate`, {
    method: 'POST',
    body: formData,
    headers,
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Failed to generate CSR' }));
    throw new Error(error.detail || 'Failed to generate CSR');
  }

  return response.json();
};

/**
 * Uploads CSID certificate and private key.
 */
export const uploadCsid = async (
  environment: string,
  certificate: File,
  privateKey: File
): Promise<CsidUploadResponse> => {
  const formData = new FormData();
  formData.append('environment', environment);
  formData.append('certificate', certificate);
  formData.append('private_key', privateKey);

  // For FormData, we need to manually construct the request to avoid setting Content-Type
  const apiKey = (await import('./auth')).getApiKey();
  const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
  
  const headers: Record<string, string> = {};
  if (apiKey) {
    headers['X-API-Key'] = apiKey;
  }
  
  const response = await fetch(`${API_BASE_URL}/api/v1/zatca/csid/upload`, {
    method: 'POST',
    body: formData,
    headers,
  });
  
  // Handle 401/403 globally
  if (response.status === 401 || response.status === 403) {
    const { clearApiKey } = await import('./auth');
    clearApiKey();
    if (window.location.pathname !== '/login') {
      window.location.href = '/login';
    }
    throw new Error('Unauthorized');
  }

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Failed to upload CSID' }));
    throw new Error(error.detail || 'Failed to upload CSID');
  }

  return response.json();
};

