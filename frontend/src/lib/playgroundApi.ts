/**
 * API Playground client.
 * 
 * Handles playground-specific API calls including templates and execution.
 */

import { apiGet, apiRequest } from './api';

export interface RequestTemplate {
  name: string;
  description: string;
  endpoint: string;
  method: string;
  body?: Record<string, unknown>;
  query_params?: Record<string, string>;
  requires_production_confirmation: boolean;
}

export interface PlaygroundRequest {
  endpoint: string;
  method: string;
  body?: Record<string, unknown>;
  query_params?: Record<string, string>;
  confirm_production?: boolean;
}

export interface PlaygroundResponse {
  status_code: number;
  headers: Record<string, string>;
  body: unknown;
  latency_ms: number;
  timestamp: string;
  source: string;
}

/**
 * Get all available request templates.
 */
export const getTemplates = async (): Promise<Record<string, RequestTemplate>> => {
  return apiGet<Record<string, RequestTemplate>>('/api/v1/playground/templates');
};

/**
 * Execute a playground request directly (bypasses playground endpoint, calls actual API).
 * This is the recommended approach - the playground endpoint is mainly for templates.
 */
export const executePlaygroundRequest = async (
  request: PlaygroundRequest
): Promise<PlaygroundResponse> => {
  const startTime = Date.now();
  
  // Build URL with query params
  let url = request.endpoint;
  if (request.query_params && Object.keys(request.query_params).length > 0) {
    const params = new URLSearchParams(request.query_params);
    url += `?${params.toString()}`;
  }
  
  // Prepare request options
  const options: RequestInit = {
    method: request.method,
    headers: {
      'Content-Type': 'application/json',
    },
  };
  
  // Add body for POST/PUT/PATCH
  if (request.body && ['POST', 'PUT', 'PATCH'].includes(request.method.toUpperCase())) {
    options.body = JSON.stringify(request.body);
  }
  
  // Make request using apiRequest to get full response details
  const response = await apiRequest(url, options);
  
  const latency_ms = Date.now() - startTime;
  
  // Parse response body
  let body: unknown;
  const text = await response.text();
  try {
    body = text ? JSON.parse(text) : {};
  } catch {
    body = text;
  }
  
  // Extract headers
  const headers: Record<string, string> = {};
  response.headers.forEach((value, key) => {
    headers[key] = value;
  });
  
  return {
    status_code: response.status,
    headers,
    body,
    latency_ms,
    timestamp: new Date().toISOString(),
    source: 'api_playground',
  };
};

/**
 * Generate curl command from request.
 */
export const generateCurlCommand = (request: PlaygroundRequest, apiKey: string): string => {
  const baseUrl = import.meta.env.VITE_API_BASE_URL || 'https://zat-pri.onrender.com';
  let url = `${baseUrl}${request.endpoint}`;
  
  // Add query params
  if (request.query_params && Object.keys(request.query_params).length > 0) {
    const params = new URLSearchParams(request.query_params);
    url += `?${params.toString()}`;
  }
  
  let curl = `curl -X ${request.method} "${url}" \\\n`;
  curl += `  -H "X-API-Key: ${apiKey}" \\\n`;
  curl += `  -H "Content-Type: application/json"`;
  
  if (request.body && ['POST', 'PUT', 'PATCH'].includes(request.method.toUpperCase())) {
    const bodyJson = JSON.stringify(request.body, null, 2);
    curl += ` \\\n  -d '${bodyJson.replace(/'/g, "'\\''")}'`;
  }
  
  return curl;
};

