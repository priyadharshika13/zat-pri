/**
 * Trigger file export (download) using API key.
 * Backend returns streaming response with Content-Disposition.
 */

import { getApiKey } from './auth';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'https://zat-pri.onrender.com';

function getFilenameFromDisposition(disposition: string | null): string | null {
  if (!disposition) return null;
  const match = disposition.match(/filename="?([^";]+)"?/);
  return match ? match[1].trim() : null;
}

export async function exportInvoices(params: {
  format: 'csv' | 'json';
  date_from?: string;
  date_to?: string;
  invoice_number?: string;
  status?: string;
  phase?: string;
  environment?: string;
}): Promise<void> {
  const query = new URLSearchParams();
  query.set('format', params.format);
  if (params.date_from) query.set('date_from', params.date_from);
  if (params.date_to) query.set('date_to', params.date_to);
  if (params.invoice_number) query.set('invoice_number', params.invoice_number);
  if (params.status) query.set('status', params.status);
  if (params.phase) query.set('phase', params.phase);
  if (params.environment) query.set('environment', params.environment);

  const apiKey = getApiKey();
  const headers: Record<string, string> = {};
  if (apiKey) headers['X-API-Key'] = apiKey;

  const res = await fetch(`${API_BASE_URL}/api/v1/exports/invoices?${query.toString()}`, { headers });
  if (!res.ok) throw new Error(await res.text().catch(() => `Export failed: ${res.status}`));

  const filename = getFilenameFromDisposition(res.headers.get('Content-Disposition'))
    || `invoices_export.${params.format}`;
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

export async function exportInvoiceLogs(params: {
  format: 'csv' | 'json';
  date_from?: string;
  date_to?: string;
  invoice_number?: string;
  status?: string;
}): Promise<void> {
  const query = new URLSearchParams();
  query.set('format', params.format);
  if (params.date_from) query.set('date_from', params.date_from);
  if (params.date_to) query.set('date_to', params.date_to);
  if (params.invoice_number) query.set('invoice_number', params.invoice_number);
  if (params.status) query.set('status', params.status);

  const apiKey = getApiKey();
  const headers: Record<string, string> = {};
  if (apiKey) headers['X-API-Key'] = apiKey;

  const res = await fetch(`${API_BASE_URL}/api/v1/exports/invoice-logs?${query.toString()}`, { headers });
  if (!res.ok) throw new Error(await res.text().catch(() => `Export failed: ${res.status}`));

  const filename = getFilenameFromDisposition(res.headers.get('Content-Disposition'))
    || `invoice_logs_export.${params.format}`;
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}
