/**
 * API client wrapper.
 * 
 * Handles base URL configuration, automatic API key attachment,
 * and global 401/403 error handling with redirect to login.
 */

import { getApiKey, clearApiKey } from './auth';

// Get base URL from environment variable
// For Vite, use VITE_ prefix
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'https://zat-pri.onrender.com';

export interface ApiError {
  message: string;
  status?: number;
  detail?: string | Record<string, unknown>;
}

/**
 * Custom fetch wrapper with automatic token attachment and error handling.
 */
export const apiRequest = async (
  endpoint: string,
  options: RequestInit = {}
): Promise<Response> => {
  const apiKey = getApiKey();
  console.log(`API Key: ${apiKey ? 'Present' : 'Not Present'}`);
  
  // Build full URL
  const url = endpoint.startsWith('http') 
    ? endpoint 
    : `${API_BASE_URL}${endpoint.startsWith('/') ? endpoint : `/${endpoint}`}`;
  
  // Prepare headers
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options.headers as Record<string, string>),
  };
  
  // Attach API key if available (X-API-Key header)
  if (apiKey) {
    (headers as Record<string, string>)['X-API-Key'] = apiKey;
  }
  
  // Make request
  const response = await fetch(url, {
    ...options,
    headers: headers as HeadersInit,
  });
  console.log(`API Request: ${options.method || 'GET'} ${url} - Status: ${response.status}`);
  
  // Handle 401/403 globally - clear API key and redirect to login
  if (response.status === 401 || response.status === 403) {
    clearApiKey();
    // Redirect to login (will be handled by router)
    if (window.location.pathname !== '/login') {
      window.location.href = '/login';
    }
    throw new Error('Unauthorized');
  }
  
  return response;
};

/**
 * GET request helper.
 */
export const apiGet = async <T = unknown>(
  endpoint: string,
  options?: RequestInit
): Promise<T> => {
  const response = await apiRequest(endpoint, {
    ...options,
    method: 'GET',
  });
  
  if (!response.ok) {
    const error = await parseError(response);
    throw error;
  }
  
  // Handle empty responses
  const text = await response.text();
  if (!text) {
    return {} as T;
  }
  
  return JSON.parse(text) as T;
};

/**
 * POST request helper.
 */
export const apiPost = async <T = unknown>(
  endpoint: string,
  data?: unknown,
  options?: RequestInit
): Promise<T> => {
  const response = await apiRequest(endpoint, {
    ...options,
    method: 'POST',
    body: data ? JSON.stringify(data) : undefined,
  });
  
  if (!response.ok) {
    const error = await parseError(response);
    throw error;
  }
  
  // Handle empty responses
  const text = await response.text();
  if (!text) {
    return {} as T;
  }
  
  return JSON.parse(text) as T;
};

/**
 * PUT request helper.
 */
export const apiPut = async <T = unknown>(
  endpoint: string,
  data?: unknown,
  options?: RequestInit
): Promise<T> => {
  const response = await apiRequest(endpoint, {
    ...options,
    method: 'PUT',
    body: data ? JSON.stringify(data) : undefined,
  });
  
  if (!response.ok) {
    const error = await parseError(response);
    throw error;
  }
  
  const text = await response.text();
  if (!text) {
    return {} as T;
  }
  
  return JSON.parse(text) as T;
};

/**
 * DELETE request helper.
 */
export const apiDelete = async <T = unknown>(
  endpoint: string,
  options?: RequestInit
): Promise<T> => {
  const response = await apiRequest(endpoint, {
    ...options,
    method: 'DELETE',
  });
  
  if (!response.ok) {
    const error = await parseError(response);
    throw error;
  }
  
  const text = await response.text();
  if (!text) {
    return {} as T;
  }
  
  return JSON.parse(text) as T;
};

/**
 * Parses error response.
 */
async function parseError(response: Response): Promise<ApiError> {
  try {
    const data = await response.json();
    return {
      message: data.detail || data.message || 'An error occurred',
      status: response.status,
      detail: data,
    };
  } catch {
    return {
      message: `HTTP ${response.status}: ${response.statusText}`,
      status: response.status,
    };
  }
}

export { API_BASE_URL };

